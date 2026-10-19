"""Evaluate offline span post-processing variants against Muse labels.

Reads a private detailed diagnostic artifact, applies deterministic span
transforms to each model's predictions, and scores every variant with the
same matching rules used by the T4 runner. No text is printed.
"""

from __future__ import annotations

import argparse
import json
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any

from healthcare_ner_replication.metrics import EntitySpan, score_entities

WORD_RE = re.compile(r"\w", re.UNICODE)
FILLER_RE = re.compile(r"[\s\W]", re.UNICODE)


def _read(path: Path) -> dict[str, Any]:
    """Load the detailed diagnostic artifact as a JSON object."""

    return json.loads(path.read_text(encoding="utf-8"))


def _score_document(
    gold: list[tuple[int, int, str]],
    predicted: list[tuple[int, int, str]],
) -> dict[str, int]:
    """Count strict, partial, and same-type one-to-one matches for a document."""

    gold_spans = [EntitySpan(start, end, label) for start, end, label in gold]
    predicted_spans = [EntitySpan(start, end, label) for start, end, label in predicted]
    strict = score_entities(gold_spans, predicted_spans, mode="strict")
    partial = score_entities(gold_spans, predicted_spans, mode="partial")
    same_type = score_entities(
        gold_spans, predicted_spans, mode="partial", same_label=True
    )
    return {
        "gold": len(gold),
        "predicted": len(predicted),
        "strict": strict.true_positive,
        "partial": partial.true_positive,
        "partial_same_type": same_type.true_positive,
    }


def _aggregate(scores: list[dict[str, int]]) -> dict[str, float | int]:
    """Sum document counts and compute corpus-level F1 variants."""

    totals = {
        key: sum(score[key] for score in scores)
        for key in ("gold", "predicted", "strict", "partial", "partial_same_type")
    }

    def f1(true_positive: int, predicted: int, gold: int) -> float:
        """Calculate F1 safely for a single set of aggregated counts."""

        precision = true_positive / predicted if predicted else 0.0
        recall = true_positive / gold if gold else 0.0
        return 2 * precision * recall / (precision + recall) if precision + recall else 0.0

    return {
        **totals,
        "strict_f1": f1(totals["strict"], totals["predicted"], totals["gold"]),
        "partial_f1": f1(totals["partial"], totals["predicted"], totals["gold"]),
        "partial_same_type_f1": f1(
            totals["partial_same_type"], totals["predicted"], totals["gold"]
        ),
    }


def _merge_spans(
    spans: list[dict[str, Any]], text: str, can_merge_gap: Callable[[str], bool]
) -> list[dict[str, Any]]:
    """Merge consecutive same-label spans when their intervening gap is allowed."""
    ordered = sorted(spans, key=lambda span: (span["start"], span["end"]))
    merged: list[dict[str, Any]] = []
    for span in ordered:
        previous = merged[-1] if merged else None
        if previous is not None and previous["label"] == span["label"]:
            gap = text[previous["end"] : span["start"]]
            if not can_merge_gap(gap):
                merged.append(span)
                continue
            overlap = any(
                other["start"] < span["start"] and other["end"] > previous["end"]
                for other in ordered
                if other is not previous and other is not span
            )
            if not overlap:
                previous["end"] = span["end"]
                previous["text"] = text[previous["start"] : previous["end"]]
                continue
        merged.append(span)
    return merged


def _merge_adjacent(spans: list[dict[str, Any]], text: str) -> list[dict[str, Any]]:
    """Merge same-label spans separated only by whitespace or punctuation."""
    return _merge_spans(
        spans,
        text,
        lambda gap: not gap or FILLER_RE.fullmatch(gap) is not None,
    )


def _merge_adjacent_words(spans: list[dict[str, Any]], text: str) -> list[dict[str, Any]]:
    """Merge same-label spans separated by spaces or hyphens, unless overlapping."""
    return _merge_spans(spans, text, lambda gap: gap in {"", " ", "-"})


def _drop_punctuation_only(spans: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Remove predicted spans that contain no word character."""

    return [
        span for span in spans if span["text"] is not None and WORD_RE.search(span["text"])
    ]


def _drop_tiny(spans: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Remove spans whose stripped text has at most two characters."""

    return [
        span
        for span in spans
        if span["text"] is not None and len(span["text"].strip()) > 2
    ]


def _expand_word_boundaries(
    spans: list[dict[str, Any]], text: str
) -> list[dict[str, Any]]:
    """Expand span edges through adjacent alphanumeric characters."""

    expanded = []
    for span in spans:
        start = span["start"]
        end = span["end"]
        if WORD_RE.search(text[start:end]):
            while start > 0 and text[start - 1].isalnum():
                start -= 1
            while end < len(text) and text[end].isalnum():
                end += 1
        expanded.append({**span, "start": start, "end": end, "text": text[start:end]})
    return expanded


TRANSFORMS = {
    "baseline": lambda spans, _text: spans,
    "merge_adjacent": _merge_adjacent,
    "drop_punctuation_only": lambda spans, _text: _drop_punctuation_only(spans),
    "drop_tiny": lambda spans, _text: _drop_tiny(spans),
    "merge_plus_drop_punctuation": lambda spans, text: _drop_punctuation_only(
        _merge_adjacent(spans, text)
    ),
    "merge_plus_drop_punctuation_plus_drop_tiny": lambda spans, text: _drop_tiny(
        _drop_punctuation_only(_merge_adjacent(spans, text))
    ),
    "merge_words_plus_drop_punctuation": lambda spans, text: _drop_punctuation_only(
        _merge_adjacent_words(spans, text)
    ),
    "merge_words_plus_drop_punctuation_plus_drop_tiny": lambda spans, text: _drop_tiny(
        _drop_punctuation_only(_merge_adjacent_words(spans, text))
    ),
    "expand_words_merge_plus_drop_punctuation": lambda spans, text: _drop_punctuation_only(
        _merge_adjacent(_expand_word_boundaries(spans, text), text)
    ),
    "expand_words_merge_plus_drop_punctuation_plus_drop_tiny": lambda spans, text: _drop_tiny(
        _drop_punctuation_only(_merge_adjacent(_expand_word_boundaries(spans, text), text))
    ),
}


def main() -> None:
    """Evaluate configured deterministic post-processing variants offline."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("diagnostic", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    diagnostic = _read(args.diagnostic)
    documents = diagnostic["documents"]
    models = sorted(documents[0]["models"])
    result: dict[str, Any] = {
        "source": str(args.diagnostic),
        "documents": len(documents),
        "models": {},
    }
    for model in models:
        model_result: dict[str, Any] = {}
        for name, transform in TRANSFORMS.items():
            scores = []
            for document in documents:
                text = document["text"]
                predicted_spans = transform(
                    [dict(span) for span in document["models"][model]["predicted_spans"]],
                    text,
                )
                gold = [
                    (span["start"], span["end"], span["label"])
                    for span in document["gold_spans"]
                ]
                predicted = [
                    (span["start"], span["end"], span["label"])
                    for span in predicted_spans
                ]
                scores.append(_score_document(gold, predicted))
            model_result[name] = _aggregate(scores)
        result["models"][model] = model_result
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result["models"], indent=2))


if __name__ == "__main__":
    main()
