"""Validate the adjudicated Muse label overlay against its source batches."""

from __future__ import annotations

import argparse
import json
from itertools import pairwise
from pathlib import Path

from healthcare_ner_replication.labels import ENTITY_TYPES

LABELS = set(ENTITY_TYPES)


def validate(source_dir: Path, labels_dir: Path) -> dict[str, int]:
    """Validate overlay IDs, offsets, text slices, labels, ordering and overlaps."""

    errors: list[str] = []
    records = kept = entities = 0
    for label_path in sorted(labels_dir.glob("labels_batch_*.json")):
        suffix = label_path.stem.removeprefix("labels_batch_")
        source_path = source_dir / f"batch_{suffix}.json"
        sources = json.loads(source_path.read_text(encoding="utf-8"))
        labels = json.loads(label_path.read_text(encoding="utf-8"))
        source_by_id = {row["id"]: row for row in sources}
        label_ids = [row["id"] for row in labels]
        if set(source_by_id) != set(label_ids):
            errors.append(f"{label_path}: source/label ids differ")
        for row in labels:
            record_id = row["id"]
            text = source_by_id[record_id]["text"]
            records += 1
            kept += int(row["keep"])
            spans: list[tuple[int, int]] = []
            if not row["keep"] and row["entities"]:
                errors.append(f"{record_id}: keep=false has entities")
            for index, entity in enumerate(row["entities"]):
                entities += 1
                start, end = entity["start"], entity["end"]
                spans.append((start, end))
                if not (0 <= start < end <= len(text)):
                    errors.append(f"{record_id}:{index}: invalid bounds")
                elif entity["text"] != text[start:end]:
                    errors.append(f"{record_id}:{index}: text mismatch")
                if entity["label"] not in LABELS:
                    errors.append(f"{record_id}:{index}: invalid label")
            if spans != sorted(spans):
                errors.append(f"{record_id}: spans are not sorted")
            for previous, current in pairwise(spans):
                if current[0] < previous[1]:
                    errors.append(f"{record_id}: overlapping spans")
                if current == previous:
                    errors.append(f"{record_id}: duplicate span")
    if errors:
        raise ValueError("\n".join(errors))
    return {"records": records, "kept": kept, "entities": entities}


def main() -> None:
    """Validate the adjudicated overlay and print aggregate record counts."""

    parser = argparse.ArgumentParser()
    parser.add_argument("source_dir", type=Path)
    parser.add_argument("labels_dir", type=Path)
    args = parser.parse_args()
    print(json.dumps(validate(args.source_dir, args.labels_dir), indent=2))


if __name__ == "__main__":
    main()
