"""Run inference-only SecureBERT diagnostics on a local article export."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from collections import Counter
from pathlib import Path

from healthcare_ner_replication.local_corpus import load_pipe_articles, select_keyword_articles

KEYWORDS = (
    "healthcare",
    "hospital",
    "medical device",
    "patient",
    "clinic",
    "pharma",
    "health system",
)
MODEL_SPECS = {
    "SecureBERT-NER": (
        "CyberPeace-Institute/SecureBERT-NER",
        "7f935a4f7db13697580c881e381bb2636dfa779a",
    ),
    "SecureBERT-APTNER": (
        "Cyber-ThreaD/SecureBERT-APTNER",
        "f220a5fbeb8ed9b60a516cf420fc816d9705ce7d",
    ),
}
TARGET_LABELS = {"IDTY", "ACT", "LOC", "VULID", "VULNAME"}


def _file_sha256(path: Path) -> str:
    """Compute a streaming SHA-256 checksum for the input corpus file."""

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _target_documents(outputs: list[list[dict[str, object]]]) -> list[list[tuple[int, int, str]]]:
    """Normalize each model output to supported entity spans by document."""

    documents = []
    for output in outputs:
        document = []
        for entity in output:
            raw_label = str(entity.get("entity_group", entity.get("entity", ""))).upper()
            if raw_label not in TARGET_LABELS:
                continue
            label = "VUL" if raw_label in {"VULID", "VULNAME"} else raw_label
            document.append((int(str(entity["start"])), int(str(entity["end"])), label))
        documents.append(document)
    return documents


def _agreement(
    first: list[list[tuple[int, int, str]]], second: list[list[tuple[int, int, str]]]
) -> dict[str, float | int]:
    """Measure strict and same-type partial agreement between model outputs."""

    strict = sum(
        sum(any(candidate == other for other in right) for candidate in left)
        for left, right in zip(first, second, strict=True)
    )
    partial = sum(
        sum(
            any(
                candidate[2] == other[2] and candidate[0] < other[1] and other[0] < candidate[1]
                for other in right
            )
            for candidate in left
        )
        for left, right in zip(first, second, strict=True)
    )
    total = sum(map(len, first)) + sum(map(len, second))
    return {
        "strict_true_positive": strict,
        "strict_f1": 2 * strict / total if total else 0.0,
        "partial_true_positive": partial,
        "partial_f1": 2 * partial / total if total else 0.0,
    }


def main() -> None:
    """Run local inference on selected articles and print aggregate diagnostics."""

    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("--limit", type=int, default=60)
    parser.add_argument("--device", type=int, default=-1)
    args = parser.parse_args()

    from transformers import pipeline

    articles = load_pipe_articles(args.input)
    examples = select_keyword_articles(articles, keywords=KEYWORDS, limit=args.limit)
    sample_hash = hashlib.sha256(
        "|".join(article.document_id for article in examples).encode()
    ).hexdigest()
    model_results = []
    target_documents = []
    started = time.perf_counter()
    for name, (repository, revision) in MODEL_SPECS.items():
        tagger = pipeline(
            "token-classification",
            model=repository,
            revision=revision,
            aggregation_strategy="simple",
            device=args.device,
        )
        outputs = [tagger(article.text) for article in examples]
        documents = _target_documents(outputs)
        target_documents.append(documents)
        model_results.append(
            {
                "model": name,
                "repository": repository,
                "revision": revision,
                "target_entities": sum(map(len, documents)),
                "documents_with_target_entities": sum(bool(document) for document in documents),
                "target_label_counts": dict(
                    Counter(span[2] for document in documents for span in document)
                ),
            }
        )
    result = {
        "experiment_status": "inference_only",
        "source_file_sha256": _file_sha256(args.input),
        "selection": {
            "keywords": KEYWORDS,
            "limit": args.limit,
            "sample_id_sha256": sample_hash,
        },
        "documents": len(examples),
        "aggregation_strategy": "simple",
        "models": model_results,
        "agreement": _agreement(target_documents[0], target_documents[1]),
        "seconds": round(time.perf_counter() - started, 2),
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
