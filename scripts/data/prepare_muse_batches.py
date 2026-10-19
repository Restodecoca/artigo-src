"""Prepare reproducible local annotation batches from the three public datasets.

The generated files contain source text and are intentionally written below
``data/raw/``, which is excluded from the public repository. Muse annotations
are kept separate from this preparation step so that source selection remains
deterministic and auditable.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path

from healthcare_ner_replication.labels import ENTITY_TYPES
from healthcare_ner_replication.protocol import (
    COLLECTION_PERIOD_END,
    COLLECTION_PERIOD_START,
)
from healthcare_ner_replication.schemas import MuseBatchSource

ALLOWED_LABELS = ENTITY_TYPES
PERIOD_START = COLLECTION_PERIOD_START
PERIOD_END = COLLECTION_PERIOD_END


@dataclass(frozen=True)
class DatasetSpec:
    name: str
    repository: str
    revision: str
    split: str
    config: str | None
    text_column: str
    identity_columns: tuple[str, ...]
    selection: Callable[[Mapping[str, object]], bool]


def _nonempty(value: object) -> bool:
    """Check whether a value is a non-blank string."""

    return isinstance(value, str) and bool(value.strip())


def _vinitvek_selection(row: Mapping[str, object]) -> bool:
    """Select described Vinitvek incidents associated with healthcare."""

    industry = str(row.get("affected_industry", "")).casefold()
    organization = str(row.get("affected_organization", "")).casefold()
    healthcare = "health" in industry or any(
        term in organization for term in ("hospital", "medical", "clinic")
    )
    return healthcare and _nonempty(row.get("description"))


def _scorton_selection(row: Mapping[str, object]) -> bool:
    """Select Scorton records that contain a non-blank summary."""

    return _nonempty(row.get("Summary"))


def _gvic_selection(row: Mapping[str, object]) -> bool:
    """Select GVIC records that contain non-blank article content."""

    return _nonempty(row.get("content"))


DATASETS = (
    DatasetSpec(
        name="vinitvek-healthcare-all",
        repository="vinitvek/cybersecurityattacks",
        revision="92ed82a32fcd6d1bcfae16722e9ff5a7ab50d46b",
        split="train",
        config=None,
        text_column="description",
        identity_columns=("source_url",),
        selection=_vinitvek_selection,
    ),
    DatasetSpec(
        name="scorton-healthcare-breaches",
        repository="ScortonAI/Cyber-Security-Breaches",
        revision="1da6a89a887067a29fa536441d3f32dce0a5879c",
        split="train",
        config=None,
        text_column="Summary",
        identity_columns=("Name_of_Covered_Entity", "Date_of_Breach"),
        selection=_scorton_selection,
    ),
    DatasetSpec(
        name="gvic-public-health-news",
        repository="gvic-unb/public-health-news-DF-qa",
        revision="9944e31a41e6cc1f3ed484b5d95cca363e6dc5ac",
        split="corpus",
        config="knowledge_base",
        text_column="content",
        identity_columns=("url",),
        selection=_gvic_selection,
    ),
)


def _load_dataset(spec: DatasetSpec):
    """Load a pinned dataset revision using its configured split and subset."""

    from datasets import load_dataset

    kwargs = {
        "path": spec.repository,
        "revision": spec.revision,
        "split": spec.split,
    }
    if spec.config is not None:
        kwargs["name"] = spec.config
    return load_dataset(**kwargs)


def _identity(row: Mapping[str, object], columns: tuple[str, ...], index: int) -> str:
    """Build a stable deduplication key from identity columns or row position."""

    values = [str(row.get(column, "")).strip() for column in columns]
    if not any(values):
        values = [f"row-{index}"]
    return "|".join(values)


def _document_id(dataset_name: str, index: int) -> str:
    """Format a stable, dataset-scoped document identifier."""

    return f"{dataset_name}-{index:06d}"


def _select_unique_records(
    dataset: Iterable[Mapping[str, object]], spec: DatasetSpec
) -> tuple[list[tuple[str, dict[str, object]]], int]:
    """Apply one dataset's selection and identity-based deduplication rules."""

    selected: list[tuple[str, dict[str, object]]] = []
    seen: set[str] = set()
    duplicate_count = 0
    for source_index, raw_row in enumerate(dataset):
        row = dict(raw_row)
        if not spec.selection(row):
            continue
        identity = _identity(row, spec.identity_columns, source_index)
        if identity in seen:
            duplicate_count += 1
            continue
        seen.add(identity)
        text = str(row[spec.text_column]).strip()
        selected.append(
            (identity, {"row": row, "text": text, "source_index": source_index})
        )
    return selected, duplicate_count


def _batch_ranges(
    records: list[tuple[str, dict[str, object]]], batch_size: int, max_chars: int | None
) -> list[tuple[int, int]]:
    """Partition selected records by count and optional character limit."""

    ranges: list[tuple[int, int]] = []
    start = 0
    while start < len(records):
        batch_chars = 0
        end = start
        while end < len(records) and end - start < batch_size:
            candidate_chars = len(str(records[end][1]["text"]))
            if max_chars is not None and end > start and batch_chars + candidate_chars > max_chars:
                break
            batch_chars += candidate_chars
            end += 1
        ranges.append((start, end))
        start = end
    return ranges


def _write_batches(
    spec: DatasetSpec,
    dataset_dir: Path,
    selected: list[tuple[str, dict[str, object]]],
    batch_size: int,
    max_chars: int | None,
) -> int:
    """Write validated source records to numbered JSON batches."""

    for old_batch in (*dataset_dir.glob("batch_*.json"), *dataset_dir.glob("labels_batch_*.json")):
        old_batch.unlink()
    ranges = _batch_ranges(selected, batch_size, max_chars)
    for batch_number, (start, end) in enumerate(ranges, start=1):
        batch_records = []
        for offset, (identity, item) in enumerate(selected[start:end], start=1):
            row = item["row"]
            assert isinstance(row, dict)
            metadata = {
                key: value
                for key, value in row.items()
                if key != spec.text_column and isinstance(value, (str, int, float, bool))
            }
            batch_records.append(
                MuseBatchSource(
                    id=_document_id(spec.name, start + offset),
                    text=str(item["text"]),
                    dataset_identity=identity,
                    source_index=int(item["source_index"]),
                    metadata=metadata,
                ).model_dump()
            )
        batch_path = dataset_dir / f"batch_{batch_number:04d}.json"
        batch_path.write_text(
            json.dumps(batch_records, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    return len(ranges)


def prepare_dataset(
    spec: DatasetSpec, output_root: Path, batch_size: int, max_chars: int | None
) -> dict[str, object]:
    """Filter, deduplicate, batch, and summarize one configured source dataset."""

    if batch_size <= 0 or (max_chars is not None and max_chars <= 0):
        raise ValueError("batch_size and max_chars must be positive when provided")
    selected, duplicate_count = _select_unique_records(_load_dataset(spec), spec)
    dataset_dir = output_root / spec.name
    dataset_dir.mkdir(parents=True, exist_ok=True)
    batches = _write_batches(spec, dataset_dir, selected, batch_size, max_chars)

    all_text = "\n".join(item["text"] for _, item in selected)
    return {
        "name": spec.name,
        "repository": spec.repository,
        "revision": spec.revision,
        "config": spec.config,
        "split": spec.split,
        "text_column": spec.text_column,
        "identity_columns": spec.identity_columns,
        "selection": (
            "healthcare metadata and full available dataset period"
            if spec.name == "vinitvek-healthcare-all"
            else "non-empty source text; Muse performs documented relevance triage"
        ),
        "selected_before_dedup": len(selected) + duplicate_count,
        "duplicates_removed": duplicate_count,
        "selected_after_dedup": len(selected),
        "batches": batches,
        "max_batch_size": batch_size,
        "max_chars_per_batch": max_chars,
        "text_sha256": hashlib.sha256(all_text.encode("utf-8")).hexdigest(),
    }


def main() -> None:
    """Prepare all configured datasets and write their aggregate manifest."""

    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, default=Path("data/raw/muse_batches"))
    parser.add_argument("--manifest", type=Path, default=Path("data/raw/muse_manifest.json"))
    parser.add_argument("--batch-size", type=int, default=50)
    parser.add_argument("--max-chars", type=int, default=None)
    args = parser.parse_args()
    if args.batch_size <= 0:
        parser.error("--batch-size must be positive")
    if args.max_chars is not None and args.max_chars <= 0:
        parser.error("--max-chars must be positive")

    results = [
        prepare_dataset(spec, args.output_root, args.batch_size, args.max_chars)
        for spec in DATASETS
    ]
    manifest = {
        "experiment_status": "extension",
        "annotation_method": "Muse Spark 1.3 Contributor via opencode-go",
        "label_status": "silver_pending_human_audit",
        "labels": ALLOWED_LABELS,
        "selection_period": "full_available_dataset_period",
        "paper_reference_period": {"start": PERIOD_START, "end": PERIOD_END},
        "datasets": results,
        "total_documents": sum(int(item["selected_after_dedup"]) for item in results),
    }
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
