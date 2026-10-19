"""Run a bounded external-validation probe on a Colab GPU runtime."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import random
import time
from collections import Counter
from datetime import date
from pathlib import Path

DATASET = "mrmoor/cyber-threat-intelligence"
DATASET_REVISION = "d8783e04f46039f3624df6958dd4d34405d8c72a"
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
LABEL_ALIASES = {
    "identity": "IDTY",
    "attack-pattern": "ACT",
    "vulnerability": "VUL",
    "location": "LOC",
}
MODEL_LABEL_ALIASES = {"VULID": "VUL", "VULNAME": "VUL"}


def normalize_gold(raw_entities: list[dict[str, object]]) -> list[tuple[int, int, str]]:
    spans = []
    for entity in raw_entities:
        label = LABEL_ALIASES.get(str(entity.get("label", "")).strip().lower())
        if label is None:
            continue
        spans.append((int(entity["start_offset"]), int(entity["end_offset"]), label))
    return spans


def normalize_prediction(raw_entities: list[dict[str, object]]) -> list[tuple[int, int, str]]:
    spans = []
    current: list[int | str] | None = None

    def flush() -> None:
        nonlocal current
        if current is not None:
            spans.append((int(current[0]), int(current[1]), str(current[2])))
            current = None

    for entity in raw_entities:
        raw_label = str(entity.get("entity_group", entity.get("entity", ""))).strip().upper()
        if raw_label == "O":
            flush()
            continue
        prefix, separator, label = raw_label.partition("-")
        if not separator:
            prefix, label = "I", raw_label
        label = MODEL_LABEL_ALIASES.get(label, label)
        if label not in {"IDTY", "ACT", "VUL", "LOC"}:
            flush()
            continue
        start = int(entity["start"])
        end = int(entity["end"])
        if prefix in {"B", "S"} or current is None or current[2] != label:
            flush()
            current = [start, end, label]
        else:
            current[1] = end
        if prefix in {"E", "S"}:
            flush()
    flush()
    return spans


def maximum_overlap(
    gold: list[tuple[int, int, str]], predicted: list[tuple[int, int, str]], strict: bool
) -> int:
    edges = []
    for prediction in predicted:
        compatible_gold = []
        for gold_index, target in enumerate(gold):
            same_span = prediction[:2] == target[:2] and prediction[2] == target[2]
            overlaps = target[0] < prediction[1] and prediction[0] < target[1]
            matches = same_span if strict else overlaps
            if matches:
                compatible_gold.append(gold_index)
        edges.append(compatible_gold)

    gold_to_prediction: dict[int, int] = {}

    def visit(prediction_index: int, visited: set[int]) -> bool:
        for gold_index in edges[prediction_index]:
            if gold_index in visited:
                continue
            visited.add(gold_index)
            previous_prediction = gold_to_prediction.get(gold_index)
            if previous_prediction is None or visit(previous_prediction, visited):
                gold_to_prediction[gold_index] = prediction_index
                return True
        return False

    return sum(visit(index, set()) for index in range(len(predicted)))


def score_documents(
    gold_documents: list[list[tuple[int, int, str]]],
    predicted_documents: list[list[tuple[int, int, str]]],
    strict: bool,
) -> dict[str, float | int]:
    true_positive = sum(
        maximum_overlap(gold, predicted, strict)
        for gold, predicted in zip(gold_documents, predicted_documents, strict=True)
    )
    total_gold = sum(len(document) for document in gold_documents)
    total_predicted = sum(len(document) for document in predicted_documents)
    false_positive = total_predicted - true_positive
    false_negative = total_gold - true_positive
    precision = (
        true_positive / (true_positive + false_positive) if true_positive + false_positive else 0.0
    )
    recall = (
        true_positive / (true_positive + false_negative) if true_positive + false_negative else 0.0
    )
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "true_positive": true_positive,
        "false_positive": false_positive,
        "false_negative": false_negative,
        "precision": precision,
        "recall": recall,
        "f1": f1,
    }


def select_examples(limit: int, seed: int) -> tuple[list[dict[str, object]], int, str]:
    from datasets import load_dataset

    dataset = load_dataset(DATASET, revision=DATASET_REVISION, split="train")
    candidates = [
        row for row in dataset if normalize_gold(row["entities"]) and len(row["text"]) > 0
    ]
    random.Random(seed).shuffle(candidates)
    selected = candidates[:limit]
    if len(selected) < limit:
        raise RuntimeError(f"Only {len(selected)} annotated rows were available")
    sample_ids = "|".join(str(row["id"]) for row in selected)
    sample_hash = hashlib.sha256(sample_ids.encode()).hexdigest()
    return selected, len(candidates), sample_hash


def run_model(
    model_name: str,
    repository: str,
    revision: str,
    examples: list[dict[str, object]],
) -> dict[str, object]:
    import torch
    from transformers import pipeline

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is not available")
    torch.cuda.reset_peak_memory_stats()
    started = time.perf_counter()
    tagger = pipeline(
        "token-classification",
        model=repository,
        revision=revision,
        aggregation_strategy="none",
        device=0,
    )
    gold_documents = [normalize_gold(row["entities"]) for row in examples]
    predicted_documents = []
    for index, row in enumerate(examples, start=1):
        predicted_documents.append(normalize_prediction(tagger(row["text"])))
        if index % 10 == 0:
            print(f"{model_name}: {index}/{len(examples)}", flush=True)
    elapsed = time.perf_counter() - started
    return {
        "model": model_name,
        "repository": repository,
        "revision": revision,
        "documents": len(examples),
        "gold_label_counts": dict(Counter(span[2] for doc in gold_documents for span in doc)),
        "strict": score_documents(gold_documents, predicted_documents, strict=True),
        "partial": score_documents(gold_documents, predicted_documents, strict=False),
        "seconds": round(elapsed, 2),
        "peak_gpu_memory_mib": round(torch.cuda.max_memory_allocated() / 1024**2, 1),
    }


def main() -> None:
    import datasets as datasets_lib
    import torch
    import transformers

    limit = int(os.getenv("LIMIT", "60"))
    seed = int(os.getenv("SEED", "42"))
    output = Path(os.getenv("OUTPUT", "/content/healthcare_ner_validation.json"))
    examples, candidate_pool_size, sample_hash = select_examples(limit, seed)
    result = {
        "experiment_status": "extension",
        "dataset": DATASET,
        "dataset_revision": DATASET_REVISION,
        "source_license": "CC-BY-4.0",
        "access_date": date.today().isoformat(),
        "redistribution": "Aggregate metrics only; raw source text is not stored.",
        "max_tokens_per_document": None,
        "token_limit_applied": False,
        "selection": {
            "split": "train",
            "candidate_pool_size": candidate_pool_size,
            "filter": "non-empty text with at least one mapped target entity",
            "sample_id_sha256": sample_hash,
        },
        "runtime": {
            "python": platform.python_version(),
            "torch": torch.__version__,
            "cuda": torch.version.cuda,
            "transformers": transformers.__version__,
            "datasets": datasets_lib.__version__,
            "gpu": torch.cuda.get_device_name(0),
        },
        "seed": seed,
        "documents": limit,
        "gold_label_counts": dict(
            Counter(span[2] for row in examples for span in normalize_gold(row["entities"]))
        ),
        "models": [],
    }
    print(
        json.dumps({"dataset": DATASET, "documents": limit, "cuda": torch.cuda.get_device_name(0)})
    )
    for model_name, (repository, revision) in MODELS.items():
        result["models"].append(run_model(model_name, repository, revision, examples))
        torch.cuda.empty_cache()
    output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
