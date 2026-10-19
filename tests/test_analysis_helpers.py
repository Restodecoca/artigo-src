from scripts.analysis.evaluate_span_postprocessing import (
    _merge_adjacent,
    _merge_adjacent_words,
)
from scripts.analysis.measure_corpus_overlap import in_period


def test_merge_adjacent_combines_spans_across_single_punctuation_character():
    spans = [
        {"start": 0, "end": 4, "label": "IDTY", "text": "Acme"},
        {"start": 5, "end": 9, "label": "IDTY", "text": "Corp"},
    ]

    merged = _merge_adjacent(spans, "Acme,Corp")

    assert merged == [{"start": 0, "end": 9, "label": "IDTY", "text": "Acme,Corp"}]


def test_merge_adjacent_words_combines_spans_separated_by_hyphen():
    spans = [
        {"start": 0, "end": 4, "label": "VUL", "text": "zero"},
        {"start": 5, "end": 8, "label": "VUL", "text": "day"},
    ]

    merged = _merge_adjacent_words(spans, "zero-day")

    assert merged == [{"start": 0, "end": 8, "label": "VUL", "text": "zero-day"}]


def test_corpus_overlap_reuses_protocol_date_range():
    assert in_period("2023-01-01")
    assert in_period("2023-10-30T12:00:00")
    assert not in_period("2022-12-31")
    assert not in_period("invalid")
