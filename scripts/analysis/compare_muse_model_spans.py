"""Build an exact, private Muse-versus-model span comparison report."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _read(path: Path) -> dict[str, Any]:
    """Read a diagnostic JSON object from disk."""

    return json.loads(path.read_text(encoding="utf-8"))


def _overlaps(gold: dict[str, Any], predicted: dict[str, Any]) -> bool:
    """Test whether two half-open character spans overlap."""

    return gold["start"] < predicted["end"] and predicted["start"] < gold["end"]


def _context(text: str, start: int, end: int, radius: int = 80) -> str:
    """Return a whitespace-normalized excerpt surrounding the requested span."""

    excerpt = text[max(0, start - radius) : min(len(text), end + radius)]
    return " ".join(excerpt.split())


def _comparison(
    document: dict[str, Any], model: str, compatible_labels: set[str]
) -> dict[str, Any]:
    """Classify gold and predicted spans and attach local text context."""

    text = document["text"]
    model_document = document["models"][model]
    gold = document["gold_spans"]
    predicted = model_document["predicted_spans"]
    strict_gold = {pair["gold"]: pair["predicted"] for pair in model_document["strict_matches"]}
    partial_gold = {pair["gold"]: pair["predicted"] for pair in model_document["partial_matches"]}
    same_type_gold = {
        pair["gold"]: pair["predicted"]
        for pair in model_document["partial_same_type_matches"]
    }
    strict_pred = {pair["predicted"] for pair in model_document["strict_matches"]}
    partial_pred = {pair["predicted"] for pair in model_document["partial_matches"]}
    same_type_pred = {
        pair["predicted"] for pair in model_document["partial_same_type_matches"]
    }

    gold_rows = []
    for index, span in enumerate(gold):
        if span["label"] not in compatible_labels:
            status = "unmapped_label"
        elif index in strict_gold:
            status = "exact"
        elif index in same_type_gold:
            status = "overlap_same_type"
        elif index in partial_gold:
            status = "overlap_wrong_type"
        else:
            status = "missed"
        overlapping = [
            {
                **candidate,
                "status": (
                    "exact"
                    if strict_gold.get(index) == candidate_index
                    else "overlap_same_type"
                    if same_type_gold.get(index) == candidate_index
                    else "overlap"
                ),
            }
            for candidate_index, candidate in enumerate(predicted)
            if _overlaps(span, candidate)
        ]
        gold_rows.append(
            {
                "status": status,
                "muse": {**span, "index": index},
                "overlapping_model_spans": overlapping,
                "context": _context(text, span["start"], span["end"]),
            }
        )

    prediction_rows = []
    for index, span in enumerate(predicted):
        if index in strict_pred:
            status = "exact"
        elif index in same_type_pred:
            status = "overlap_same_type"
        elif index in partial_pred:
            status = "overlap_wrong_type"
        else:
            status = "false_positive"
        prediction_rows.append(
            {
                "status": status,
                "model": {**span, "index": index},
                "context": _context(text, span["start"], span["end"]),
            }
        )

    return {
        "id": document["id"],
        "gold": gold_rows,
        "model_predictions": prediction_rows,
        "native_model_predictions": model_document.get("native_predicted_spans", []),
    }


def main() -> None:
    """Write a private per-span comparison report for one selected model."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("diagnostic", type=Path)
    parser.add_argument("--model", default=None)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    diagnostic = _read(args.diagnostic)
    documents = diagnostic["documents"]
    models = sorted(documents[0]["models"])
    model = args.model or models[0]
    if model not in models:
        parser.error(f"unknown model {model!r}; choose from {', '.join(models)}")
    compatible_labels = set(diagnostic.get("compatible_labels", {"IDTY", "ACT", "VUL", "LOC"}))
    payload = {
        "model": model,
        "compatible_labels": sorted(compatible_labels),
        "documents": [
            _comparison(document, model, compatible_labels) for document in documents
        ],
    }
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "model": model,
                "documents": len(documents),
                "output": str(args.output),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
