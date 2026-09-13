import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))

from validate_muse_labels import validate_directory, validate_records


def test_validate_records_accepts_valid_half_open_spans():
    source = [{"id": "doc-1", "text": "Acme exploited MOVEit."}]
    labels = [
        {
            "id": "doc-1",
            "entities": [
                {"start": 0, "end": 4, "label": "IDTY"},
                {"start": 15, "end": 21, "label": "VUL"},
            ],
        }
    ]

    assert validate_records(source, labels) == []


@pytest.mark.parametrize(
    ("entity", "message"),
    [
        ({"start": -1, "end": 2, "label": "IDTY"}, "start must be non-negative"),
        ({"start": 2, "end": 2, "label": "IDTY"}, "end must be greater than start"),
        ({"start": 0, "end": 99, "label": "IDTY"}, "outside text bounds"),
        ({"start": 0, "end": 2, "label": "BAD"}, "unknown label"),
    ],
)
def test_validate_records_reports_invalid_entities(entity, message):
    errors = validate_records(
        [{"id": "doc-1", "text": "Acme"}],
        [{"id": "doc-1", "entities": [entity]}],
    )

    assert any(message in error for error in errors)


def test_validate_records_reports_missing_ids_overlap_and_unsorted_spans():
    errors = validate_records(
        [{"id": "doc-1", "text": "0123456789"}, {"id": "doc-2", "text": "text"}],
        [
            {
                "id": "doc-1",
                "entities": [
                    {"start": 4, "end": 7, "label": "ACT"},
                    {"start": 3, "end": 6, "label": "IDTY"},
                ],
            }
        ],
    )

    assert any("missing label record for doc-2" in error for error in errors)
    assert any("not sorted by start" in error for error in errors)
    assert any("overlaps previous span" in error for error in errors)


def test_validate_records_rejects_duplicate_ids():
    errors = validate_records(
        [{"id": "doc-1", "text": "one"}, {"id": "doc-1", "text": "two"}],
        [{"id": "doc-1", "entities": []}],
    )

    assert any("duplicate source id" in error for error in errors)


def test_validate_records_reports_malformed_records_without_crashing():
    errors = validate_records([None], [None])

    assert any("source record 0 must be an object" in error for error in errors)
    assert any("label record 0 must be an object" in error for error in errors)


def test_validate_directory_reports_orphan_label_files(tmp_path):
    label_path = tmp_path / "labels_batch_01.json"
    label_path.write_text(json.dumps([{"id": "ghost", "entities": []}]), encoding="utf-8")

    errors, source_count, label_count = validate_directory(tmp_path)

    assert source_count == 0
    assert label_count == 0
    assert any("has no matching batch_01.json" in error for error in errors)
