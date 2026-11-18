"""Validate the AI-assisted, human-verified entity additions layer.

The additions file is a separate layer: it never overwrites the adjudicated
overlay. This validator checks that every added span points at the exact source
text, uses a protocol label, does not overlap an existing overlay entity, and is
not duplicated inside the same document.
"""

from __future__ import annotations

import argparse
import json
import sys
import tarfile
from collections import Counter
from pathlib import Path
from typing import Any

LABELS = {"IDTY", "ACT", "VUL", "LOC"}


def load_archive_labels(archive: Path) -> dict[str, dict[str, Any]]:
    """Read all labels_batch_*.json files from a Muse-style tar.gz archive."""

    records: dict[str, dict[str, Any]] = {}
    with tarfile.open(archive, "r:gz") as handle:
        for member in handle.getmembers():
            if not Path(member.name).name.startswith("labels_batch_"):
                continue
            extracted = handle.extractfile(member)
            if extracted is None:
                raise ValueError(f"{archive}: cannot read {member.name}")
            payload = json.loads(extracted.read())
            for record in payload:
                records[record["id"]] = record
    if not records:
        raise ValueError(f"{archive}: no labels_batch_*.json files")
    return records


def load_archive_texts(archive: Path) -> dict[str, str]:
    """Read all batch_*.json texts from a Muse-style tar.gz archive."""

    texts: dict[str, str] = {}
    with tarfile.open(archive, "r:gz") as handle:
        for member in handle.getmembers():
            if not Path(member.name).name.startswith("batch_"):
                continue
            extracted = handle.extractfile(member)
            if extracted is None:
                raise ValueError(f"{archive}: cannot read {member.name}")
            payload = json.loads(extracted.read())
            for record in payload:
                texts[record["id"]] = record["text"]
    if not texts:
        raise ValueError(f"{archive}: no batch_*.json files")
    return texts


def validate_additions(
    additions: dict[str, Any],
    texts: dict[str, str],
    base_labels: dict[str, dict[str, Any]],
) -> tuple[list[str], dict[str, Any]]:
    """Return human-readable errors and aggregate statistics."""

    errors: list[str] = []
    per_label: Counter[str] = Counter()
    per_document: dict[str, int] = {}
    seen_documents: set[str] = set()

    for document in additions.get("documents", []):
        doc_id = document.get("id")
        if not isinstance(doc_id, str) or not doc_id:
            errors.append("document without a valid id")
            continue
        if doc_id in seen_documents:
            errors.append(f"{doc_id}: duplicated document entry")
            continue
        seen_documents.add(doc_id)
        if doc_id not in texts:
            errors.append(f"{doc_id}: document not found in source texts")
            continue
        if doc_id not in base_labels:
            errors.append(f"{doc_id}: document not found in base labels")
            continue

        text = texts[doc_id]
        base_spans = [
            (int(entity["start"]), int(entity["end"]))
            for entity in base_labels[doc_id].get("entities", [])
        ]
        seen_spans: set[tuple[int, int]] = set()
        seen_names: set[str] = set()

        for entity in document.get("added_entities", []):
            start = entity.get("start")
            end = entity.get("end")
            label = entity.get("label")
            surface = entity.get("text")

            if label not in LABELS:
                errors.append(f"{doc_id}: invalid label {label!r}")
                continue
            if not isinstance(start, int) or not isinstance(end, int):
                errors.append(f"{doc_id}: non-integer span {start!r}-{end!r}")
                continue
            if not 0 <= start < end <= len(text):
                errors.append(f"{doc_id}: span out of range {start}-{end}")
                continue
            if text[start:end] != surface:
                errors.append(
                    f"{doc_id}: text mismatch at {start}-{end}: {text[start:end]!r} != {surface!r}"
                )
                continue
            if any(start < b_end and end > b_start for b_start, b_end in base_spans):
                errors.append(f"{doc_id}: span {start}-{end} overlaps the base layer")
                continue
            if (start, end) in seen_spans:
                errors.append(f"{doc_id}: duplicated span {start}-{end}")
                continue
            seen_spans.add((start, end))

            name = str(surface).casefold().strip()
            if name in seen_names:
                errors.append(f"{doc_id}: duplicated surface {surface!r}")
                continue
            seen_names.add(name)

            per_label[label] += 1
            per_document[doc_id] = per_document.get(doc_id, 0) + 1

    documents_with_additions = len(per_document)
    total = sum(per_label.values())
    stats = {
        "documents_with_additions": documents_with_additions,
        "documents_without_additions": len(texts) - documents_with_additions,
        "total_added_entities": total,
        "added_label_counts": dict(per_label),
        "base_entities": sum(len(record.get("entities", [])) for record in base_labels.values()),
        "augmented_entities": sum(
            len(record.get("entities", [])) for record in base_labels.values()
        )
        + total,
        "added_per_document": per_document,
    }
    return errors, stats


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--additions",
        type=Path,
        default=Path("data/muse-artifacts/annotations/ai_assisted_additions.json"),
    )
    parser.add_argument(
        "--archive",
        type=Path,
        default=Path("data/muse-artifacts/processed/muse_corrected.tar.gz"),
        help="base overlay archive (batch_*.json + labels_batch_*.json)",
    )
    parser.add_argument("--json", action="store_true", help="print stats as JSON")
    args = parser.parse_args()

    additions = json.loads(args.additions.read_text(encoding="utf-8"))
    texts = load_archive_texts(args.archive)
    base_labels = load_archive_labels(args.archive)
    errors, stats = validate_additions(additions, texts, base_labels)

    if args.json:
        print(json.dumps({"errors": errors, "stats": stats}, ensure_ascii=False, indent=2))
    else:
        print(f"additions: {args.additions}")
        print(f"archive:   {args.archive}")
        print(f"errors:    {len(errors)}")
        for error in errors:
            print(f"  - {error}")
        print(f"added:     {stats['total_added_entities']}")
        print(f"documents: {stats['documents_with_additions']} with additions")
        print(f"labels:    {stats['added_label_counts']}")
        print(f"base:      {stats['base_entities']} entities")
        print(f"augmented: {stats['augmented_entities']} entities")
    raise SystemExit(1 if errors else 0)


if __name__ == "__main__":
    sys.exit(main())
