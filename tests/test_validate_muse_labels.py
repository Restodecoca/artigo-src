import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))

from run_colab_muse_validation import (
    _aligned_window_ranges,
    _postprocess_spans,
    _window_ranges,
)
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


def test_window_ranges_cover_long_documents_with_overlap():
    ranges = _window_ranges(token_count=1045, window_size=510, stride=128)

    assert ranges == [(0, 510), (382, 892), (764, 1045)]
    assert ranges[1][0] - ranges[0][0] == 382
    assert ranges[-1][1] == 1045


def test_window_ranges_keep_short_documents_in_one_window():
    assert _window_ranges(token_count=400, window_size=510, stride=128) == [(0, 400)]


def test_window_ranges_reject_invalid_stride():
    with pytest.raises(ValueError, match="stride"):
        _window_ranges(token_count=100, window_size=100, stride=100)


def test_aligned_window_ranges_do_not_split_words():
    text = "alpha beta gamma delta epsilon zeta"
    offsets = [
        (0, 5),
        (5, 6),
        (6, 10),
        (10, 11),
        (11, 16),
        (16, 17),
        (17, 22),
        (22, 23),
        (23, 30),
        (30, 31),
        (31, 35),
    ]

    ranges = _aligned_window_ranges(offsets, text, window_size=5, stride=2)

    assert ranges[-1][1] == len(offsets)
    assert all(
        start == 0
        or text[offsets[start][0]].isspace()
        or text[offsets[start][0] - 1].isspace()
        for start, _ in ranges
    )


def test_postprocess_merges_subword_zero_day_and_drops_punctuation():
    text = "zero-day vulnerability\n"
    spans = [(0, 4, "VUL"), (4, 5, "VUL"), (5, 8, "VUL"), (22, 23, "IDTY")]

    assert _postprocess_spans(spans, text, "merge_drop_punctuation") == [
        (0, 8, "VUL")
    ]


def test_postprocess_keeps_short_word_entities_without_tiny_policy():
    text = "US"
    spans = [(0, 2, "LOC")]

    assert _postprocess_spans(spans, text, "merge_drop_punctuation") == spans
    assert _postprocess_spans(spans, text, "merge_drop_punctuation_drop_tiny") == []


def test_postprocess_expands_partial_word_boundaries():
    text = "Medical"
    spans = [(3, 7, "IDTY")]

    assert _postprocess_spans(
        spans, text, "expand_words_merge_drop_punctuation_drop_tiny"
    ) == [(0, 7, "IDTY")]
