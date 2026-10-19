"""Inspect actual tokenizer overflow windows in a Colab runtime."""

from __future__ import annotations

import argparse
import json
import tarfile
from pathlib import Path

from transformers import AutoTokenizer

DEFAULT_ARCHIVE = Path("/content/muse_batches.tar.gz")
DEFAULT_MODEL = "CyberPeace-Institute/SecureBERT-NER"
DEFAULT_REVISION = "7f935a4f7db13697580c881e381bb2636dfa779a"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, default=DEFAULT_ARCHIVE)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--revision", default=DEFAULT_REVISION)
    args = parser.parse_args()

    with tarfile.open(args.archive) as archive:
        names = [
            name
            for name in archive.getnames()
            if name.endswith(".json") and "/batch_" in name and "/labels_" not in name
        ]
        records = [record for name in names for record in json.load(archive.extractfile(name))]
    tokenizers = {
        "default": AutoTokenizer.from_pretrained(args.model, revision=args.revision),
        "fast": AutoTokenizer.from_pretrained(args.model, revision=args.revision, use_fast=True),
    }
    for name, tokenizer in tokenizers.items():
        print(f"tokenizer={name} class={type(tokenizer).__name__} is_fast={tokenizer.is_fast}")
        print(f"model_max_length={tokenizer.model_max_length}")
        shown = 0
        for record in records:
            raw = tokenizer(
                record["text"], add_special_tokens=True, truncation=False, verbose=False
            )
            if len(raw["input_ids"]) <= 1000:
                continue
            variants = {
                "implicit_max_length": {"padding": True},
                "explicit_max_length": {"max_length": 512, "padding": True},
                "max_length_padding": {"max_length": 512, "padding": "max_length"},
            }
            counts = {}
            for variant, options in variants.items():
                windowed = tokenizer(
                    record["text"],
                    add_special_tokens=True,
                    truncation=True,
                    return_overflowing_tokens=True,
                    stride=128,
                    verbose=False,
                    **options,
                )
                counts[variant] = (
                    len(windowed["input_ids"]),
                    [len(item) for item in windowed["input_ids"]],
                )
            print(f"{record['id']} raw_tokens={len(raw['input_ids'])} variants={counts}")
            shown += 1
            if shown == 5:
                break


if __name__ == "__main__":
    main()
