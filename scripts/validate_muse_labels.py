"""Validate character-offset labels produced for the private Muse batches."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ALLOWED_LABELS = frozenset({"IDTY", "ACT", "VUL", "LOC"})


def _read_json(path: Path) -> Any:
    with path.open(encoding="utf-8-sig") as handle:
        return json.load(handle)


def validate_records(
    source_records: list[dict[str, Any]], label_records: list[dict[str, Any]]
) -> list[str]:
    """Return every structural and offset error in one source/label pair."""

    errors: list[str] = []
    source_by_id: dict[str, dict[str, Any]] = {}
    for index, record in enumerate(source_records):
        if not isinstance(record, dict):
            errors.append(f"source record {index} must be an object")
            continue
        record_id = record.get("id")
        if not isinstance(record_id, str) or not record_id:
            errors.append(f"source record {index} has no valid id")
            continue
        if record_id in source_by_id:
            errors.append(f"duplicate source id {record_id}")
        source_by_id[record_id] = record

    label_by_id: dict[str, dict[str, Any]] = {}
    for index, record in enumerate(label_records):
        if not isinstance(record, dict):
            errors.append(f"label record {index} must be an object")
            continue
        record_id = record.get("id")
        if not isinstance(record_id, str) or not record_id:
            errors.append(f"label record {index} has no valid id")
            continue
        if record_id in label_by_id:
            errors.append(f"duplicate label id {record_id}")
        label_by_id[record_id] = record

    for record_id in sorted(source_by_id.keys() - label_by_id.keys()):
        errors.append(f"missing label record for {record_id}")
    for record_id in sorted(label_by_id.keys() - source_by_id.keys()):
        errors.append(f"label record has unknown source id {record_id}")

    for record_id, source in source_by_id.items():
        label_record = label_by_id.get(record_id)
        if label_record is None:
            continue
        text = source.get("text")
        entities = label_record.get("entities")
        if not isinstance(text, str):
            errors.append(f"{record_id}: source text is not a string")
            continue
        if not isinstance(entities, list):
            errors.append(f"{record_id}: entities must be a list")
            continue

        previous_start = -1
        previous_end = -1
        for entity_index, entity in enumerate(entities):
            prefix = f"{record_id} entity {entity_index}"
            if not isinstance(entity, dict):
                errors.append(f"{prefix}: entity must be an object")
                continue
            start = entity.get("start")
            end = entity.get("end")
            label = entity.get("label")
            if isinstance(start, bool) or not isinstance(start, int):
                errors.append(f"{prefix}: start must be an integer")
                continue
            if isinstance(end, bool) or not isinstance(end, int):
                errors.append(f"{prefix}: end must be an integer")
                continue
            if start < 0:
                errors.append(f"{prefix}: start must be non-negative")
            if end <= start:
                errors.append(f"{prefix}: end must be greater than start")
            if start >= len(text) or end > len(text):
                errors.append(f"{prefix}: span is outside text bounds")
            if isinstance(label, str):
                if label not in ALLOWED_LABELS:
                    errors.append(f"{prefix}: unknown label {label}")
            else:
                errors.append(f"{prefix}: label must be a string")
            if start < previous_start:
                errors.append(f"{prefix}: spans are not sorted by start")
            if start < previous_end:
                errors.append(f"{prefix}: span overlaps previous span")
            if 0 <= start < end <= len(text) and not text[start:end].strip():
                errors.append(f"{prefix}: span contains only whitespace")
            previous_start = start
            previous_end = max(previous_end, end)

    return errors


def validate_directory(directory: Path) -> tuple[list[str], int, int]:
    """Validate all matching batch pairs and return errors and record counts."""

    errors: list[str] = []
    source_count = 0
    label_count = 0
    for source_path in sorted(directory.glob("batch_*.json")):
        suffix = source_path.stem.removeprefix("batch_")
        label_path = directory / f"labels_batch_{suffix}.json"
        source_records = _read_json(source_path)
        if not isinstance(source_records, list):
            errors.append(f"{source_path.name}: source file must contain a list")
            continue
        source_count += len(source_records)
        if not label_path.exists():
            errors.append(f"{source_path.name}: missing {label_path.name}")
            continue
        label_records = _read_json(label_path)
        if not isinstance(label_records, list):
            errors.append(f"{label_path.name}: label file must contain a list")
            continue
        label_count += len(label_records)
        errors.extend(
            f"{source_path.name}: {error}"
            for error in validate_records(source_records, label_records)
        )
    for label_path in sorted(directory.glob("labels_batch_*.json")):
        suffix = label_path.stem.removeprefix("labels_batch_")
        source_path = directory / f"batch_{suffix}.json"
        if not source_path.exists():
            errors.append(f"{label_path.name}: has no matching {source_path.name}")
    return errors, source_count, label_count


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    errors, source_count, label_count = validate_directory(args.directory)
    print(f"source_records={source_count} label_records={label_count} errors={len(errors)}")
    for error in errors:
        print(error)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
