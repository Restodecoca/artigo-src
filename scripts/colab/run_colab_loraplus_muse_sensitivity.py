"""Run a paired LoRA+ fine-tuning sensitivity experiment on Colab T4."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import random
import tarfile
from collections import Counter
from pathlib import Path
from typing import Any

MODEL = "CyberPeace-Institute/SecureBERT-NER"
REVISION = "7f935a4f7db13697580c881e381bb2636dfa779a"
ENTITY_TYPES = ("IDTY", "ACT", "VUL", "LOC")
LABELS = ("O", *tuple(prefix + "-" + label for label in ENTITY_TYPES for prefix in ("B", "I")))
LABEL_TO_ID = {label: index for index, label in enumerate(LABELS)}


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_archive(path: Path) -> dict[str, dict[str, Any]]:
    with tarfile.open(path, "r:gz") as archive:
        members = {member.name: member for member in archive.getmembers()}
        source_members = [
            member for member in members.values() if Path(member.name).name.startswith("batch_")
        ]
        records: dict[str, dict[str, Any]] = {}
        for source_member in source_members:
            parent, filename = source_member.name.rsplit("/", maxsplit=1)
            label_name = f"{parent}/{filename.replace('batch_', 'labels_batch_')}"
            label_member = members.get(label_name)
            if label_member is None:
                raise ValueError(f"missing labels for {source_member.name}")
            sources = json.loads(archive.extractfile(source_member).read())
            labels = json.loads(archive.extractfile(label_member).read())
            label_by_id = {row["id"]: row for row in labels}
            for source in sources:
                label = label_by_id[source["id"]]
                if label["keep"]:
                    records[source["id"]] = {
                        "id": source["id"],
                        "text": source["text"],
                        "entities": label["entities"],
                    }
    if not records:
        raise ValueError(f"no retained records in {path}")
    return records


def split_ids(records: dict[str, dict[str, Any]], seed: int) -> dict[str, list[str]]:
    groups: dict[str, list[str]] = {}
    for record_id, record in records.items():
        key = hashlib.sha256(record["text"].encode("utf-8")).hexdigest()
        groups.setdefault(key, []).append(record_id)
    keys = sorted(groups)
    random.Random(seed).shuffle(keys)
    target_train = int(len(records) * 0.6)
    target_val = int(len(records) * 0.8)
    result = {"train": [], "validation": [], "test": []}
    for key in keys:
        destination = "train" if len(result["train"]) < target_train else "validation"
        if (
            len(result["train"]) >= target_train
            and len(result["validation"]) >= target_val - target_train
        ):
            destination = "test"
        result[destination].extend(groups[key])
    return result


def ros_records(records: list[dict[str, Any]], seed: int) -> list[dict[str, Any]]:
    """Oversample training documents containing rare entity classes."""
    class_weights = {"IDTY": 1.0, "ACT": 1.0, "LOC": 1.25, "VUL": 3.0}
    weights = [
        max(
            (class_weights[str(entity["label"])] for entity in record["entities"]),
            default=1.0,
        )
        for record in records
    ]
    return random.Random(seed).choices(records, weights=weights, k=len(records))


def _collate(features: list[dict[str, list[int]]]) -> dict[str, Any]:
    import torch

    length = max(len(row["input_ids"]) for row in features)
    batch: dict[str, list[list[int]]] = {"input_ids": [], "attention_mask": [], "labels": []}
    for row in features:
        padding = length - len(row["input_ids"])
        batch["input_ids"].append(row["input_ids"] + [1] * padding)
        batch["attention_mask"].append(row["attention_mask"] + [0] * padding)
        batch["labels"].append(row["labels"] + [-100] * padding)
    return {key: torch.tensor(value, dtype=torch.long) for key, value in batch.items()}


def _token_features(tokenizer: Any, records: list[dict[str, Any]]) -> list[dict[str, list[int]]]:
    features: list[dict[str, list[int]]] = []
    for record in records:
        encoded = tokenizer(
            record["text"],
            truncation=True,
            max_length=512,
            stride=128,
            return_overflowing_tokens=True,
            return_offsets_mapping=True,
            padding=False,
        )
        spans = [
            (int(entity["start"]), int(entity["end"]), str(entity["label"]))
            for entity in record["entities"]
        ]
        for input_ids, attention, offsets in zip(
            encoded["input_ids"],
            encoded["attention_mask"],
            encoded["offset_mapping"],
            strict=True,
        ):
            labels = []
            for start, end in offsets:
                if end <= start:
                    labels.append(-100)
                    continue
                match = next(
                    (span for span in spans if span[0] < end and start < span[1]),
                    None,
                )
                if match is None:
                    labels.append(LABEL_TO_ID["O"])
                else:
                    prefix = "B" if start <= match[0] else "I"
                    labels.append(LABEL_TO_ID[f"{prefix}-{match[2]}"])
            features.append(
                {
                    "input_ids": list(input_ids),
                    "attention_mask": list(attention),
                    "labels": labels,
                }
            )
    if not features:
        raise ValueError("tokenization produced no features")
    return features


def _prediction_spans(
    model: Any, tokenizer: Any, records: list[dict[str, Any]]
) -> dict[str, list[tuple[int, int, str]]]:
    import torch

    model.eval()
    result: dict[str, set[tuple[int, int, str]]] = {record["id"]: set() for record in records}
    with torch.no_grad():
        for record in records:
            encoded = tokenizer(
                record["text"],
                truncation=True,
                max_length=512,
                stride=128,
                return_overflowing_tokens=True,
                return_offsets_mapping=True,
                padding=False,
            )
            for input_ids, attention, offsets in zip(
                encoded["input_ids"],
                encoded["attention_mask"],
                encoded["offset_mapping"],
                strict=True,
            ):
                inputs = {
                    "input_ids": torch.tensor([input_ids], device=model.device),
                    "attention_mask": torch.tensor([attention], device=model.device),
                }
                predictions = model(**inputs).logits.argmax(dim=-1)[0].tolist()
                current: list[int | str] | None = None
                for prediction, (start, end) in zip(predictions, offsets, strict=True):
                    if end <= start or prediction == LABEL_TO_ID["O"]:
                        if current is not None:
                            result[record["id"]].add(tuple(current))
                            current = None
                        continue
                    label = LABELS[prediction]
                    prefix, entity_type = label.split("-", maxsplit=1)
                    if prefix == "B" or current is None or current[2] != entity_type:
                        if current is not None:
                            result[record["id"]].add(tuple(current))
                        current = [start, end, entity_type]
                    else:
                        current[1] = end
                if current is not None:
                    result[record["id"]].add(tuple(current))
    return {record_id: sorted(spans) for record_id, spans in result.items()}


def _matching_count(
    gold: list[tuple[int, int, str]], predicted: list[tuple[int, int, str]], strict: bool
) -> int:
    edges = [
        [
            index
            for index, target in enumerate(gold)
            if (target == span if strict else target[0] < span[1] and span[0] < target[1])
            and (strict or target[2] == span[2])
        ]
        for span in predicted
    ]
    matched: dict[int, int] = {}

    def visit(prediction: int, seen: set[int]) -> bool:
        for target in edges[prediction]:
            if target in seen:
                continue
            seen.add(target)
            previous = matched.get(target)
            if previous is None or visit(previous, seen):
                matched[target] = prediction
                return True
        return False

    return sum(visit(index, set()) for index in range(len(predicted)))


def _score(
    records: list[dict[str, Any]], predictions: dict[str, list[tuple[int, int, str]]], strict: bool
) -> dict[str, float | int]:
    gold = [
        [(int(e["start"]), int(e["end"]), str(e["label"])) for e in record["entities"]]
        for record in records
    ]
    actual = [predictions[record["id"]] for record in records]
    true_positive = sum(
        _matching_count(expected, found, strict)
        for expected, found in zip(gold, actual, strict=True)
    )
    predicted = sum(map(len, actual))
    expected = sum(map(len, gold))
    false_positive = predicted - true_positive
    false_negative = expected - true_positive
    precision = true_positive / predicted if predicted else 0.0
    recall = true_positive / expected if expected else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "true_positive": true_positive,
        "false_positive": false_positive,
        "false_negative": false_negative,
        "precision": precision,
        "recall": recall,
        "f1": f1,
    }


def _set_seed(seed: int) -> None:
    import numpy as np
    import torch

    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)


def train_one(
    train_records: list[dict[str, Any]],
    validation_records: list[dict[str, Any]],
    test_records: list[dict[str, Any]],
    seed: int,
    epochs: int,
    batch_size: int,
    gradient_accumulation: int,
    method: str,
    weighted_loss: bool,
) -> dict[str, Any]:
    import torch
    from transformers import AutoModelForTokenClassification, AutoTokenizer

    _set_seed(seed)
    tokenizer = AutoTokenizer.from_pretrained(MODEL, revision=REVISION)
    model = AutoModelForTokenClassification.from_pretrained(
        MODEL,
        revision=REVISION,
        num_labels=len(LABELS),
        id2label={index: label for index, label in enumerate(LABELS)},
        label2id=LABEL_TO_ID,
        ignore_mismatched_sizes=True,
    )
    if method == "loraplus":
        from peft import LoraConfig, TaskType, get_peft_model

        model = get_peft_model(
            model,
            LoraConfig(
                task_type=TaskType.TOKEN_CLS,
                r=8,
                lora_alpha=16,
                lora_dropout=0.1,
                target_modules=["query", "value"],
                modules_to_save=["classifier"],
                bias="none",
            ),
        )
    elif method != "full":
        raise ValueError(f"unknown training method: {method}")
    model.to("cuda")
    train_features = _token_features(tokenizer, train_records)
    if method == "full":
        for parameter in model.parameters():
            parameter.requires_grad = True
    trainable = [
        (name, parameter) for name, parameter in model.named_parameters() if parameter.requires_grad
    ]
    optimizer = torch.optim.AdamW(
        [
            {
                "params": [parameter],
                "lr": (
                    1e-3
                    if "classifier" in name
                    else 2e-5 * (8 if method == "loraplus" and "lora_B" in name else 1)
                ),
                "weight_decay": 0.01,
            }
            for name, parameter in trainable
        ]
    )
    steps_per_epoch = math.ceil(len(train_features) / batch_size / gradient_accumulation)
    total_steps = steps_per_epoch * epochs
    warmup_steps = max(1, int(total_steps * 0.1))
    scheduler = torch.optim.lr_scheduler.LambdaLR(
        optimizer,
        lambda step: (
            min(step / warmup_steps, 1.0)
            if step < warmup_steps
            else max((total_steps - step) / max(total_steps - warmup_steps, 1), 0.0)
        ),
    )
    scaler = torch.cuda.amp.GradScaler()
    class_weights = None
    if weighted_loss:
        counts = Counter(
            label for feature in train_features for label in feature["labels"] if label >= 0
        )
        raw_weights = torch.tensor(
            [1 / math.sqrt(max(counts.get(index, 1), 1)) for index in range(len(LABELS))],
            device="cuda",
            dtype=torch.float32,
        )
        class_weights = raw_weights / raw_weights.mean()
    losses: list[float] = []
    model.train()
    optimizer.zero_grad(set_to_none=True)
    for epoch in range(epochs):
        random.Random(seed + epoch).shuffle(train_features)
        for batch_index in range(0, len(train_features), batch_size):
            batch = _collate(train_features[batch_index : batch_index + batch_size])
            batch = {key: value.to("cuda") for key, value in batch.items()}
            with torch.autocast(device_type="cuda", dtype=torch.float16):
                logits = model(
                    input_ids=batch["input_ids"], attention_mask=batch["attention_mask"]
                ).logits
                loss = (
                    torch.nn.functional.cross_entropy(
                        logits.reshape(-1, len(LABELS)),
                        batch["labels"].reshape(-1),
                        weight=class_weights,
                        ignore_index=-100,
                    )
                    / gradient_accumulation
                )
            scaler.scale(loss).backward()
            is_last = batch_index + batch_size >= len(train_features)
            if ((batch_index // batch_size) + 1) % gradient_accumulation == 0 or is_last:
                scaler.unscale_(optimizer)
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                scaler.step(optimizer)
                scaler.update()
                scheduler.step()
                optimizer.zero_grad(set_to_none=True)
            losses.append(float(loss.detach().cpu()) * gradient_accumulation)
    validation_predictions = _prediction_spans(model, tokenizer, validation_records)
    test_predictions = _prediction_spans(model, tokenizer, test_records)
    return {
        "seed": seed,
        "train_documents": len(train_records),
        "unique_train_documents": len({record["id"] for record in train_records}),
        "validation_documents": len(validation_records),
        "test_documents": len(test_records),
        "train_features": len(train_features),
        "trainable_parameters": sum(parameter.numel() for _, parameter in trainable),
        "method": method,
        "weighted_loss": weighted_loss,
        "mean_training_loss": sum(losses) / len(losses),
        "validation_strict": _score(validation_records, validation_predictions, True),
        "validation_partial_same_type": _score(validation_records, validation_predictions, False),
        "test_predictions": test_predictions,
    }


def summarize(values: list[float]) -> dict[str, float]:
    mean = sum(values) / len(values)
    variance = sum((value - mean) ** 2 for value in values) / len(values)
    return {"mean": mean, "std": math.sqrt(variance)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--original-archive", type=Path, default=Path("/content/muse_original.tar.gz")
    )
    parser.add_argument(
        "--corrected-archive", type=Path, default=Path("/content/muse_corrected.tar.gz")
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(os.environ.get("LORA_PLUS_OUTPUT", "/content/loraplus_muse_sensitivity.json")),
    )
    parser.add_argument(
        "--method",
        choices=("loraplus", "full"),
        default=os.environ.get("LORA_PLUS_METHOD", "loraplus"),
    )
    parser.add_argument(
        "--weighted-loss",
        action="store_true",
        default=os.environ.get("LORA_PLUS_WEIGHTED_LOSS", "false").lower() == "true",
    )
    parser.add_argument(
        "--ros",
        action="store_true",
        default=os.environ.get("LORA_PLUS_ROS", "false").lower() == "true",
    )
    parser.add_argument("--split-seed", type=int, default=2024)
    parser.add_argument("--seeds", type=int, nargs="+", default=[42, 123, 2024])
    parser.add_argument("--epochs", type=int, default=5)
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--gradient-accumulation", type=int, default=2)
    args, _ = parser.parse_known_args()
    if args.ros and args.weighted_loss:
        parser.error("--ros and --weighted-loss are separate ablations")

    original = load_archive(args.original_archive)
    corrected = load_archive(args.corrected_archive)
    common_ids = sorted(set(original) & set(corrected))
    if set(original) != set(corrected):
        raise ValueError("original and corrected archives do not contain the same retained IDs")
    if any(original[record_id]["text"] != corrected[record_id]["text"] for record_id in common_ids):
        raise ValueError("original and corrected source text differs")
    splits = split_ids(original, args.split_seed)
    result: dict[str, Any] = {
        "experiment_status": "extension",
        "experiment": f"{args.method}_annotation_layer_sensitivity",
        "model": MODEL,
        "revision": REVISION,
        "original_archive_sha256": file_sha256(args.original_archive),
        "corrected_archive_sha256": file_sha256(args.corrected_archive),
        "split_seed": args.split_seed,
        "split_counts": {name: len(ids) for name, ids in splits.items()},
        "split_ids_sha256": hashlib.sha256("|".join(splits["test"]).encode()).hexdigest(),
        "training": {
            "method": "LoRA+" if args.method == "loraplus" else "full_finetune",
            "target_modules": ["query", "value"],
            "rank": 8,
            "alpha": 16,
            "dropout": 0.1,
            "loraplus_lr_ratio": 8,
            "base_learning_rate": 2e-5,
            "classifier_learning_rate": 1e-3,
            "weighted_loss": args.weighted_loss,
            "ros": args.ros,
            "ros_class_weights": {"IDTY": 1.0, "ACT": 1.0, "LOC": 1.25, "VUL": 3.0},
            "epochs": args.epochs,
            "batch_size": args.batch_size,
            "gradient_accumulation": args.gradient_accumulation,
            "max_length": 512,
            "stride": 128,
            "labels": LABELS,
        },
        "conditions": {},
    }
    for condition_name, annotation in (("original", original), ("corrected", corrected)):
        condition_results = []
        train_records = [annotation[record_id] for record_id in splits["train"]]
        if args.ros:
            train_records = ros_records(train_records, args.split_seed)
        validation_records = [annotation[record_id] for record_id in splits["validation"]]
        test_records = [annotation[record_id] for record_id in splits["test"]]
        for seed in args.seeds:
            run = train_one(
                train_records,
                validation_records,
                test_records,
                seed,
                args.epochs,
                args.batch_size,
                args.gradient_accumulation,
                args.method,
                args.weighted_loss,
            )
            predictions = run.pop("test_predictions")
            run["test_against_original"] = {
                "strict": _score(
                    [original[record_id] for record_id in splits["test"]], predictions, True
                ),
                "partial_same_type": _score(
                    [original[record_id] for record_id in splits["test"]], predictions, False
                ),
            }
            run["test_against_corrected"] = {
                "strict": _score(
                    [corrected[record_id] for record_id in splits["test"]], predictions, True
                ),
                "partial_same_type": _score(
                    [corrected[record_id] for record_id in splits["test"]], predictions, False
                ),
            }
            condition_results.append(run)
        result["conditions"][condition_name] = condition_results
    for condition_name, runs in result["conditions"].items():
        for evaluation_name in ("test_against_original", "test_against_corrected"):
            for metric_name in ("strict", "partial_same_type"):
                result.setdefault("summary", {}).setdefault(condition_name, {}).setdefault(
                    evaluation_name, {}
                )[metric_name] = {
                    key: summarize([run[evaluation_name][metric_name][key] for run in runs])
                    for key in ("precision", "recall", "f1")
                }
    result["gold_entity_counts"] = {
        "original": dict(
            Counter(
                entity["label"] for record in original.values() for entity in record["entities"]
            )
        ),
        "corrected": dict(
            Counter(
                entity["label"] for record in corrected.values() for entity in record["entities"]
            )
        ),
    }
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "output": str(args.output),
                "split_counts": result["split_counts"],
                "summary": result["summary"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
