"""Package raw Muse sources with the adjudicated label overlay."""

from __future__ import annotations

import argparse
import tarfile
from pathlib import Path


def package(source_dir: Path, labels_dir: Path, output: Path) -> None:
    source_batches = sorted(source_dir.glob("batch_*.json"))
    if not source_batches:
        raise ValueError(f"no source batches found in {source_dir}")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(output, "w:gz") as archive:
        root = Path("muse_batches") / "vinitvek-healthcare-corrected"
        for source_path in source_batches:
            label_path = labels_dir / source_path.name.replace("batch_", "labels_batch_")
            if not label_path.exists():
                raise FileNotFoundError(label_path)
            archive.add(source_path, arcname=root / source_path.name)
            archive.add(label_path, arcname=root / label_path.name)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source_dir", type=Path)
    parser.add_argument("labels_dir", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    package(args.source_dir, args.labels_dir, args.output)
    print(args.output)


if __name__ == "__main__":
    main()
