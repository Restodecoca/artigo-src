"""Probe five text records from a Hugging Face candidate on a Colab GPU.

The probe reports only text fingerprints, lengths, and aggregate model output.
It never prints or writes source text, spans, or per-document predictions.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import time
from collections import Counter
from collections.abc import Iterable, Mapping
from datetime import date
from pathlib import Path
from typing import TypedDict

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


class PredictionSummary(TypedDict):
    target_entity_count: int
    documents_with_target_entities: int
    target_label_counts: dict[str, int]


def build_dataset_kwargs(
    path: str, name: str | None, split: str, revision: str | None = None
) -> dict[str, str | None]:
    """Build explicit ``datasets.load_dataset`` arguments for a candidate."""

    kwargs: dict[str, str | None] = {"path": path, "split": split, "revision": revision}
    if name is not None:
        kwargs["name"] = name
    return kwargs


def validate_probe_limit(limit: int) -> int:
    """Require the fixed five-record bound used by this feasibility probe."""

    if limit != 5:
        raise ValueError("The candidate probe requires exactly 5 records")
    return limit


def _select_text_records(
    rows: Iterable[Mapping[str, object]], text_column: str, limit: int
) -> list[tuple[int, str]]:
    records: list[tuple[int, str]] = []
    for source_index, row in enumerate(rows):
        value = row.get(text_column)
        if not isinstance(value, str):
            continue
        text = value.strip()
        if not text:
            continue
        records.append((source_index, text))
        if len(records) == limit:
            break
    if len(records) < limit:
        raise ValueError(f"Only {len(records)} non-empty records found; need {limit}")
    return records


def _record_metadata(records: Iterable[tuple[int, str]]) -> dict[str, int | str]:
    texts = [text for _, text in records]
    character_counts = [len(text) for text in texts]
    word_counts = [len(text.split()) for text in texts]
    sample = "\n".join(texts).encode("utf-8")
    return {
        "documents": len(texts),
        "characters_total": sum(character_counts),
        "characters_min": min(character_counts),
        "characters_max": max(character_counts),
        "words_total": sum(word_counts),
        "words_min": min(word_counts),
        "words_max": max(word_counts),
        "sample_sha256": hashlib.sha256(sample).hexdigest(),
    }


def select_first_nonempty_texts(
    rows: Iterable[Mapping[str, object]], text_column: str, limit: int
) -> dict[str, int | str]:
    """Select source-order records and return aggregate metadata only."""

    return _record_metadata(_select_text_records(rows, text_column, limit))


def _canonical_label(value: object) -> str | None:
    label = str(value).strip().upper()
    if "-" in label:
        _, label = label.split("-", maxsplit=1)
    if label in {"VUL", "VULID", "VULNAME"}:
        return "VUL"
    if label in {"IDTY", "ACT", "LOC"}:
        return label
    return None


def _summarize_prediction(raw_entities: Iterable[Mapping[str, object]]) -> PredictionSummary:
    labels = [
        label
        for entity in raw_entities
        if (label := _canonical_label(entity.get("entity_group", entity.get("entity")))) is not None
    ]
    return {
        "target_entity_count": len(labels),
        "documents_with_target_entities": int(bool(labels)),
        "target_label_counts": dict(Counter(labels)),
    }


def run_model(
    model_name: str,
    repository: str,
    revision: str,
    texts: list[str],
) -> dict[str, object]:
    import torch
    from transformers import pipeline

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is not available; this probe requires the Colab T4")
    torch.cuda.reset_peak_memory_stats()
    started = time.perf_counter()
    tagger = pipeline(
        "token-classification",
        model=repository,
        revision=revision,
        aggregation_strategy="simple",
        device=0,
    )
    total_entities = 0
    documents_with_entities = 0
    label_counts: Counter[str] = Counter()
    for text in texts:
        summary = _summarize_prediction(tagger(text))
        total_entities += int(summary["target_entity_count"])
        documents_with_entities += int(summary["documents_with_target_entities"])
        label_counts.update(summary["target_label_counts"])
    return {
        "model": model_name,
        "repository": repository,
        "revision": revision,
        "documents": len(texts),
        "target_entity_count": total_entities,
        "documents_with_target_entities": documents_with_entities,
        "target_label_counts": dict(label_counts),
        "seconds": round(time.perf_counter() - started, 2),
        "peak_gpu_memory_mib": round(torch.cuda.max_memory_allocated() / 1024**2, 1),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default=os.environ.get("DATASET"))
    parser.add_argument("--text-column", default=os.environ.get("TEXT_COLUMN"))
    parser.add_argument("--split", default=os.environ.get("SPLIT", "train"))
    parser.add_argument("--config", default=os.environ.get("CONFIG"))
    parser.add_argument("--revision", default=os.environ.get("REVISION"))
    parser.add_argument("--limit", type=int, default=int(os.environ.get("LIMIT", "5")))
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(os.environ.get("OUTPUT", "/content/candidate_probe.json")),
    )
    args, _ = parser.parse_known_args()

    if not args.dataset or not args.text_column:
        parser.error("--dataset and --text-column are required, directly or via environment")

    import datasets as datasets_lib
    import torch
    import transformers
    from datasets import load_dataset

    validate_probe_limit(args.limit)
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is not available; request a T4 with the Colab CLI")

    dataset = load_dataset(
        **build_dataset_kwargs(args.dataset, args.config, args.split, args.revision)
    )
    records = _select_text_records(dataset, args.text_column, args.limit)
    texts = [text for _, text in records]
    model_results: list[dict[str, object]] = []
    result: dict[str, object] = {
        "experiment_status": "extension",
        "probe": "first_nonempty_source_order_records",
        "dataset": args.dataset,
        "dataset_revision": args.revision,
        "config": args.config,
        "split": args.split,
        "text_column": args.text_column,
        "source_license": "See data/SEARCH_LOG.md; probe does not grant redistribution rights.",
        "access_date": date.today().isoformat(),
        "redistribution": "Metadata and aggregate model counts only; no raw text or predictions.",
        "sample": _record_metadata(records),
        "runtime": {
            "python": platform.python_version(),
            "torch": torch.__version__,
            "cuda": torch.version.cuda,
            "transformers": transformers.__version__,
            "datasets": datasets_lib.__version__,
            "gpu": torch.cuda.get_device_name(0),
        },
        "models": model_results,
    }
    print(
        json.dumps(
            {
                "dataset": args.dataset,
                "records": args.limit,
                "gpu": torch.cuda.get_device_name(0),
            }
        ),
        flush=True,
    )
    for model_name, (repository, revision) in MODELS.items():
        model_results.append(run_model(model_name, repository, revision, texts))
        torch.cuda.empty_cache()
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
