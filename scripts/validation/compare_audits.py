"""Aggregate exported Muse human audits without reproducing article text.

The browser tool writes one export per reviewer. This module compares each
reviewer with the Muse suggestion and compares reviewers with each other. Its
output contains only identifiers, labels, counts, and agreement statistics.
Notes and entity text are intentionally not included.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import UTC, datetime
from itertools import combinations
from pathlib import Path
from typing import Any

ENTITY_TYPES = ("IDTY", "ACT", "VUL", "LOC")
AUDIT_LABELS = (*ENTITY_TYPES, "NONE")
TOOL_NAME = "muse-annotation-audit"


def _read_json(path: Path) -> dict[str, Any]:
    """Read a UTF-8 JSON object, accepting an optional byte-order mark."""

    with path.open(encoding="utf-8-sig") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"{path}: export must be a JSON object")
    return data


def _strict_bool(row: dict[str, Any], field: str, path: Path) -> bool:
    """Read an optional boolean field without accepting truthy strings."""

    value = row.get(field, False)
    if not isinstance(value, bool):
        raise ValueError(f"{path}: {field} must be a boolean")
    return value


def load_review(path: Path) -> dict[str, Any]:
    """Load and validate one browser audit export."""

    data = _read_json(path)
    if data.get("tool") != TOOL_NAME:
        raise ValueError(f"{path}: not a {TOOL_NAME} export")
    version = data.get("schema_version")
    if isinstance(version, bool) or not isinstance(version, int) or version != 1:
        raise ValueError(f"{path}: unsupported schema_version {version!r}")
    reviewer = data.get("reviewer")
    if not isinstance(reviewer, str) or not reviewer.strip():
        raise ValueError(f"{path}: missing reviewer")
    reviewer = reviewer.strip()
    dataset_key = data.get("dataset_key")
    if not isinstance(dataset_key, str) or not dataset_key.strip():
        raise ValueError(f"{path}: missing dataset_key")
    dataset = data.get("dataset")
    if not isinstance(dataset, dict):
        raise ValueError(f"{path}: dataset must be an object")
    if "synthetic_demo" in dataset and not isinstance(dataset["synthetic_demo"], bool):
        raise ValueError(f"{path}: dataset.synthetic_demo must be a boolean")
    entity_count = dataset.get("entities")
    if isinstance(entity_count, bool) or not isinstance(entity_count, int) or entity_count < 0:
        raise ValueError(f"{path}: dataset.entities must be a non-negative integer")
    rows = data.get("decisions")
    if not isinstance(rows, list):
        raise ValueError(f"{path}: decisions must be a list")

    decisions: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError(f"{path}: every decision must be an object")
        row_reviewer = row.get("reviewer")
        if row_reviewer is not None and (
            not isinstance(row_reviewer, str) or row_reviewer.strip() != reviewer
        ):
            raise ValueError(f"{path}: row reviewer does not match export reviewer")
        human_label = row.get("human_label")
        muse_label = row.get("muse_label")
        origin = row.get("origin", "muse")
        if origin not in ("muse", "custom"):
            raise ValueError(f"{path}: invalid origin {origin!r}")
        if human_label not in AUDIT_LABELS:
            raise ValueError(f"{path}: invalid human_label {human_label!r}")
        if origin == "muse":
            if muse_label not in ENTITY_TYPES:
                raise ValueError(f"{path}: invalid muse_label {muse_label!r}")
        else:
            # Entities added by a reviewer have no Muse suggestion to compare.
            muse_label = ""
        key = row.get("item_key")
        if not isinstance(key, str) or not key:
            document_id = row.get("document_id")
            entity_index = row.get("entity_index")
            start = row.get("start")
            end = row.get("end")
            if (
                not isinstance(document_id, (str, int))
                or isinstance(document_id, bool)
                or not isinstance(entity_index, int)
                or isinstance(entity_index, bool)
                or not isinstance(start, int)
                or isinstance(start, bool)
                or not isinstance(end, int)
                or isinstance(end, bool)
            ):
                raise ValueError(f"{path}: decision without a usable item_key")
            key = f"{document_id}::{entity_index}::{start}-{end}"
        if key in decisions:
            raise ValueError(f"{path}: duplicate decision {key}")
        decisions[key] = {
            "human_label": human_label,
            "muse_label": muse_label,
            "origin": origin,
            "uncertain": _strict_bool(row, "uncertain", path),
            "muse_revealed": _strict_bool(row, "muse_revealed", path),
            "note": str(row.get("note") or ""),
        }

    if len(decisions) > entity_count:
        raise ValueError(f"{path}: reviewed decisions exceed dataset.entities")
    return {
        "path": str(path),
        "reviewer": reviewer,
        "dataset_key": dataset_key.strip(),
        "dataset": dataset,
        "decisions": decisions,
    }


def cohen_kappa(pairs: list[tuple[str, str]]) -> float | None:
    """Return Cohen's kappa for paired categorical ratings."""

    if not pairs:
        return None
    total = len(pairs)
    observed = sum(left == right for left, right in pairs) / total
    left_counts = Counter(left for left, _ in pairs)
    right_counts = Counter(right for _, right in pairs)
    categories = set(left_counts) | set(right_counts)
    expected = sum(
        (left_counts[category] / total) * (right_counts[category] / total)
        for category in categories
    )
    if expected >= 1.0:
        return 1.0 if observed >= 1.0 else 0.0
    return (observed - expected) / (1.0 - expected)


def fleiss_kappa(ratings: list[list[str]]) -> float | None:
    """Return Fleiss' kappa for a fixed set of raters per item."""

    if not ratings:
        return None
    rater_count = len(ratings[0])
    if rater_count < 2:
        raise ValueError("Fleiss' kappa requires at least two raters")
    if any(len(row) != rater_count for row in ratings):
        raise ValueError("every item must have the same number of ratings")

    item_count = len(ratings)
    proportions: list[float] = []
    totals: Counter[str] = Counter()
    for row in ratings:
        counts = Counter(row)
        totals.update(counts)
        numerator = sum(count * count for count in counts.values()) - rater_count
        proportions.append(numerator / (rater_count * (rater_count - 1)))

    observed = sum(proportions) / item_count
    expected = sum((count / (item_count * rater_count)) ** 2 for count in totals.values())
    if expected >= 1.0:
        return 1.0 if observed >= 1.0 else 0.0
    return (observed - expected) / (1.0 - expected)


def _round(value: float | None) -> float | None:
    """Round a metric for stable JSON output."""

    return None if value is None else round(value, 4)


def human_vs_muse(review: dict[str, Any]) -> dict[str, Any]:
    """Compare one reviewer's labels with the Muse labels."""

    decisions = list(review["decisions"].values())
    reviewed = len(decisions)
    # Human-added entities have no Muse suggestion; Muse agreement is measured
    # only on the original queue items.
    muse_rows = [row for row in decisions if row.get("origin", "muse") == "muse"]
    agreements = sum(row["human_label"] == row["muse_label"] for row in muse_rows)
    confident = [row for row in muse_rows if not row["uncertain"]]
    confident_agreements = sum(row["human_label"] == row["muse_label"] for row in confident)

    per_label: dict[str, dict[str, int | float | None]] = {}
    raw_f1: dict[str, float | None] = {}
    supports: dict[str, int] = {}
    for label in AUDIT_LABELS:
        true_positive = sum(
            row["muse_label"] == label and row["human_label"] == label for row in muse_rows
        )
        false_positive = sum(
            row["muse_label"] != label and row["human_label"] == label for row in muse_rows
        )
        false_negative = sum(
            row["muse_label"] == label and row["human_label"] != label for row in muse_rows
        )
        support = sum(row["muse_label"] == label for row in muse_rows)
        predicted = true_positive + false_positive
        precision = true_positive / predicted if predicted else 0.0 if support else None
        recall = true_positive / support if support else 0.0 if predicted else None
        f1 = (
            2 * precision * recall / (precision + recall)
            if precision is not None and recall is not None and precision + recall > 0
            else 0.0
            if precision is not None and recall is not None
            else None
        )
        raw_f1[label] = f1
        supports[label] = support
        per_label[label] = {
            "support": support,
            "predicted": predicted,
            "true_positive": true_positive,
            "false_positive": false_positive,
            "false_negative": false_negative,
            "precision": _round(precision),
            "recall": _round(recall),
            "f1": _round(f1),
        }

    macro_f1_values: list[float] = []
    for label in AUDIT_LABELS:
        value = raw_f1[label]
        if supports[label] > 0 and value is not None:
            macro_f1_values.append(value)
    macro_f1 = sum(macro_f1_values) / len(macro_f1_values) if macro_f1_values else None

    confusion: dict[str, dict[str, int]] = {}
    for row in muse_rows:
        muse = row["muse_label"]
        human = row["human_label"]
        confusion.setdefault(muse, {label: 0 for label in AUDIT_LABELS})
        confusion[muse][human] += 1

    dataset = review["dataset"]
    total_entities = dataset.get("entities")
    coverage = (
        reviewed / total_entities
        if isinstance(total_entities, int)
        and not isinstance(total_entities, bool)
        and total_entities > 0
        else None
    )
    return {
        "reviewed": reviewed,
        "custom_added": sum(row.get("origin", "muse") == "custom" for row in decisions),
        "coverage": _round(coverage),
        "accuracy": _round(agreements / len(muse_rows) if muse_rows else None),
        "cohen_kappa": _round(
            cohen_kappa([(row["muse_label"], row["human_label"]) for row in muse_rows])
        ),
        "confident_reviewed": len(confident),
        "confident_accuracy": _round(confident_agreements / len(confident) if confident else None),
        "uncertain": sum(row["uncertain"] for row in decisions),
        "muse_revealed": sum(bool(row.get("muse_revealed")) for row in decisions),
        "with_note": sum(bool(row["note"]) for row in decisions),
        "macro_f1": _round(macro_f1),
        "per_label": per_label,
        "confusion": confusion,
    }


def pairwise_reviews(reviews: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Compare every reviewer pair on the items both reviewed."""

    result: list[dict[str, Any]] = []
    for left, right in combinations(sorted(reviews, key=lambda item: item["reviewer"]), 2):
        common = sorted(set(left["decisions"]) & set(right["decisions"]))
        pairs = [
            (left["decisions"][key]["human_label"], right["decisions"][key]["human_label"])
            for key in common
        ]
        agreements = sum(a == b for a, b in pairs)
        inconsistent_muse = sum(
            left["decisions"][key]["muse_label"] != right["decisions"][key]["muse_label"]
            for key in common
        )
        result.append(
            {
                "left": left["reviewer"],
                "right": right["reviewer"],
                "items": len(common),
                "agreements": agreements,
                "accuracy": _round(agreements / len(common) if common else None),
                "cohen_kappa": _round(cohen_kappa(pairs)),
                "inconsistent_muse_labels": inconsistent_muse,
            }
        )
    return result


def fleiss_summary(reviews: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute Fleiss' kappa on items reviewed by every supplied reviewer."""

    if len(reviews) < 2:
        return {"reviewers": len(reviews), "items": 0, "kappa": None}
    common = set(reviews[0]["decisions"])
    for review in reviews[1:]:
        common &= set(review["decisions"])
    keys = sorted(common)
    ratings = [[review["decisions"][key]["human_label"] for review in reviews] for key in keys]
    kappa = fleiss_kappa(ratings) if ratings else None
    return {
        "reviewers": len(reviews),
        "items": len(keys),
        "kappa": _round(kappa),
    }


def build_report(reviews: list[dict[str, Any]]) -> dict[str, Any]:
    """Build a privacy-preserving aggregate report."""

    reviewer_names = [review["reviewer"] for review in reviews]
    if len(reviewer_names) != len({name.casefold() for name in reviewer_names}):
        raise ValueError("reviewer names must be unique across exports")
    normalized_keys: set[str] = set()
    for review in reviews:
        key = review.get("dataset_key")
        if not isinstance(key, str) or not key.strip():
            raise ValueError(
                "exports refer to different datasets; every export must have a dataset_key"
            )
        normalized_keys.add(key.strip())
    if len(normalized_keys) > 1:
        found = ", ".join(sorted(normalized_keys))
        raise ValueError(
            "exports refer to different datasets; compare only audits from the same "
            f"dataset_key (found: {found})"
        )
    dataset_keys = sorted(normalized_keys)
    return {
        "experiment_status": "extension",
        "tool": TOOL_NAME,
        "generated_at": datetime.now(UTC).isoformat(),
        "reviewers": reviewer_names,
        "dataset_keys": dataset_keys,
        "synthetic_demo": any(bool(review["dataset"].get("synthetic_demo")) for review in reviews),
        "human_vs_muse": {review["reviewer"]: human_vs_muse(review) for review in reviews},
        "pairwise_human": pairwise_reviews(reviews),
        "fleiss_kappa": fleiss_summary(reviews),
    }


def format_summary(report: dict[str, Any]) -> str:
    """Format the aggregate report for a terminal."""

    lines = [
        "Auditoria Muse - resumo agregado",
        f"Revisores: {', '.join(report['reviewers'])}",
    ]
    if report["dataset_keys"]:
        lines.append(f"Conjuntos: {', '.join(report['dataset_keys'])}")
    lines.append("")
    lines.append("Humano vs Muse:")
    for reviewer, metrics in report["human_vs_muse"].items():
        accuracy = _format_percent(metrics["accuracy"])
        kappa = _format_metric(metrics["cohen_kappa"])
        lines.append(
            f"  {reviewer}: {accuracy} | kappa {kappa} | "
            f"{metrics['reviewed']} revisadas | {metrics['uncertain']} incertas | "
            f"{metrics['muse_revealed']} com Muse revelada"
        )
    if report["pairwise_human"]:
        lines.append("")
        lines.append("Entre revisores (itens em comum):")
        for pair in report["pairwise_human"]:
            lines.append(
                f"  {pair['left']} x {pair['right']}: {_format_percent(pair['accuracy'])} | "
                f"kappa {_format_metric(pair['cohen_kappa'])} | n={pair['items']}"
            )
    fleiss = report["fleiss_kappa"]
    lines.append("")
    lines.append(
        f"Fleiss kappa: {_format_metric(fleiss['kappa'])} "
        f"(n={fleiss['items']}, {fleiss['reviewers']} revisores)"
    )
    return "\n".join(lines)


def _format_percent(value: float | None) -> str:
    """Format a proportion as a percentage for the terminal."""

    return "n/a" if value is None else f"{value * 100:.1f}%"


def _format_metric(value: float | None) -> str:
    """Format a kappa value for the terminal."""

    return "n/a" if value is None else f"{value:.3f}"


def main() -> None:
    """Run the comparison from the command line."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reviews", nargs="+", type=Path, help="exported audit JSON files")
    parser.add_argument("--output", type=Path, help="write the aggregate JSON here")
    parser.add_argument("--json", action="store_true", help="print JSON instead of a summary")
    args = parser.parse_args()

    if args.output:
        output_path = args.output.resolve()
        same_path = any(path.resolve() == output_path for path in args.reviews)
        same_file = args.output.exists() and any(
            path.exists() and path.samefile(args.output) for path in args.reviews
        )
        if same_path or same_file:
            parser.error("--output must not overwrite one of the review exports")

    reviews = [load_review(path) for path in args.reviews]
    report = build_report(reviews)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(format_summary(report))
    if args.output:
        print(f"Agregado salvo em {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
