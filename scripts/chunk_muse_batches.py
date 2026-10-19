"""Create smaller source chunks for long-document Muse annotation runs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _read(path: Path) -> list[dict[str, Any]]:
    return json.loads(path.read_text(encoding="utf-8"))


def chunk_sources(source_dir: Path, chunk_dir: Path, size: int) -> None:
    chunk_dir.mkdir(parents=True, exist_ok=True)
    chunk_number = 1
    for batch_path in sorted(source_dir.glob("batch_*.json")):
        records = _read(batch_path)
        for start in range(0, len(records), size):
            output = chunk_dir / f"batch_{chunk_number:04d}.json"
            output.write_text(
                json.dumps(records[start : start + size], ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            chunk_number += 1


def merge_labels(source_dir: Path, chunk_dir: Path) -> None:
    by_id: dict[str, dict[str, Any]] = {}
    for label_path in sorted(chunk_dir.glob("labels_batch_*.json")):
        for label in _read(label_path):
            identifier = str(label["id"])
            if identifier in by_id:
                raise ValueError(f"duplicate label id: {identifier}")
            by_id[identifier] = label

    for source_path in sorted(source_dir.glob("batch_*.json")):
        sources = _read(source_path)
        labels = []
        for source in sources:
            identifier = str(source["id"])
            if identifier not in by_id:
                raise ValueError(f"missing label id: {identifier}")
            labels.append(by_id[identifier])
        output = source_dir / f"labels_{source_path.name}"
        output.write_text(json.dumps(labels, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source_dir", type=Path)
    parser.add_argument("chunk_dir", type=Path)
    parser.add_argument("--size", type=int, default=10)
    parser.add_argument("--merge", action="store_true")
    args = parser.parse_args()
    if args.size <= 0:
        parser.error("--size must be positive")
    if args.merge:
        merge_labels(args.source_dir, args.chunk_dir)
    else:
        chunk_sources(args.source_dir, args.chunk_dir, args.size)


if __name__ == "__main__":
    main()
