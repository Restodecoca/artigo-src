"""Validate the AI-assisted, human-verified review of the adjudicated overlay.

The review layer never overwrites the overlay archive. For each reviewed
document it records only the overlay entities that changed (``relabel``,
``fix_span`` or ``reject``) plus the entities that were missing
(``added_entities``). Overlay entities without a decision in a reviewed
document were confirmed as they are.

This validator checks that every decision points at an existing overlay
entity, that every span matches the source text, that labels belong to the
protocol, and that the resulting layer has no overlapping or duplicated spans.
With ``--export-dir`` it also writes the reviewed layer in the Muse batch
format (``batch_*.json`` + ``labels_batch_*.json``).
"""

from __future__ import annotations

import argparse
import itertools
import json
import shutil
import sys
import tarfile
from collections import Counter
from pathlib import Path
from typing import Any

from scripts.validation.validate_ai_additions import (
    LABELS,
    load_archive_labels,
    load_archive_texts,
)

ACTIONS = {"relabel", "fix_span", "reject"}


def _span_key(entity: dict[str, Any]) -> tuple[int, int, str]:
    return int(entity["start"]), int(entity["end"]), str(entity["label"])


def _check_span(
    doc_id: str, text: str, start: Any, end: Any, label: Any, surface: Any
) -> str | None:
    if label not in LABELS:
        return f"{doc_id}: invalid label {label!r}"
    if not isinstance(start, int) or not isinstance(end, int):
        return f"{doc_id}: non-integer span {start!r}-{end!r}"
    if not 0 <= start < end <= len(text):
        return f"{doc_id}: span out of range {start}-{end}"
    if surface is not None and text[start:end] != surface:
        return f"{doc_id}: text mismatch at {start}-{end}: {text[start:end]!r} != {surface!r}"
    if text[start:end] != text[start:end].strip():
        return f"{doc_id}: span {start}-{end} has leading or trailing whitespace"
    return None


def apply_review(
    review: dict[str, Any],
    texts: dict[str, str],
    base_labels: dict[str, dict[str, Any]],
) -> tuple[list[str], dict[str, dict[str, Any]], dict[str, Any]]:
    """Apply the review to the overlay and return errors, final labels and stats."""

    errors: list[str] = []
    final: dict[str, dict[str, Any]] = {
        doc_id: {**record, "entities": [dict(entity) for entity in record.get("entities", [])]}
        for doc_id, record in base_labels.items()
    }
    actions: Counter[str] = Counter()
    added_labels: Counter[str] = Counter()
    reviewed: set[str] = set()

    for document in review.get("documents", []):
        doc_id = document.get("id")
        if not isinstance(doc_id, str) or not doc_id:
            errors.append("document without a valid id")
            continue
        if doc_id in reviewed:
            errors.append(f"{doc_id}: duplicated document entry")
            continue
        if doc_id not in texts or doc_id not in base_labels:
            errors.append(f"{doc_id}: document not found in the overlay archive")
            continue
        if not document.get("reviewed"):
            errors.append(f"{doc_id}: entry present but not marked reviewed")
            continue
        reviewed.add(doc_id)

        text = texts[doc_id]
        record = base_labels[doc_id]
        if not record.get("keep", True):
            if document.get("decisions") or document.get("added_entities"):
                errors.append(f"{doc_id}: keep=false document must stay without entities")
            continue

        by_key = {_span_key(entity): entity for entity in record.get("entities", [])}
        removed: set[tuple[int, int, str]] = set()
        replacements: list[dict[str, Any]] = []

        for decision in document.get("decisions", []):
            action = decision.get("action")
            if action not in ACTIONS:
                errors.append(f"{doc_id}: invalid action {action!r}")
                continue
            try:
                key = _span_key(decision)
            except (KeyError, TypeError, ValueError):
                errors.append(f"{doc_id}: decision without start/end/label")
                continue
            if key not in by_key:
                errors.append(f"{doc_id}: decision {key} does not match an overlay entity")
                continue
            if key in removed:
                errors.append(f"{doc_id}: more than one decision for {key}")
                continue
            removed.add(key)
            actions[action] += 1
            if action == "reject":
                continue

            start = decision.get("new_start", key[0])
            end = decision.get("new_end", key[1])
            label = decision.get("new_label", key[2])
            if action == "relabel" and label == key[2]:
                errors.append(f"{doc_id}: relabel of {key} keeps the same label")
                continue
            if action == "fix_span" and (start, end) == (key[0], key[1]):
                errors.append(f"{doc_id}: fix_span of {key} keeps the same offsets")
                continue
            error = _check_span(doc_id, text, start, end, label, None)
            if error:
                errors.append(error)
                continue
            replacements.append(
                {"start": start, "end": end, "label": label, "text": text[start:end]}
            )

        for entity in document.get("added_entities", []):
            error = _check_span(
                doc_id,
                text,
                entity.get("start"),
                entity.get("end"),
                entity.get("label"),
                entity.get("text"),
            )
            if error:
                errors.append(error)
                continue
            added_labels[entity["label"]] += 1
            replacements.append(
                {
                    "start": entity["start"],
                    "end": entity["end"],
                    "label": entity["label"],
                    "text": entity["text"],
                }
            )

        entities = [e for e in record.get("entities", []) if _span_key(e) not in removed]
        entities.extend(replacements)
        entities.sort(key=lambda entity: (entity["start"], entity["end"]))
        for previous, current in itertools.pairwise(entities):
            if current["start"] < previous["end"]:
                errors.append(
                    f"{doc_id}: overlapping spans {previous['start']}-{previous['end']} "
                    f"and {current['start']}-{current['end']}"
                )
        final[doc_id] = {**record, "entities": entities}

    label_counts: Counter[str] = Counter(
        entity["label"] for record in final.values() for entity in record["entities"]
    )
    stats = {
        "reviewed_documents": len(reviewed),
        "kept_documents": sum(1 for record in base_labels.values() if record.get("keep", True)),
        "decision_counts": dict(actions),
        "added_entities": sum(added_labels.values()),
        "added_label_counts": dict(added_labels),
        "base_entities": sum(len(r.get("entities", [])) for r in base_labels.values()),
        "final_entities": sum(label_counts.values()),
        "final_label_counts": dict(label_counts),
    }
    return errors, final, stats


def export_muse_layer(archive: Path, final: dict[str, dict[str, Any]], output_dir: Path) -> None:
    """Write the reviewed layer next to copies of the source batches."""

    output_dir.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive, "r:gz") as handle:
        for member in handle.getmembers():
            name = Path(member.name).name
            extracted = handle.extractfile(member)
            if extracted is None:
                continue
            if name.startswith("batch_"):
                with (output_dir / name).open("wb") as target:
                    shutil.copyfileobj(extracted, target)
            elif name.startswith("labels_batch_"):
                payload = json.loads(extracted.read())
                reviewed = [final[record["id"]] for record in payload]
                (output_dir / name).write_text(
                    json.dumps(reviewed, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
                )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--review",
        type=Path,
        default=Path("data/muse-artifacts/annotations/overlay_review_v1.json"),
    )
    parser.add_argument(
        "--archive",
        type=Path,
        default=Path("data/muse-artifacts/processed/muse_corrected.tar.gz"),
        help="overlay archive (batch_*.json + labels_batch_*.json)",
    )
    parser.add_argument("--export-dir", type=Path, help="write the reviewed Muse layer here")
    parser.add_argument("--json", action="store_true", help="print errors and stats as JSON")
    args = parser.parse_args()

    review = json.loads(args.review.read_text(encoding="utf-8"))
    texts = load_archive_texts(args.archive)
    base_labels = load_archive_labels(args.archive)
    errors, final, stats = apply_review(review, texts, base_labels)

    if args.export_dir and not errors:
        export_muse_layer(args.archive, final, args.export_dir)

    if args.json:
        print(json.dumps({"errors": errors, "stats": stats}, ensure_ascii=False, indent=2))
    else:
        print(f"review:    {args.review}")
        print(f"errors:    {len(errors)}")
        for error in errors:
            print(f"  - {error}")
        print(
            f"reviewed:  {stats['reviewed_documents']} of {stats['kept_documents']} kept documents"
        )
        print(f"decisions: {stats['decision_counts']}")
        print(f"added:     {stats['added_entities']} {stats['added_label_counts']}")
        print(f"entities:  {stats['base_entities']} -> {stats['final_entities']}")
        print(f"labels:    {stats['final_label_counts']}")
        if args.export_dir and not errors:
            print(f"exported:  {args.export_dir}")
    raise SystemExit(1 if errors else 0)


if __name__ == "__main__":
    sys.exit(main())
