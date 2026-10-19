"""Package local Muse source/label batches for the Colab validation runner."""

from __future__ import annotations

import argparse
import tarfile
from pathlib import Path


def package(source_dir: Path, output: Path) -> None:
    """Archive all source and label batch files under a stable dataset path."""

    files = sorted(
        path
        for pattern in ("batch_*.json", "labels_batch_*.json")
        for path in source_dir.glob(pattern)
    )
    if not files:
        raise ValueError(f"no Muse batches found in {source_dir}")

    output.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(output, "w:gz") as archive:
        for path in files:
            archive.add(path, arcname=Path("muse_batches") / source_dir.name / path.name)


def main() -> None:
    """Package one local Muse dataset for transfer to a model runner."""

    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    package(args.source, args.output)
    print(args.output)


if __name__ == "__main__":
    main()
