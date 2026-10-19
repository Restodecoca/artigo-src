"""Analyze private per-document Muse/model diagnostics without changing labels."""

from __future__ import annotations

import argparse
import json
import re
import statistics
from collections import Counter
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

ERROR_MARKERS = (
    "site not found",
    "page not found",
    "404",
    "captcha",
    "access denied",
    "enable javascript",
    "request unsuccessful",
    "just a moment",
    "cloudflare",
)
WORD_RE = re.compile(r"\w", re.UNICODE)


def _read(path: Path) -> Any:
    """Parse a UTF-8 JSON artifact from disk."""

    return json.loads(path.read_text(encoding="utf-8"))


def _sources(directory: Path) -> dict[str, dict[str, Any]]:
    """Index source records from all batch files by document ID."""

    records = {}
    for path in sorted(directory.glob("batch_*.json")):
        for record in _read(path):
            records[record["id"]] = record
    return records


def _metric(documents: list[dict[str, Any]], model: str) -> dict[str, int | float]:
    """Aggregate entity counts and partial-match precision/recall for a model."""

    model_documents = [document["models"][model] for document in documents]
    gold = sum(len(document["gold_spans"]) for document in documents)
    predicted = sum(len(item["predicted_spans"]) for item in model_documents)
    strict = sum(len(item["strict_matches"]) for item in model_documents)
    partial = sum(len(item["partial_matches"]) for item in model_documents)
    return {
        "documents": len(documents),
        "gold_entities": gold,
        "predicted_entities": predicted,
        "strict_true_positive": strict,
        "partial_true_positive": partial,
        "partial_false_positive": predicted - partial,
        "partial_false_negative": gold - partial,
        "partial_precision": partial / predicted if predicted else 0.0,
        "partial_recall": partial / gold if gold else 0.0,
    }


def _label_metrics(
    documents: list[dict[str, Any]], model: str
) -> dict[str, dict[str, int | float]]:
    """Compute gold counts and match recall separately for each entity type."""

    result: dict[str, dict[str, int | float]] = {}
    for label in ("IDTY", "ACT", "VUL", "LOC"):
        gold = 0
        partial = 0
        partial_same_type = 0
        strict = 0
        for document in documents:
            gold_spans = document["gold_spans"]
            model_document = document["models"][model]
            gold += sum(span["label"] == label for span in gold_spans)
            partial_gold = {
                pair["gold"] for pair in model_document["partial_matches"]
            }
            partial_same_gold = {
                pair["gold"]
                for pair in model_document["partial_same_type_matches"]
            }
            strict_gold = {pair["gold"] for pair in model_document["strict_matches"]}
            partial += sum(
                index in partial_gold and span["label"] == label
                for index, span in enumerate(gold_spans)
            )
            partial_same_type += sum(
                index in partial_same_gold and span["label"] == label
                for index, span in enumerate(gold_spans)
            )
            strict += sum(
                index in strict_gold and span["label"] == label
                for index, span in enumerate(gold_spans)
            )
        result[label] = {
            "gold": gold,
            "partial_matches": partial,
            "partial_same_type_matches": partial_same_type,
            "strict_matches": strict,
            "partial_recall": partial / gold if gold else 0.0,
            "partial_same_type_recall": partial_same_type / gold if gold else 0.0,
        }
    return result


def _cuts_word(document: dict[str, Any], span: dict[str, Any]) -> bool:
    """Return whether either span boundary falls inside an alphanumeric word."""

    text = document["text"]
    start = span["start"]
    end = span["end"]
    starts_inside_word = (
        start > 0
        and start < len(text)
        and text[start - 1].isalnum()
        and text[start].isalnum()
    )
    ends_inside_word = (
        end > 0
        and end < len(text)
        and text[end - 1].isalnum()
        and text[end].isalnum()
    )
    return starts_inside_word or ends_inside_word


def _bins(documents: list[dict[str, Any]], model: str) -> dict[str, dict[str, int | float]]:
    """Group model metrics by document token-length ranges."""

    with_lengths = [
        document
        for document in documents
        if isinstance(document["models"][model].get("token_length"), int)
    ]
    groups = {
        "under_or_equal_512": [
            document
            for document in with_lengths
            if document["models"][model]["token_length"] <= 512
        ],
        "513_to_1024": [
            document
            for document in with_lengths
            if 512 < document["models"][model]["token_length"] <= 1024
        ],
        "over_1024": [
            document
            for document in with_lengths
            if document["models"][model]["token_length"] > 1024
        ],
    }
    return {name: _metric(group, model) for name, group in groups.items()}


def _examples(
    documents: list[dict[str, Any]], model: str, key: str, limit: int
) -> list[dict[str, Any]]:
    """Return the highest-error documents with bounded span and text previews."""

    ranked = sorted(
        documents,
        key=lambda document: (
            len(document["models"][model]["predicted_spans"])
            - len(document["models"][model]["partial_matches"])
            if key == "false_positives"
            else len(document["gold_spans"])
            - len(document["models"][model]["partial_matches"])
        ),
        reverse=True,
    )
    result = []
    for document in ranked[:limit]:
        model_document = document["models"][model]
        partial_indices = {
            pair["predicted"] for pair in model_document["partial_matches"]
        }
        unmatched_predicted = [
            span
            for index, span in enumerate(model_document["predicted_spans"])
            if index not in partial_indices
        ]
        gold_indices = {pair["gold"] for pair in model_document["partial_matches"]}
        unmatched_gold = [
            span
            for index, span in enumerate(document["gold_spans"])
            if index not in gold_indices
        ]
        result.append(
            {
                "id": document["id"],
                "token_length": model_document["token_length"],
                "window_count": model_document["window_count"],
                "gold_entities": len(document["gold_spans"]),
                "predicted_entities": len(model_document["predicted_spans"]),
                "partial_matches": len(model_document["partial_matches"]),
                "unmatched_predicted": unmatched_predicted[:10],
                "unmatched_gold": unmatched_gold[:10],
                "text_preview": document["text"][:400].replace("\n", " "),
            }
        )
    return result


def main() -> None:
    """Analyze diagnostics and print aggregate quality and error summaries."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "diagnostic",
        type=Path,
        default=Path("data/raw/vinitvek-articles-2023-muse-detailed.json"),
        nargs="?",
    )
    parser.add_argument(
        "--source-dir", type=Path, default=Path("data/raw/vinitvek-articles-2023")
    )
    parser.add_argument("--top", type=int, default=5)
    parser.add_argument("--summary-only", action="store_true")
    args = parser.parse_args()
    if args.top <= 0:
        parser.error("--top must be positive")

    diagnostic = _read(args.diagnostic)
    documents = diagnostic["documents"]
    sources = _sources(args.source_dir)
    models = sorted(documents[0]["models"])

    source_errors = []
    source_lengths = []
    marker_records = []
    domains: Counter[str] = Counter()
    detailed_text_mismatches = 0
    replacement_characters = 0
    replacement_documents = 0
    ellipsis_documents = 0
    markdown_heading_documents = 0
    for identifier, source in sources.items():
        title = str(source.get("title", ""))
        body = str(source.get("body", ""))
        text = str(source.get("text", ""))
        body_words = len(body.split())
        source_lengths.append(body_words)
        replacements = text.count("\ufffd")
        replacement_characters += replacements
        replacement_documents += bool(replacements)
        ellipsis_documents += body.rstrip().endswith("...")
        markdown_heading_documents += "##" in body
        expected = f"{title}\n{body}".strip()
        if text != expected:
            source_errors.append(identifier)
        lowered = text.casefold()
        markers = [marker for marker in ERROR_MARKERS if marker in lowered]
        if markers:
            marker_records.append({"id": identifier, "markers": markers})
        url = str(source.get("metadata", {}).get("source_url", ""))
        domains[urlsplit(url).netloc.casefold()] += 1
    for document in documents:
        if document["id"] in sources and document["text"] != sources[document["id"]]["text"]:
            detailed_text_mismatches += 1

    result: dict[str, Any] = {
        "documents": len(documents),
        "source_records": len(sources),
        "source_text_mismatches": len(source_errors),
        "detailed_text_mismatches": detailed_text_mismatches,
        "source_body_words": {
            "min": min(source_lengths, default=0),
            "median": statistics.median(source_lengths) if source_lengths else 0,
            "max": max(source_lengths, default=0),
            "under_40": sum(length < 40 for length in source_lengths),
        },
        "source_text_quality": {
            "replacement_characters": replacement_characters,
            "documents_with_replacement_characters": replacement_documents,
            "bodies_ending_in_ellipsis": ellipsis_documents,
            "documents_with_markdown_headings": markdown_heading_documents,
        },
        "error_page_markers": marker_records,
        "source_domains": dict(domains),
        "gold_label_counts": dict(
            Counter(
                span["label"]
                for document in documents
                for span in document["gold_spans"]
            )
        ),
        "models": {},
    }
    for model in models:
        model_documents = [document["models"][model] for document in documents]
        predicted_spans = [
            span
            for model_document in model_documents
            for span in model_document["predicted_spans"]
        ]
        predicted_label_counts = Counter(span["label"] for span in predicted_spans)
        model_result: dict[str, Any] = {
            "overall": _metric(documents, model),
            "label_metrics": _label_metrics(documents, model),
            "predicted_label_counts": dict(predicted_label_counts),
            "length_bins": _bins(documents, model),
            "documents_with_zero_predictions": sum(
                not document["models"][model]["predicted_spans"] for document in documents
            ),
            "documents_with_zero_gold": sum(
                not document["gold_spans"] for document in documents
            ),
            "window_count_distribution": dict(
                Counter(model_document["window_count"] for model_document in model_documents)
            ),
            "tiny_predicted_spans": sum(
                len(span["text"].strip()) <= 2
                for span in predicted_spans
                if span["text"] is not None
            ),
            "punctuation_only_predicted_spans": sum(
                not WORD_RE.search(span["text"])
                for span in predicted_spans
                if span["text"] is not None and span["text"].strip()
            ),
            "predicted_spans_cutting_words": sum(
                _cuts_word(document, span)
                for document in documents
                for span in document["models"][model]["predicted_spans"]
            ),
        }
        if not args.summary_only:
            model_result["largest_partial_false_positive_cases"] = _examples(
                documents, model, "false_positives", args.top
            )
            model_result["largest_partial_missed_gold_cases"] = _examples(
                documents, model, "missed_gold", args.top
            )
        result["models"][model] = model_result
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
