"""Score SecureBERT against the local Muse silver labels on a Colab GPU.

The input archive is uploaded separately to the ephemeral Colab runtime. The
default output contains aggregate metrics only; an explicitly requested private
diagnostic can additionally include source text and per-document spans.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import tarfile
import time
from collections import Counter
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
LABELS = {"IDTY", "ACT", "VUL", "LOC"}
WORD_RE = re.compile(r"\w", re.UNICODE)


def _extract_archive(archive: Path, destination: Path) -> None:
    """Extract a trusted Muse archive into the runtime work directory."""

    destination.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive, "r:gz") as handle:
        handle.extractall(destination, filter="data")


def _load_records(root: Path) -> list[dict[str, Any]]:
    """Load retained source records together with their gold entity labels."""

    records: list[dict[str, Any]] = []
    for dataset_dir in sorted(path for path in root.iterdir() if path.is_dir()):
        for batch_path in sorted(dataset_dir.glob("batch_*.json")):
            suffix = batch_path.stem.removeprefix("batch_")
            label_path = dataset_dir / f"labels_batch_{suffix}.json"
            sources = json.loads(batch_path.read_text(encoding="utf-8"))
            labels = json.loads(label_path.read_text(encoding="utf-8"))
            if len(sources) != len(labels):
                raise ValueError(f"source/label length mismatch: {batch_path}")
            for source, label in zip(sources, labels, strict=True):
                if source["id"] != label["id"]:
                    raise ValueError(f"source/label id mismatch: {batch_path}")
                if label["keep"]:
                    records.append(
                        {
                            "dataset": dataset_dir.name,
                            "id": source["id"],
                            "title": source.get("title", ""),
                            "body": source.get("body", ""),
                            "text": source["text"],
                            "entities": label["entities"],
                        }
                    )
    if not records:
        raise ValueError("the archive has no keep=true records")
    return records


def _gold_spans(record: dict[str, Any]) -> list[tuple[int, int, str]]:
    """Convert a record's gold entities to typed half-open character spans."""

    return [
        (int(entity["start"]), int(entity["end"]), str(entity["label"]))
        for entity in record["entities"]
    ]


def _prediction_spans(raw_entities: list[dict[str, Any]]) -> list[tuple[int, int, str]]:
    """Normalize pipeline entity aliases and offsets into supported spans."""

    spans = []
    for entity in raw_entities:
        raw_label = str(entity.get("entity_group", entity.get("entity", ""))).upper()
        if "-" in raw_label:
            _, raw_label = raw_label.split("-", maxsplit=1)
        label = "VUL" if raw_label in {"VULID", "VULNAME"} else raw_label
        if label not in LABELS:
            continue
        start = entity.get("start")
        end = entity.get("end")
        if isinstance(start, int) and isinstance(end, int):
            spans.append((start, end, label))
    return spans


def _matches(
    gold: tuple[int, int, str],
    predicted: tuple[int, int, str],
    strict: bool,
    same_label: bool = False,
) -> bool:
    """Check exact span equality or overlap, optionally requiring equal labels."""

    if strict:
        return gold == predicted
    return (
        gold[0] < predicted[1]
        and predicted[0] < gold[1]
        and (not same_label or gold[2] == predicted[2])
    )


def _maximum_matching(
    gold: list[tuple[int, int, str]],
    predicted: list[tuple[int, int, str]],
    strict: bool,
    same_label: bool = False,
) -> int:
    """Return the count of maximum one-to-one compatible span assignments."""

    return len(_matching_pairs(gold, predicted, strict, same_label))


def _matching_pairs(
    gold: list[tuple[int, int, str]],
    predicted: list[tuple[int, int, str]],
    strict: bool,
    same_label: bool = False,
) -> list[tuple[int, int]]:
    """Return gold/prediction index pairs from a maximum bipartite matching."""

    edges = [
        [
            index
            for index, target in enumerate(gold)
            if _matches(target, span, strict, same_label)
        ]
        for span in predicted
    ]
    gold_to_prediction: dict[int, int] = {}

    def visit(prediction_index: int, visited: set[int]) -> bool:
        """Augment the matching recursively through unassigned gold spans."""

        for gold_index in edges[prediction_index]:
            if gold_index in visited:
                continue
            visited.add(gold_index)
            previous = gold_to_prediction.get(gold_index)
            if previous is None or visit(previous, visited):
                gold_to_prediction[gold_index] = prediction_index
                return True
        return False

    for index in range(len(predicted)):
        visit(index, set())
    return [
        (gold_index, prediction_index)
        for gold_index, prediction_index in gold_to_prediction.items()
    ]


def _serialize_spans(
    spans: list[tuple[int, int, str]], text: str
) -> list[dict[str, Any]]:
    """Serialize spans and include their text slice when offsets are valid."""

    return [
        {
            "start": start,
            "end": end,
            "label": label,
            "text": text[start:end] if 0 <= start <= end <= len(text) else None,
        }
        for start, end, label in spans
    ]


def _window_ranges(
    token_count: int, window_size: int, stride: int
) -> list[tuple[int, int]]:
    """Partition token indexes into fixed-size windows with the requested overlap."""

    if token_count <= 0:
        return []
    if window_size <= 0 or stride < 0 or stride >= window_size:
        raise ValueError("stride must be non-negative and less than window_size")
    step = window_size - stride
    ranges = []
    start = 0
    while start < token_count:
        end = min(start + window_size, token_count)
        ranges.append((start, end))
        if end == token_count:
            break
        start += step
    return ranges


def _is_word_start(offset: tuple[int, int], text: str) -> bool:
    """Check whether a tokenizer offset begins at a whitespace-delimited word."""

    start, _ = offset
    return start == 0 or text[start].isspace() or text[start - 1].isspace()


def _aligned_window_ranges(
    offsets: list[tuple[int, int]], text: str, window_size: int, stride: int
) -> list[tuple[int, int]]:
    """Create overlapping token windows whose boundaries align to word starts."""

    if not offsets:
        return []
    ranges = []
    start = 0
    while start < len(offsets):
        end = min(start + window_size, len(offsets))
        while end > start and end < len(offsets) and not _is_word_start(offsets[end], text):
            end -= 1
        if end == start:
            end = min(start + window_size, len(offsets))
        ranges.append((start, end))
        if end == len(offsets):
            break
        start = max(end - stride, start + 1)
        while start < len(offsets) and not _is_word_start(offsets[start], text):
            start += 1
    return ranges


def _sliding_window_predictions(
    tagger: Any, text: str, model_limit: int, stride: int
) -> tuple[list[tuple[int, int, str]], int]:
    """Run a tagger on aligned text windows and restore full-text character offsets."""

    tokenizer = tagger.tokenizer
    if not tokenizer.is_fast:
        raise RuntimeError("manual sliding windows require a fast tokenizer")
    encoded = tokenizer(
        text,
        add_special_tokens=False,
        truncation=False,
        return_offsets_mapping=True,
        verbose=False,
    )
    offsets = encoded["offset_mapping"]
    content_limit = model_limit - tokenizer.num_special_tokens_to_add(pair=False)
    windows = _aligned_window_ranges(offsets, text, content_limit, stride)
    spans: set[tuple[int, int, str]] = set()
    for start, end in windows:
        char_start = offsets[start][0]
        char_end = offsets[end - 1][1]
        window_text = text[char_start:char_end]
        for span_start, span_end, label in _prediction_spans(tagger(window_text)):
            adjusted = (span_start + char_start, span_end + char_start, label)
            if adjusted[0] >= 0 and adjusted[1] <= len(text):
                spans.add(adjusted)
    return sorted(spans), len(windows)


def _postprocess_spans(
    spans: list[tuple[int, int, str]], text: str, policy: str
) -> list[tuple[int, int, str]]:
    """Apply the selected deterministic boundary, merge, and filtering policy."""

    if policy == "none":
        return spans
    ordered = sorted(spans)
    if policy == "expand_words_merge_drop_punctuation_drop_tiny":
        expanded = []
        for start, end, label in ordered:
            if WORD_RE.search(text[start:end]):
                while start > 0 and text[start - 1].isalnum():
                    start -= 1
                while end < len(text) and text[end].isalnum():
                    end += 1
            expanded.append((start, end, label))
        ordered = sorted(set(expanded))
    merged: list[tuple[int, int, str]] = []
    for span in ordered:
        previous = merged[-1] if merged else None
        if previous is not None and previous[2] == span[2]:
            gap = text[previous[1] : span[0]]
            if not gap or all(character.isspace() or not character.isalnum() for character in gap):
                merged[-1] = (previous[0], span[1], previous[2])
                continue
        merged.append(span)
    if policy in {
        "merge_drop_punctuation",
        "merge_drop_punctuation_drop_tiny",
        "expand_words_merge_drop_punctuation_drop_tiny",
    }:
        merged = [span for span in merged if WORD_RE.search(text[span[0] : span[1]])]
    if policy == "merge_drop_punctuation_drop_tiny":
        merged = [span for span in merged if len(text[span[0] : span[1]].strip()) > 2]
    return merged


def _score(
    gold_documents: list[list[tuple[int, int, str]]],
    predicted_documents: list[list[tuple[int, int, str]]],
    strict: bool,
    same_label: bool = False,
) -> dict[str, float | int]:
    """Aggregate one-to-one span matches into precision, recall, and F1 counts."""

    true_positive = sum(
        _maximum_matching(gold, predicted, strict, same_label)
        for gold, predicted in zip(gold_documents, predicted_documents, strict=True)
    )
    total_gold = sum(map(len, gold_documents))
    total_predicted = sum(map(len, predicted_documents))
    false_positive = total_predicted - true_positive
    false_negative = total_gold - true_positive
    precision = true_positive / total_predicted if total_predicted else 0.0
    recall = true_positive / total_gold if total_gold else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "true_positive": true_positive,
        "false_positive": false_positive,
        "false_negative": false_negative,
        "precision": precision,
        "recall": recall,
        "f1": f1,
    }


def _score_by_dataset(
    records: list[dict[str, Any]], predictions: list[list[tuple[int, int, str]]], strict: bool
) -> dict[str, dict[str, float | int]]:
    """Compute span metrics independently for each source dataset."""

    result: dict[str, dict[str, float | int]] = {}
    for dataset in sorted({record["dataset"] for record in records}):
        indices = [index for index, record in enumerate(records) if record["dataset"] == dataset]
        result[dataset] = _score(
            [_gold_spans(records[index]) for index in indices],
            [predictions[index] for index in indices],
            strict,
        )
    return result


def _truncate_record(
    record: dict[str, Any], tokenizer: Any, limit: int
) -> tuple[dict[str, Any], int]:
    """Truncate text to a content-token limit and retain only complete gold spans."""

    encoded = tokenizer(
        record["text"],
        add_special_tokens=False,
        truncation=False,
        return_offsets_mapping=True,
        verbose=False,
    )
    offsets = encoded["offset_mapping"]
    if len(offsets) <= limit:
        return record, len(offsets)
    cut = offsets[limit - 1][1]
    entities = [
        entity
        for entity in record["entities"]
        if int(entity["end"]) <= cut
    ]
    return {**record, "text": record["text"][:cut], "entities": entities}, len(offsets)


def run_model(
    name: str,
    repository: str,
    revision: str,
    records: list[dict[str, Any]],
    stride: int,
    aggregation_strategy: str = "simple",
    truncate_tokens: int | None = None,
    span_postprocess: str = "none",
    document_diagnostics: list[dict[str, Any]] | None = None,
    detailed_diagnostics: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Run one model with overlapping windows and optionally collect diagnostics."""

    import torch
    from transformers import AutoTokenizer, pipeline

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is unavailable; this runner requires a Colab T4")
    started = time.perf_counter()
    torch.cuda.reset_peak_memory_stats()
    tokenizer = AutoTokenizer.from_pretrained(repository, revision=revision, use_fast=True)
    tagger = pipeline(
        "token-classification",
        model=repository,
        revision=revision,
        tokenizer=tokenizer,
        aggregation_strategy=aggregation_strategy,
        device=0,
    )
    model_limit = int(getattr(tagger.tokenizer, "model_max_length", 512))
    if model_limit > 100_000:
        model_limit = int(getattr(tagger.model.config, "max_position_embeddings", 512))
    if truncate_tokens is not None:
        truncated: list[dict[str, Any]] = []
        for record in records:
            truncated_record, _ = _truncate_record(
                record, tagger.tokenizer, truncate_tokens
            )
            truncated.append(truncated_record)
        records = truncated
        print(
            f"{name}: truncated to {truncate_tokens} tokens; "
            f"gold={sum(len(record['entities']) for record in records)}",
            flush=True,
        )
    gold = [_gold_spans(record) for record in records]
    predictions: list[list[tuple[int, int, str]]] = []
    token_lengths: list[int] = []
    token_lengths_by_document: list[int | None] = []
    window_counts_by_document: list[int | None] = []
    for index, record in enumerate(records, start=1):
        encoded = tagger.tokenizer(
            record["text"], add_special_tokens=True, truncation=False, verbose=False
        )
        token_length = len(encoded["input_ids"])
        token_lengths.append(token_length)
        document_predictions, window_count = _sliding_window_predictions(
            tagger, record["text"], model_limit, stride
        )
        document_predictions = _postprocess_spans(
            document_predictions, record["text"], span_postprocess
        )
        predictions.append(document_predictions)
        token_lengths_by_document.append(token_length)
        window_counts_by_document.append(window_count)
        failure_type = None
        if index % 100 == 0:
            print(f"{name}: {index}/{len(records)}", flush=True)
    result: dict[str, Any] = {
        "model": name,
        "repository": repository,
        "revision": revision,
        "documents_attempted": len(records),
        "documents_processed": len(records),
        "failure_types": {},
        "model_max_tokens": model_limit,
        "window_stride": stride,
        "aggregation_strategy": aggregation_strategy,
        "truncate_tokens": truncate_tokens,
        "span_postprocess": span_postprocess,
        "inference_overflow_policy": "manual_word_aligned_overlapping_windows",
        "documents_over_model_limit": sum(length > model_limit for length in token_lengths),
        "token_length_max": max(token_lengths, default=0),
        "predicted_entities": sum(map(len, predictions)),
        "predicted_label_counts": dict(
            Counter(label for document in predictions for _, _, label in document)
        ),
        "strict": _score(gold, predictions, strict=True),
        "partial": _score(gold, predictions, strict=False),
        "partial_same_type": _score(gold, predictions, strict=False, same_label=True),
        "strict_by_dataset": _score_by_dataset(records, predictions, strict=True),
        "partial_by_dataset": _score_by_dataset(records, predictions, strict=False),
        "seconds": round(time.perf_counter() - started, 2),
        "peak_gpu_memory_mib": round(torch.cuda.max_memory_allocated() / 1024**2, 1),
    }
    if document_diagnostics is not None:
        for index, (record, gold_spans, predicted_spans) in enumerate(
            zip(records, gold, predictions, strict=True)
        ):
            strict = _score([gold_spans], [predicted_spans], strict=True)
            partial = _score([gold_spans], [predicted_spans], strict=False)
            partial_same_type = _score(
                [gold_spans], [predicted_spans], strict=False, same_label=True
            )
            document_diagnostics.append(
                {
                    "id": record["id"],
                    "text_characters": len(record["text"]),
                    "text_words": len(record["text"].split()),
                    "title_characters": len(str(record.get("title", ""))),
                    "body_characters": len(str(record.get("body", ""))),
                    "token_length": token_lengths_by_document[index],
                    "window_count": window_counts_by_document[index],
                    "gold_entities": len(gold_spans),
                    "predicted_entities": len(predicted_spans),
                    "gold_label_counts": dict(Counter(label for _, _, label in gold_spans)),
                    "predicted_label_counts": dict(
                        Counter(label for _, _, label in predicted_spans)
                    ),
                    "strict_true_positive": strict["true_positive"],
                    "partial_true_positive": partial["true_positive"],
                    "partial_same_type_true_positive": partial_same_type["true_positive"],
                    "failure_type": failure_type,
                }
            )
    if detailed_diagnostics is not None:
        for index, (record, gold_spans, predicted_spans) in enumerate(
            zip(records, gold, predictions, strict=True)
        ):
            detailed_diagnostics.append(
                {
                    "id": record["id"],
                    "text": record["text"],
                    "gold_spans": _serialize_spans(gold_spans, record["text"]),
                    "predicted_spans": _serialize_spans(predicted_spans, record["text"]),
                    "strict_matches": [
                        {"gold": gold_index, "predicted": predicted_index}
                        for gold_index, predicted_index in _matching_pairs(
                            gold_spans, predicted_spans, strict=True
                        )
                    ],
                    "partial_matches": [
                        {"gold": gold_index, "predicted": predicted_index}
                        for gold_index, predicted_index in _matching_pairs(
                            gold_spans, predicted_spans, strict=False
                        )
                    ],
                    "partial_same_type_matches": [
                        {"gold": gold_index, "predicted": predicted_index}
                        for gold_index, predicted_index in _matching_pairs(
                            gold_spans, predicted_spans, strict=False, same_label=True
                        )
                    ],
                    "token_length": token_lengths_by_document[index],
                    "window_count": window_counts_by_document[index],
                    "failure_type": failure_type,
                }
            )
    return result


def main() -> None:
    """Load the archive, run configured models, and write aggregate/private outputs."""

    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path, default=Path("/content/muse_batches.tar.gz"))
    parser.add_argument(
        "--output",
        type=Path,
        default=(
            Path(os.environ["MUSE_VALIDATION_OUTPUT"])
            if os.environ.get("MUSE_VALIDATION_OUTPUT")
            else Path("/content/muse_validation.json")
        ),
    )
    parser.add_argument(
        "--annotation-status",
        default=os.environ.get(
            "MUSE_ANNOTATION_STATUS", "silver_muse_review_pass4"
        ),
        help="Annotation layer identifier recorded in the result artifact",
    )
    parser.add_argument(
        "--diagnostic-output",
        type=Path,
        default=(
            Path(os.environ["MUSE_DIAGNOSTIC_OUTPUT"])
            if os.environ.get("MUSE_DIAGNOSTIC_OUTPUT")
            else None
        ),
        help="Optional private per-document counts; never includes text or spans",
    )
    parser.add_argument(
        "--detailed-output",
        type=Path,
        default=(
            Path(os.environ["MUSE_DETAILED_OUTPUT"])
            if os.environ.get("MUSE_DETAILED_OUTPUT")
            else None
        ),
        help="Optional private per-document text and span comparisons",
    )
    parser.add_argument("--stride", type=int, default=128)
    parser.add_argument(
        "--aggregation-strategy",
        choices=("simple", "first", "average", "max"),
        default=os.environ.get("MUSE_AGGREGATION_STRATEGY", "simple"),
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=(
            int(os.environ["MUSE_DOCUMENT_LIMIT"])
            if os.environ.get("MUSE_DOCUMENT_LIMIT")
            else None
        ),
    )
    parser.add_argument(
        "--truncate-tokens",
        type=int,
        default=(
            int(os.environ["MUSE_TRUNCATE_TOKENS"])
            if os.environ.get("MUSE_TRUNCATE_TOKENS")
            else None
        ),
        help="Content-token truncation applied before scoring (paper protocol)",
    )
    parser.add_argument(
        "--span-postprocess",
        choices=(
            "none",
            "merge_contiguous",
            "merge_drop_punctuation",
            "merge_drop_punctuation_drop_tiny",
            "expand_words_merge_drop_punctuation_drop_tiny",
        ),
        default=os.environ.get("MUSE_SPAN_POSTPROCESS", "none"),
    )
    args, _ = parser.parse_known_args()
    if args.stride < 1:
        parser.error("--stride must be positive")
    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be positive")
    if args.truncate_tokens is not None and args.truncate_tokens < 1:
        parser.error("--truncate-tokens must be positive")

    import datasets
    import torch
    import transformers

    workdir = Path("/content/muse_batches_extracted")
    _extract_archive(args.archive, workdir)
    records = _load_records(workdir / "muse_batches")
    if args.limit is not None:
        records = records[: args.limit]
    gold_counts = Counter(
        entity["label"] for record in records for entity in record["entities"]
    )
    result: dict[str, Any] = {
        "experiment_status": "extension",
        "annotation_status": args.annotation_status,
        "dataset_source": "local_muse_batches_archive",
        "archive_sha256": hashlib.sha256(args.archive.read_bytes()).hexdigest(),
        "documents": len(records),
        "document_counts": dict(Counter(record["dataset"] for record in records)),
        "gold_label_counts": dict(gold_counts),
        "runtime": {
            "python": platform.python_version(),
            "torch": torch.__version__,
            "cuda": torch.version.cuda,
            "transformers": transformers.__version__,
            "datasets": datasets.__version__,
            "gpu": torch.cuda.get_device_name(0),
        },
        "models": [],
    }
    diagnostics: dict[str, list[dict[str, Any]]] = {}
    detailed: dict[str, list[dict[str, Any]]] = {}
    for name, (repository, revision) in MODELS.items():
        model_diagnostics = [] if args.diagnostic_output is not None else None
        model_detailed = [] if args.detailed_output is not None else None
        result["models"].append(
            run_model(
                name,
                repository,
                revision,
                records,
                args.stride,
                args.aggregation_strategy,
                args.truncate_tokens,
                args.span_postprocess,
                model_diagnostics,
                model_detailed,
            )
        )
        if model_diagnostics is not None:
            diagnostics[name] = model_diagnostics
        if model_detailed is not None:
            detailed[name] = model_detailed
        torch.cuda.empty_cache()
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    if args.diagnostic_output is not None:
        args.diagnostic_output.write_text(
            json.dumps(
                {
                    "experiment_status": result["experiment_status"],
                    "annotation_status": result["annotation_status"],
                    "archive_sha256": result["archive_sha256"],
                    "documents": result["documents"],
                    "models": diagnostics,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
    if args.detailed_output is not None:
        documents: dict[str, dict[str, Any]] = {}
        for model_name, model_records in detailed.items():
            for model_record in model_records:
                identifier = model_record["id"]
                document = documents.setdefault(
                    identifier,
                    {
                        "id": identifier,
                        "text": model_record["text"],
                        "gold_spans": model_record["gold_spans"],
                        "models": {},
                    },
                )
                document["models"][model_name] = {
                    key: value
                    for key, value in model_record.items()
                    if key not in {"id", "text", "gold_spans"}
                }
        args.detailed_output.write_text(
            json.dumps(
                {
                    "experiment_status": result["experiment_status"],
                    "annotation_status": result["annotation_status"],
                    "archive_sha256": result["archive_sha256"],
                    "documents": list(documents.values()),
                },
                indent=2,
            ),
            encoding="utf-8",
        )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
