"""Run a deterministic, no-gold-span candidate benchmark on a Colab GPU.

The output contains corpus-level and model-level diagnostics only. It never
writes source identifiers, raw text, spans, or per-document predictions.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import re
import statistics
import time
from collections import Counter
from collections.abc import Callable, Iterable, Mapping, Sequence
from datetime import date
from pathlib import Path
from typing import Any

MODELS = {
    "SecureBERT-NER": (
        "CyberPeace-Institute/SecureBERT-NER",
        "7f935a4f7db13697580c881e381bb2636dfa779a",
    ),
    "SecureBERT-APTNER": (
        "Cyber-ThreaD/SecureBERT-APTNER",
        "f220a5fbeb8ed9b60a516cf420fc816d9705ce7d",
    ),
}


def build_dataset_kwargs(
    path: str, name: str | None, split: str, revision: str | None = None
) -> dict[str, str | None]:
    kwargs: dict[str, str | None] = {"path": path, "split": split, "revision": revision}
    if name is not None:
        kwargs["name"] = name
    return kwargs


def validate_revision(revision: str | None) -> str:
    if not revision or re.fullmatch(r"[0-9a-fA-F]{40}", revision) is None:
        raise ValueError("dataset revision must be pinned")
    return revision


def _value(row: Mapping[str, object], key: str) -> str:
    value = row.get(key)
    if value is None:
        return ""
    return value.strip() if isinstance(value, str) else str(value).strip()


def _identity(row: Mapping[str, object], column: str, source_index: int) -> str:
    columns = [part.strip() for part in column.split(",") if part.strip()]
    values = [_value(row, part) for part in columns]
    return (
        json.dumps(values, ensure_ascii=False, separators=(",", ":"))
        if columns and all(values)
        else ""
    )


def select_sample(
    rows: Iterable[Mapping[str, object]],
    *,
    text_column: str,
    identity_column: str,
    corpus_id: str,
    seed: int,
    limit: int,
    eligibility: Callable[[Mapping[str, object]], bool] | None = None,
) -> tuple[list[dict[str, object]], dict[str, int | str]]:
    """Filter, exact-deduplicate, and deterministically sample source rows."""

    if limit < 1:
        raise ValueError("limit must be positive")
    eligible_rows: list[dict[str, object]] = []
    seen: set[str] = set()
    duplicates_removed = 0
    for source_index, row in enumerate(rows):
        text = row.get(text_column)
        if not isinstance(text, str) or not text.strip():
            continue
        if eligibility is not None and not eligibility(row):
            continue
        identity = _identity(row, identity_column, source_index)
        if not identity:
            raise ValueError(f"identity column {identity_column!r} is missing or empty")
        if identity in seen:
            duplicates_removed += 1
            continue
        seen.add(identity)
        eligible_rows.append({**row, "__text": text.strip(), "__identity": identity})

    if len(eligible_rows) < limit:
        raise ValueError(f"only {len(eligible_rows)} eligible rows available; need {limit}")

    ranked = sorted(
        eligible_rows,
        key=lambda row: hashlib.sha256(
            f"{seed}|{corpus_id}|{row['__identity']}".encode()
        ).hexdigest(),
    )
    selected = ranked[:limit]
    stats: dict[str, int | str] = {
        "eligible_before_dedup": len(eligible_rows) + duplicates_removed,
        "duplicates_removed": duplicates_removed,
        "eligible_after_dedup": len(eligible_rows),
        "selected": len(selected),
    }
    return selected, stats


def candidate_filter(name: str) -> Callable[[Mapping[str, object]], bool] | None:
    if name == "none":
        return None
    if name == "nonempty":
        return lambda row: True
    if name == "vinitvek-healthcare-2023":

        def is_healthcare(row: Mapping[str, object]) -> bool:
            industry = _value(row, "affected_industry").casefold()
            organization = _value(row, "affected_organization").casefold()
            event_date = _value(row, "event_date")[:10]
            domain_match = "health" in industry or any(
                term in organization for term in ("hospital", "medical")
            )
            return domain_match and "2023-01-01" <= event_date <= "2023-10-30"

        return is_healthcare
    raise ValueError(f"unknown filter: {name}")


def _percentiles(values: Sequence[int | float]) -> dict[str, float | int]:
    if not values:
        return {"min": 0, "median": 0, "p90": 0, "p95": 0, "max": 0}
    ordered = sorted(values)

    def percentile_value(fraction: float) -> int | float:
        index = max(0, min(len(ordered) - 1, math.ceil(len(ordered) * fraction) - 1))
        return ordered[index]

    return {
        "min": ordered[0],
        "median": round(statistics.median(ordered), 2),
        "p90": round(percentile_value(0.90), 2),
        "p95": round(percentile_value(0.95), 2),
        "max": ordered[-1],
    }


def _canonical_label(value: object) -> str | None:
    label = str(value).strip().upper()
    if "-" in label:
        _, label = label.split("-", maxsplit=1)
    if label in {"VUL", "VULID", "VULNAME"}:
        return "VUL"
    if label in {"IDTY", "ACT", "LOC"}:
        return label
    return None


def _prediction_spans(raw_entities: Iterable[Mapping[str, object]]) -> list[tuple[int, int, str]]:
    spans = []
    for entity in raw_entities:
        label = _canonical_label(entity.get("entity_group", entity.get("entity")))
        start = entity.get("start")
        end = entity.get("end")
        if label is None or not isinstance(start, int) or not isinstance(end, int):
            continue
        spans.append((start, end, label))
    return spans


def _prediction_scores(raw_entities: Iterable[Mapping[str, object]]) -> list[float]:
    scores = []
    for entity in raw_entities:
        label = _canonical_label(entity.get("entity_group", entity.get("entity")))
        score = entity.get("score")
        if label is None or score is None:
            continue
        try:
            scores.append(float(str(score)))
        except (TypeError, ValueError):
            continue
    return scores


def _token_lengths(tokenizer: Any, text: str) -> tuple[int, int]:
    encoded = tokenizer(text, add_special_tokens=True, truncation=False)
    input_ids = encoded["input_ids"]
    return len(input_ids), len(text.split())


def _model_limit(tagger: Any) -> int:
    tokenizer_limit = getattr(tagger.tokenizer, "model_max_length", 512)
    if tokenizer_limit > 100_000:
        tokenizer_limit = getattr(tagger.model.config, "max_position_embeddings", 512)
    return int(tokenizer_limit)


def _length_bins(
    word_counts: list[int], entity_counts: list[int | None]
) -> dict[str, dict[str, int]]:
    bins = {"0-49": [], "50-199": [], "200-499": [], "500+": []}
    for words, entities in zip(word_counts, entity_counts, strict=True):
        if entities is None:
            continue
        key = (
            "0-49"
            if words < 50
            else "50-199"
            if words < 200
            else "200-499"
            if words < 500
            else "500+"
        )
        bins[key].append(entities)
    return {
        key: {
            "documents": len(values),
            "documents_with_entities": sum(value > 0 for value in values),
            "entities": sum(values),
        }
        for key, values in bins.items()
    }


def _prediction_metrics(
    entity_counts: list[int | None], word_counts: list[int]
) -> dict[str, float | int]:
    processed = [
        (entities, words)
        for entities, words in zip(entity_counts, word_counts, strict=True)
        if entities is not None
    ]
    counts = [entities for entities, _ in processed]
    words = [words for _, words in processed]
    documents = len(counts)
    total_entities = sum(counts)
    return {
        "documents_processed": documents,
        "predicted_entities": total_entities,
        "documents_with_entities": sum(count > 0 for count in counts),
        "empty_prediction_rate": round(sum(count == 0 for count in counts) / documents, 4)
        if documents
        else 0.0,
        "entities_per_100_words": round(100 * total_entities / max(sum(words), 1), 4),
    }


def run_model(
    model_name: str,
    repository: str,
    revision: str,
    texts: list[str],
) -> tuple[dict[str, object], list[set[tuple[int, int, str]] | None], list[bool]]:
    import torch
    from transformers import pipeline

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is not available; request a Colab T4")
    torch.cuda.reset_peak_memory_stats()
    started = time.perf_counter()
    tagger = pipeline(
        "token-classification",
        model=repository,
        revision=revision,
        aggregation_strategy="simple",
        device=0,
    )
    model_limit = _model_limit(tagger)
    word_counts = [len(text.split()) for text in texts]
    token_counts = []
    over_limit = 0
    dropped_tokens = 0
    predictions: list[set[tuple[int, int, str]] | None] = []
    successes: list[bool] = []
    entity_counts: list[int | None] = []
    label_counts: Counter[str] = Counter()
    span_lengths: list[int] = []
    scores: list[float] = []
    failures: Counter[str] = Counter()
    for text in texts:
        try:
            token_count, _ = _token_lengths(tagger.tokenizer, text)
            token_counts.append(token_count)
            if token_count > model_limit:
                over_limit += 1
                dropped_tokens += token_count - model_limit
            raw_entities = tagger(text)
            spans = set(_prediction_spans(raw_entities))
            predictions.append(spans)
            successes.append(True)
            entity_counts.append(len(spans))
            for _, _, label in spans:
                label_counts[label] += 1
            span_lengths.extend(end - start for start, end, _ in spans)
            scores.extend(_prediction_scores(raw_entities))
        except Exception as error:  # pragma: no cover - exercised by remote runtimes
            predictions.append(None)
            successes.append(False)
            entity_counts.append(None)
            failures[type(error).__name__] += 1

    processed = sum(successes)
    prediction_metrics = _prediction_metrics(entity_counts, word_counts)
    elapsed = time.perf_counter() - started
    result = {
        "model": model_name,
        "repository": repository,
        "revision": revision,
        "documents_attempted": len(texts),
        "documents_processed": processed,
        "documents_failed": len(texts) - processed,
        "failure_types": dict(failures),
        "model_max_tokens": model_limit,
        "token_lengths": _percentiles(token_counts),
        "documents_over_model_limit": over_limit,
        "over_limit_rate": round(over_limit / len(texts), 4),
        "tokens_over_model_limit": dropped_tokens,
        "inference_overflow_policy": "transformers_pipeline_default_single_window",
        **prediction_metrics,
        "entity_label_counts": dict(label_counts),
        "span_lengths": _percentiles(span_lengths),
        "score_mean": round(statistics.mean(scores), 4) if scores else 0.0,
        "score_p05": (
            round(sorted(scores)[max(0, math.ceil(len(scores) * 0.05) - 1)], 4) if scores else 0.0
        ),
        "length_bins": _length_bins(word_counts, entity_counts),
        "seconds": round(elapsed, 2),
        "documents_per_second": round(processed / max(elapsed, 0.001), 4),
        "peak_gpu_memory_mib": round(torch.cuda.max_memory_allocated() / 1024**2, 1),
    }
    return result, predictions, successes


def _set_f1(left: set[Any], right: set[Any]) -> float:
    true_positive = len(left & right)
    if not left and not right:
        return 1.0
    if (not left and right) or (left and not right):
        return 0.0
    precision = true_positive / len(left)
    recall = true_positive / len(right)
    return 2 * precision * recall / (precision + recall) if precision + recall else 0.0


def agreement(
    left: list[set[tuple[int, int, str]] | None],
    right: list[set[tuple[int, int, str]] | None],
    left_success: list[bool],
    right_success: list[bool],
) -> dict[str, float | int]:
    comparable = [
        index
        for index, (left_ok, right_ok) in enumerate(zip(left_success, right_success, strict=True))
        if left_ok and right_ok
    ]
    if not comparable:
        return {
            "comparable_documents": 0,
            "exact_set_agreement": 0.0,
            "empty_nonempty_agreement": 0.0,
            "mean_typed_concordance_f1": 0.0,
            "mean_boundary_concordance_f1": 0.0,
        }
    typed_scores = [_set_f1(left[index] or set(), right[index] or set()) for index in comparable]
    boundary_scores = [
        _set_f1(
            {(start, end) for start, end, _ in (left[index] or set())},
            {(start, end) for start, end, _ in (right[index] or set())},
        )
        for index in comparable
    ]
    return {
        "comparable_documents": len(comparable),
        "exact_set_agreement": round(
            sum(left[index] == right[index] for index in comparable) / len(comparable), 4
        ),
        "empty_nonempty_agreement": round(
            sum(bool(left[index]) == bool(right[index]) for index in comparable) / len(comparable),
            4,
        ),
        "mean_typed_concordance_f1": round(statistics.mean(typed_scores), 4),
        "mean_boundary_concordance_f1": round(statistics.mean(boundary_scores), 4),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default=os.environ.get("DATASET"))
    parser.add_argument("--text-column", default=os.environ.get("TEXT_COLUMN"))
    parser.add_argument("--identity-column", default=os.environ.get("IDENTITY_COLUMN"))
    parser.add_argument("--split", default=os.environ.get("SPLIT", "train"))
    parser.add_argument("--config", default=os.environ.get("CONFIG"))
    parser.add_argument("--revision", default=os.environ.get("REVISION"))
    parser.add_argument("--filter", dest="filter_name", default=os.environ.get("FILTER", "none"))
    parser.add_argument("--seed", type=int, default=int(os.environ.get("SEED", "20260913")))
    parser.add_argument("--limit", type=int, default=int(os.environ.get("LIMIT", "100")))
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(os.environ.get("OUTPUT", "/content/candidate_benchmark.json")),
    )
    args, _ = parser.parse_known_args()
    if not args.dataset or not args.text_column:
        parser.error("--dataset and --text-column are required")
    if not args.identity_column:
        parser.error("--identity-column is required for reproducible deduplication")
    args.revision = validate_revision(args.revision)

    import datasets as datasets_lib
    import torch
    import transformers
    from datasets import load_dataset

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is not available; request a Colab T4")
    dataset = load_dataset(
        **build_dataset_kwargs(args.dataset, args.config, args.split, args.revision)
    )
    selected, sampling = select_sample(
        dataset,
        text_column=args.text_column,
        identity_column=args.identity_column,
        corpus_id=args.dataset,
        seed=args.seed,
        limit=args.limit,
        eligibility=candidate_filter(args.filter_name),
    )
    texts = [str(row["__text"]) for row in selected]
    model_results = []
    model_predictions = []
    model_successes = []
    started = time.perf_counter()
    for model_name, (repository, revision) in MODELS.items():
        try:
            result, predictions, successes = run_model(model_name, repository, revision, texts)
        except Exception as error:  # pragma: no cover - exercised by remote runtimes
            result = {
                "model": model_name,
                "repository": repository,
                "revision": revision,
                "documents_attempted": len(texts),
                "documents_processed": 0,
                "documents_failed": len(texts),
                "initialization_failed": True,
                "failure_types": {type(error).__name__: 1},
            }
            predictions = [None] * len(texts)
            successes = [False] * len(texts)
        model_results.append(result)
        model_predictions.append(predictions)
        model_successes.append(successes)
        torch.cuda.empty_cache()
    result = {
        "experiment_status": "extension",
        "benchmark": "no_gold_span_candidate_suitability",
        "dataset": args.dataset,
        "dataset_revision": args.revision,
        "config": args.config,
        "split": args.split,
        "text_column": args.text_column,
        "identity_column": args.identity_column,
        "filter": args.filter_name,
        "seed": args.seed,
        "source_license": "See data/SEARCH_LOG.md; benchmark does not grant redistribution rights.",
        "access_date": date.today().isoformat(),
        "redistribution": (
            "Aggregate diagnostics only; no raw text, identifiers, spans, "
            "or per-document predictions."
        ),
        "sampling": sampling,
        "sample_text": {
            "documents": len(texts),
            "characters_total": sum(len(text) for text in texts),
            "words_total": sum(len(text.split()) for text in texts),
            "sample_sha256": hashlib.sha256("\n".join(texts).encode()).hexdigest(),
            "characters": _percentiles([len(text) for text in texts]),
            "words": _percentiles([len(text.split()) for text in texts]),
        },
        "runtime": {
            "python": platform.python_version(),
            "torch": torch.__version__,
            "cuda": torch.version.cuda,
            "transformers": transformers.__version__,
            "datasets": datasets_lib.__version__,
            "gpu": torch.cuda.get_device_name(0),
            "seconds_total": round(time.perf_counter() - started, 2),
        },
        "models": model_results,
        "agreement": agreement(
            model_predictions[0],
            model_predictions[1],
            model_successes[0],
            model_successes[1],
        ),
    }
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
