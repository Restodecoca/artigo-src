"""Run SecureBERT 2.0 NER on the local Muse corpus in Colab.

The model uses a different entity taxonomy from the paper. The output keeps
its native label counts and reports a clearly scoped compatibility score only
for Organization -> IDTY and Vulnerability -> VUL.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import tarfile
import time
from collections import Counter
from pathlib import Path
from typing import Any

MODEL = "cisco-ai/SecureBERT2.0-NER"
REVISION = "792db5b533118afee8c3fab86db119d09ab77ff6"
COMPATIBLE_LABELS = {"Organization": "IDTY", "Vulnerability": "VUL"}


def _extract_archive(archive: Path, destination: Path) -> None:
    """Extract a Muse batch archive into the Colab working directory."""

    destination.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive, "r:gz") as handle:
        handle.extractall(destination, filter="data")


def _load_records(root: Path) -> list[dict[str, Any]]:
    """Read retained documents and labels from extracted dataset batches."""

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


def _spans(
    entities: list[dict[str, Any]], mapping: dict[str, str] | None = None
) -> list[tuple[int, int, str]]:
    """Normalize model outputs to typed spans, applying an optional label map."""

    spans = []
    for entity in entities:
        label = str(entity.get("entity_group", entity.get("entity", "")))
        label = label.removeprefix("B-").removeprefix("I-")
        if mapping is not None:
            label = mapping.get(label, "")
        if label and isinstance(entity.get("start"), int) and isinstance(entity.get("end"), int):
            spans.append((entity["start"], entity["end"], label))
    return spans


def _gold(record: dict[str, Any], labels: set[str] | None = None) -> list[tuple[int, int, str]]:
    """Return gold spans, optionally restricted to comparable entity types."""

    return [
        (int(entity["start"]), int(entity["end"]), str(entity["label"]))
        for entity in record["entities"]
        if labels is None or entity["label"] in labels
    ]


def _matching_pairs(
    gold: list[tuple[int, int, str]],
    predicted: list[tuple[int, int, str]],
    strict: bool,
    same_label: bool = False,
) -> list[tuple[int, int]]:
    """Pair gold and predicted spans one-to-one under strict or overlap matching."""

    edges = [
        [
            index
            for index, target in enumerate(gold)
            if (
                (target == span if strict else target[0] < span[1] and span[0] < target[1])
                and (not same_label or target[2] == span[2])
            )
        ]
        for span in predicted
    ]
    gold_to_prediction: dict[int, int] = {}

    def visit(prediction_index: int, visited: set[int]) -> bool:
        """Find a compatible gold span, reassigning an earlier match if necessary."""

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


def _score(
    gold: list[list[tuple[int, int, str]]],
    predicted: list[list[tuple[int, int, str]]],
    strict: bool,
) -> dict[str, float | int]:
    """Aggregate span counts and precision/recall/F1 across documents."""

    true_positive = sum(
        len(_matching_pairs(expected, actual, strict))
        for expected, actual in zip(gold, predicted, strict=True)
    )
    total_gold = sum(map(len, gold))
    total_predicted = sum(map(len, predicted))
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


def _serialize_spans(
    spans: list[tuple[int, int, str]], text: str
) -> list[dict[str, Any]]:
    """Serialize spans with offsets, labels, and valid text slices."""

    return [
        {
            "start": start,
            "end": end,
            "label": label,
            "text": text[start:end] if 0 <= start <= end <= len(text) else None,
        }
        for start, end, label in spans
    ]


def _native_spans(entities: list[dict[str, Any]], text: str) -> list[dict[str, Any]]:
    """Serialize all native model spans without restricting the label taxonomy."""

    spans = []
    for entity in entities:
        label = str(entity.get("entity_group", entity.get("entity", "")))
        label = label.removeprefix("B-").removeprefix("I-")
        start = entity.get("start")
        end = entity.get("end")
        if label and isinstance(start, int) and isinstance(end, int):
            spans.append(
                {
                    "start": start,
                    "end": end,
                    "label": label,
                    "text": text[start:end] if 0 <= start <= end <= len(text) else None,
                }
            )
    return spans


def main() -> None:
    """Run SecureBERT 2.0 and report native and compatible-label metrics."""

    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path, default=Path("/content/muse_batches.tar.gz"))
    parser.add_argument(
        "--output",
        type=Path,
        default=(
            Path(os.environ["SECUREBERT2_OUTPUT"])
            if os.environ.get("SECUREBERT2_OUTPUT")
            else Path("/content/securebert2_muse.json")
        ),
    )
    parser.add_argument(
        "--aggregation-strategy",
        choices=("simple", "first", "average", "max"),
        default=os.environ.get("SECUREBERT2_AGGREGATION_STRATEGY", "simple"),
    )
    parser.add_argument(
        "--detailed-output",
        type=Path,
        default=(
            Path(os.environ["SECUREBERT2_DETAILED_OUTPUT"])
            if os.environ.get("SECUREBERT2_DETAILED_OUTPUT")
            else None
        ),
    )
    args, _ = parser.parse_known_args()

    import torch
    import transformers
    from transformers import pipeline

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is unavailable; this runner requires a Colab GPU")
    workdir = Path("/content/muse_batches_extracted")
    _extract_archive(args.archive, workdir)
    records = _load_records(workdir / "muse_batches")
    tagger = pipeline(
        "token-classification",
        model=MODEL,
        revision=REVISION,
        aggregation_strategy=args.aggregation_strategy,
        device=0,
    )
    model_limit = int(getattr(tagger.tokenizer, "model_max_length", 512))
    if model_limit > 100_000:
        model_limit = int(getattr(tagger.model.config, "max_position_embeddings", 512))
    started = time.perf_counter()
    raw_predictions: list[list[dict[str, Any]]] = []
    token_lengths: list[int] = []
    for record in records:
        encoded = tagger.tokenizer(record["text"], truncation=False)
        token_lengths.append(len(encoded["input_ids"]))
        raw_predictions.append(tagger(record["text"]))
    mapped_predictions = [_spans(prediction, COMPATIBLE_LABELS) for prediction in raw_predictions]
    gold = [_gold(record, set(COMPATIBLE_LABELS.values())) for record in records]
    result = {
        "experiment_status": "extension",
        "annotation_status": "silver_muse_review_pass4",
        "model": MODEL,
        "revision": REVISION,
        "aggregation_strategy": args.aggregation_strategy,
        "model_taxonomy": ["Indicator", "Malware", "Organization", "System", "Vulnerability"],
        "compatibility_mapping": COMPATIBLE_LABELS,
        "compatibility_warning": "ACT and LOC are not mapped; scores cover only IDTY and VUL.",
        "archive_sha256": hashlib.sha256(args.archive.read_bytes()).hexdigest(),
        "documents_attempted": len(records),
        "documents_processed": len(records),
        "failure_types": {},
        "model_max_tokens": model_limit,
        "documents_over_model_limit": sum(length > model_limit for length in token_lengths),
        "token_length_max": max(token_lengths, default=0),
        "native_label_counts": dict(
            Counter(
                str(entity.get("entity_group", entity.get("entity", "")))
                .removeprefix("B-")
                .removeprefix("I-")
                for prediction in raw_predictions
                for entity in prediction
            )
        ),
        "compatible_exact": _score(gold, mapped_predictions, strict=True),
        "compatible_partial": _score(gold, mapped_predictions, strict=False),
        "runtime": {
            "python": platform.python_version(),
            "torch": torch.__version__,
            "transformers": transformers.__version__,
            "gpu": torch.cuda.get_device_name(0),
            "seconds": round(time.perf_counter() - started, 2),
            "peak_gpu_memory_mib": round(torch.cuda.max_memory_allocated() / 1024**2, 1),
        },
    }
    if args.detailed_output is not None:
        result["detailed_output"] = str(args.detailed_output)
        result["documents_detail"] = []
        for record, expected, raw, actual in zip(
            records, gold, raw_predictions, mapped_predictions, strict=True
        ):
            all_gold = _gold(record)
            compatible_gold_indices = [
                index
                for index, span in enumerate(all_gold)
                if span[2] in COMPATIBLE_LABELS.values()
            ]
            strict_pairs = _matching_pairs(expected, actual, strict=True)
            partial_pairs = _matching_pairs(expected, actual, strict=False)
            partial_same_type_pairs = _matching_pairs(
                expected, actual, strict=False, same_label=True
            )
            result["documents_detail"].append(
                {
                    "id": record["id"],
                    "text": record["text"],
                    "gold_spans": _serialize_spans(all_gold, record["text"]),
                    "predicted_spans": _serialize_spans(actual, record["text"]),
                    "native_predicted_spans": _native_spans(raw, record["text"]),
                    "strict_matches": [
                        {
                            "gold": compatible_gold_indices[gold_index],
                            "predicted": predicted_index,
                        }
                        for gold_index, predicted_index in strict_pairs
                    ],
                    "partial_matches": [
                        {
                            "gold": compatible_gold_indices[gold_index],
                            "predicted": predicted_index,
                        }
                        for gold_index, predicted_index in partial_pairs
                    ],
                    "partial_same_type_matches": [
                        {
                            "gold": compatible_gold_indices[gold_index],
                            "predicted": predicted_index,
                        }
                        for gold_index, predicted_index in partial_same_type_pairs
                    ],
                }
            )
        detailed_payload = {
            "model": MODEL,
            "compatible_labels": sorted(COMPATIBLE_LABELS.values()),
            "documents": [
                {
                    "id": document["id"],
                    "text": document["text"],
                    "gold_spans": document["gold_spans"],
                    "models": {
                        MODEL: {
                            "predicted_spans": document["predicted_spans"],
                            "native_predicted_spans": document["native_predicted_spans"],
                            "strict_matches": document["strict_matches"],
                            "partial_matches": document["partial_matches"],
                            "partial_same_type_matches": document[
                                "partial_same_type_matches"
                            ],
                            "token_length": None,
                            "window_count": 1,
                        }
                    },
                }
                for document in result.pop("documents_detail")
            ]
        }
        args.detailed_output.write_text(
            json.dumps(detailed_payload, indent=2), encoding="utf-8"
        )
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
