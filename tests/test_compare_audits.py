import json
from pathlib import Path
from typing import Any

import pytest

from scripts.validation.compare_audits import (
    build_report,
    cohen_kappa,
    fleiss_kappa,
    fleiss_summary,
    format_summary,
    human_vs_muse,
    load_review,
    pairwise_reviews,
)


def _review(
    reviewer: str,
    rows: list[tuple[str, str]],
    *,
    dataset_entities: int | None = None,
    dataset_key: str = "dataset-1",
) -> dict[str, Any]:
    decisions = {}
    for index, (muse_label, human_label) in enumerate(rows):
        key = f"doc-1::{index}::0-1"
        decisions[key] = {
            "human_label": human_label,
            "muse_label": muse_label,
            "uncertain": False,
            "muse_revealed": False,
            "note": "",
        }
    return {
        "path": "",
        "reviewer": reviewer,
        "dataset_key": dataset_key,
        "dataset": {"entities": dataset_entities or len(rows)},
        "decisions": decisions,
    }


def test_cohen_kappa_matches_known_two_by_two_table():
    pairs = [("A", "A")] * 20 + [("A", "B")] * 5 + [("B", "A")] * 10 + [("B", "B")] * 15

    assert cohen_kappa(pairs) == pytest.approx(0.4)


def test_cohen_kappa_handles_empty_and_perfect_agreement():
    assert cohen_kappa([]) is None
    assert cohen_kappa([("IDTY", "IDTY"), ("ACT", "ACT")]) == pytest.approx(1.0)


def test_fleiss_kappa_matches_published_example():
    counts = [
        [0, 0, 0, 0, 14],
        [0, 2, 6, 4, 2],
        [0, 0, 3, 5, 6],
        [0, 3, 9, 2, 0],
        [2, 2, 8, 1, 1],
        [7, 7, 0, 0, 0],
        [3, 2, 6, 3, 0],
        [2, 5, 3, 2, 2],
        [6, 5, 2, 1, 0],
        [0, 2, 2, 3, 7],
    ]
    categories = ["1", "2", "3", "4", "5"]
    ratings = [
        [category for category, count in zip(categories, row, strict=True) for _ in range(count)]
        for row in counts
    ]

    assert fleiss_kappa(ratings) == pytest.approx(0.210, abs=0.001)


def test_fleiss_kappa_rejects_ragged_ratings():
    with pytest.raises(ValueError, match="same number"):
        fleiss_kappa([["A", "A"], ["B"]])


def test_human_vs_muse_reports_confusion_and_label_metrics():
    review = _review(
        "dev1",
        [
            ("IDTY", "IDTY"),
            ("ACT", "IDTY"),
            ("VUL", "NONE"),
            ("LOC", "LOC"),
        ],
    )

    review["decisions"]["doc-1::0::0-1"]["muse_revealed"] = True
    metrics = human_vs_muse(review)

    assert metrics["reviewed"] == 4
    assert metrics["accuracy"] == 0.5
    assert metrics["muse_revealed"] == 1
    assert metrics["confusion"]["ACT"]["IDTY"] == 1
    assert metrics["confusion"]["VUL"]["NONE"] == 1
    assert metrics["per_label"]["IDTY"]["precision"] == 0.5
    assert metrics["per_label"]["IDTY"]["recall"] == 1.0
    assert metrics["per_label"]["ACT"]["recall"] == 0.0
    assert metrics["per_label"]["ACT"]["f1"] == 0.0
    assert metrics["macro_f1"] == pytest.approx(0.4167, abs=0.0001)


def test_macro_f1_counts_labels_with_zero_true_positives():
    review = _review(
        "dev1",
        [
            ("IDTY", "IDTY"),
            ("ACT", "NONE"),
            ("VUL", "NONE"),
        ],
    )

    metrics = human_vs_muse(review)

    assert metrics["macro_f1"] == pytest.approx(1 / 3, abs=0.0001)


def test_human_vs_muse_ignores_boolean_dataset_size():
    review = _review("dev1", [("IDTY", "IDTY")])
    review["dataset"]["entities"] = True

    metrics = human_vs_muse(review)

    assert metrics["coverage"] is None


def test_pairwise_and_fleiss_summary_use_common_items():
    dev1 = _review("dev1", [("IDTY", "IDTY"), ("ACT", "ACT"), ("VUL", "NONE")])
    dev2 = _review("dev2", [("IDTY", "IDTY"), ("ACT", "ACT"), ("VUL", "VUL")])
    dev3 = _review("dev3", [("IDTY", "IDTY"), ("ACT", "NONE"), ("VUL", "VUL")])

    pairs = pairwise_reviews([dev1, dev2, dev3])
    fleiss = fleiss_summary([dev1, dev2, dev3])

    assert len(pairs) == 3
    assert (
        next(pair for pair in pairs if {pair["left"], pair["right"]} == {"dev1", "dev2"})["items"]
        == 3
    )
    assert next(pair for pair in pairs if {pair["left"], pair["right"]} == {"dev1", "dev2"})[
        "accuracy"
    ] == pytest.approx(2 / 3, abs=0.0001)
    assert fleiss["items"] == 3
    assert fleiss["reviewers"] == 3
    assert fleiss["kappa"] is not None


def test_build_report_is_aggregate_only():
    review = _review("dev1", [("IDTY", "IDTY"), ("ACT", "NONE")], dataset_key="abc")
    review["dataset"]["title"] = "SECRET_TITLE"
    review["decisions"]["doc-1::0::0-1"]["note"] = "SECRET_NOTE"
    review["decisions"]["doc-1::0::0-1"]["muse_revealed"] = True

    report = build_report([review])
    serialized = json.dumps(report, ensure_ascii=False)
    summary = format_summary(report)

    assert report["reviewers"] == ["dev1"]
    assert report["dataset_keys"] == ["abc"]
    assert report["human_vs_muse"]["dev1"]["reviewed"] == 2
    assert report["human_vs_muse"]["dev1"]["muse_revealed"] == 1
    assert "decisions" not in json.dumps(report["human_vs_muse"])
    assert "SECRET_TITLE" not in serialized
    assert "SECRET_NOTE" not in serialized
    assert "SECRET_TITLE" not in summary
    assert "SECRET_NOTE" not in summary
    assert "kappa" in summary


def test_build_report_rejects_mixed_datasets():
    dev1 = _review("dev1", [("IDTY", "IDTY")], dataset_key="dataset-1")
    dev2 = _review("dev2", [("IDTY", "IDTY")], dataset_key="dataset-2")

    with pytest.raises(ValueError, match="different datasets"):
        build_report([dev1, dev2])


def test_build_report_rejects_blank_key_mixed_with_known_dataset():
    dev1 = _review("dev1", [("IDTY", "IDTY")], dataset_key="dataset-1")
    dev2 = _review("dev2", [("IDTY", "IDTY")], dataset_key="")

    with pytest.raises(ValueError, match="different datasets"):
        build_report([dev1, dev2])


@pytest.mark.parametrize("dataset_key", [None, "   ", 123])
def test_build_report_rejects_invalid_direct_dataset_keys(dataset_key: object):
    review = _review("dev1", [("IDTY", "IDTY")])
    review["dataset_key"] = dataset_key

    with pytest.raises(ValueError, match="every export must have a dataset_key"):
        build_report([review])


def test_build_report_rejects_all_blank_dataset_keys():
    dev1 = _review("dev1", [("IDTY", "IDTY")], dataset_key="")
    dev2 = _review("dev2", [("IDTY", "IDTY")], dataset_key="")

    with pytest.raises(ValueError, match="every export must have a dataset_key"):
        build_report([dev1, dev2])


def test_build_report_rejects_case_insensitive_duplicate_reviewers():
    dev1 = _review("dev1", [("IDTY", "IDTY")])
    dev1_upper = _review("Dev1", [("IDTY", "IDTY")])

    with pytest.raises(ValueError, match="unique"):
        build_report([dev1, dev1_upper])


def test_build_report_reports_synthetic_demo():
    review = _review("dev1", [("IDTY", "IDTY")])
    review["dataset"]["synthetic_demo"] = True

    report = build_report([review])

    assert report["synthetic_demo"] is True


def test_load_review_accepts_browser_export(tmp_path: Path):
    payload = {
        "schema_version": 1,
        "tool": "muse-annotation-audit",
        "reviewer": "dev2",
        "dataset_key": "d1",
        "dataset": {"entities": 1},
        "decisions": [
            {
                "item_key": "doc-1::0::0-4",
                "document_id": "doc-1",
                "entity_index": 0,
                "start": 0,
                "end": 4,
                "muse_label": "IDTY",
                "human_label": "IDTY",
                "uncertain": False,
                "note": "",
            }
        ],
    }
    path = tmp_path / "review.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    review = load_review(path)

    assert review["reviewer"] == "dev2"
    assert "doc-1::0::0-4" in review["decisions"]


@pytest.mark.parametrize("version", [True, 1.0, "1", 99])
def test_load_review_rejects_unsupported_schema(tmp_path: Path, version: object):
    payload = {
        "schema_version": version,
        "tool": "muse-annotation-audit",
        "reviewer": "dev1",
        "decisions": [],
    }
    path = tmp_path / "review.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="unsupported schema_version"):
        load_review(path)


@pytest.mark.parametrize("dataset_key", [None, "", "   "])
def test_load_review_rejects_missing_dataset_key(tmp_path: Path, dataset_key: object):
    payload = {
        "schema_version": 1,
        "tool": "muse-annotation-audit",
        "reviewer": "dev1",
        "dataset_key": dataset_key,
        "dataset": {"entities": 0},
        "decisions": [],
    }
    path = tmp_path / "review.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="missing dataset_key"):
        load_review(path)


def test_load_review_rejects_missing_schema_and_dataset(tmp_path: Path):
    missing_schema = {
        "tool": "muse-annotation-audit",
        "reviewer": "dev1",
        "dataset_key": "d1",
        "dataset": {"entities": 0},
        "decisions": [],
    }
    missing_dataset = {
        "schema_version": 1,
        "tool": "muse-annotation-audit",
        "reviewer": "dev1",
        "dataset_key": "d1",
        "decisions": [],
    }
    for index, payload in enumerate((missing_schema, missing_dataset)):
        path = tmp_path / f"review-{index}.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        with pytest.raises(ValueError):
            load_review(path)


@pytest.mark.parametrize("entities", [-1, 1.5, "1", True])
def test_load_review_rejects_invalid_dataset_entities(tmp_path: Path, entities: object):
    payload = {
        "schema_version": 1,
        "tool": "muse-annotation-audit",
        "reviewer": "dev1",
        "dataset_key": "d1",
        "dataset": {"entities": entities},
        "decisions": [],
    }
    path = tmp_path / "review.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match=r"dataset\.entities"):
        load_review(path)


def test_load_review_rejects_more_decisions_than_entities(tmp_path: Path):
    payload = {
        "schema_version": 1,
        "tool": "muse-annotation-audit",
        "reviewer": "dev1",
        "dataset_key": "d1",
        "dataset": {"entities": 1},
        "decisions": [
            {
                "item_key": "doc-1::0::0-4",
                "muse_label": "IDTY",
                "human_label": "IDTY",
            },
            {
                "item_key": "doc-1::1::5-9",
                "muse_label": "IDTY",
                "human_label": "IDTY",
            },
        ],
    }
    path = tmp_path / "review.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="exceed dataset"):
        load_review(path)


def test_load_review_rejects_non_boolean_synthetic_demo(tmp_path: Path):
    payload = {
        "schema_version": 1,
        "tool": "muse-annotation-audit",
        "reviewer": "dev1",
        "dataset_key": "d1",
        "dataset": {"entities": 0, "synthetic_demo": "false"},
        "decisions": [],
    }
    path = tmp_path / "review.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="synthetic_demo"):
        load_review(path)


def test_load_review_rejects_non_boolean_flags(tmp_path: Path):
    payload = {
        "schema_version": 1,
        "tool": "muse-annotation-audit",
        "reviewer": "dev1",
        "dataset_key": "d1",
        "dataset": {"entities": 1},
        "decisions": [
            {
                "item_key": "doc-1::0::0-4",
                "muse_label": "IDTY",
                "human_label": "IDTY",
                "uncertain": "false",
            }
        ],
    }
    path = tmp_path / "review.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="uncertain must be a boolean"):
        load_review(path)


def test_load_review_rejects_incomplete_fallback_key(tmp_path: Path):
    payload = {
        "schema_version": 1,
        "tool": "muse-annotation-audit",
        "reviewer": "dev1",
        "dataset_key": "d1",
        "dataset": {"entities": 1},
        "decisions": [
            {
                "document_id": "doc-1",
                "entity_index": None,
                "start": 0,
                "end": 4,
                "muse_label": "IDTY",
                "human_label": "IDTY",
            }
        ],
    }
    path = tmp_path / "review.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="usable item_key"):
        load_review(path)


def test_load_review_rejects_row_reviewer_mismatch(tmp_path: Path):
    payload = {
        "schema_version": 1,
        "tool": "muse-annotation-audit",
        "reviewer": "dev1",
        "dataset_key": "d1",
        "dataset": {"entities": 1},
        "decisions": [
            {
                "item_key": "doc-1::0::0-4",
                "muse_label": "IDTY",
                "human_label": "IDTY",
                "reviewer": "dev2",
            }
        ],
    }
    path = tmp_path / "review.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="row reviewer"):
        load_review(path)


def test_load_review_rejects_invalid_labels(tmp_path: Path):
    payload = {
        "schema_version": 1,
        "tool": "muse-annotation-audit",
        "reviewer": "dev1",
        "dataset_key": "d1",
        "dataset": {"entities": 1},
        "decisions": [
            {
                "item_key": "doc-1::0::0-4",
                "muse_label": "IDTY",
                "human_label": "BAD",
            }
        ],
    }
    path = tmp_path / "review.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="invalid human_label"):
        load_review(path)


def test_load_review_accepts_custom_origin_without_muse_label(tmp_path: Path):
    payload = {
        "schema_version": 1,
        "tool": "muse-annotation-audit",
        "reviewer": "dev1",
        "dataset_key": "d1",
        "dataset": {"entities": 2, "custom_entities": 1},
        "custom_entities": [
            {"doc_id": "doc-1", "start": 8, "end": 12, "label": "VUL"},
        ],
        "decisions": [
            {
                "item_key": "doc-1::0::0-4",
                "muse_label": "IDTY",
                "human_label": "IDTY",
            },
            {
                "item_key": "doc-1::1::8-12",
                "origin": "custom",
                "muse_label": "",
                "human_label": "VUL",
            },
        ],
    }
    path = tmp_path / "review.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    review = load_review(path)
    assert review["decisions"]["doc-1::1::8-12"]["origin"] == "custom"
    metrics = human_vs_muse(review)
    assert metrics["reviewed"] == 2
    assert metrics["custom_added"] == 1
    assert metrics["accuracy"] == 1.0
    assert metrics["cohen_kappa"] == pytest.approx(1.0)
    assert "custom" not in {row for row in metrics["confusion"]}
