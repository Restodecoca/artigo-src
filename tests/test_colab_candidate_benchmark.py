from decimal import Decimal

import pytest

from scripts.colab.run_colab_candidate_benchmark import (
    _identity,
    _percentiles,
    _prediction_metrics,
    _prediction_scores,
    candidate_filter,
    select_sample,
    validate_revision,
)


def test_select_sample_filters_deduplicates_and_is_seed_stable():
    rows = [
        {"text": "duplicate one", "source": "u1", "keep": True},
        {"text": "discarded", "source": "u2", "keep": False},
        {"text": "unique", "source": "u3", "keep": True},
        {"text": "duplicate two", "source": "u1", "keep": True},
    ]

    first, first_stats = select_sample(
        rows,
        text_column="text",
        identity_column="source",
        corpus_id="fixture",
        seed=20260913,
        limit=2,
        eligibility=lambda row: bool(row["keep"]),
    )
    second, second_stats = select_sample(
        rows,
        text_column="text",
        identity_column="source",
        corpus_id="fixture",
        seed=20260913,
        limit=2,
        eligibility=lambda row: bool(row["keep"]),
    )

    assert [row["text"] for row in first] == [row["text"] for row in second]
    assert first_stats == second_stats
    assert first_stats["eligible_before_dedup"] == 3
    assert first_stats["duplicates_removed"] == 1
    assert first_stats["eligible_after_dedup"] == 2


def test_select_sample_rejects_insufficient_eligible_rows():
    with pytest.raises(ValueError, match="only 1 eligible"):
        select_sample(
            [{"text": "one", "source": "u1"}],
            text_column="text",
            identity_column="source",
            corpus_id="fixture",
            seed=20260913,
            limit=2,
        )


def test_select_sample_requires_a_real_identity_column():
    with pytest.raises(ValueError, match="identity column"):
        select_sample(
            [{"text": "one"}],
            text_column="text",
            identity_column="source",
            corpus_id="fixture",
            seed=20260913,
            limit=1,
        )


def test_select_sample_supports_composite_identity_columns():
    selected, stats = select_sample(
        [
            {"text": "first", "entity": "Hospital", "date": "2023-01-01"},
            {"text": "duplicate", "entity": "Hospital", "date": "2023-01-01"},
            {"text": "second", "entity": "Hospital", "date": "2023-01-02"},
        ],
        text_column="text",
        identity_column="entity,date",
        corpus_id="fixture",
        seed=20260913,
        limit=2,
    )

    assert len(selected) == 2
    assert stats["duplicates_removed"] == 1


def test_validate_revision_requires_a_pinned_revision():
    revision = "0123456789abcdef0123456789abcdef01234567"
    assert validate_revision(revision) == revision
    for mutable_revision in (None, "main", "v1.0", "abc123"):
        with pytest.raises(ValueError, match="revision"):
            validate_revision(mutable_revision)


def test_composite_identity_is_unambiguous_and_preserves_zero_values():
    assert _identity({"left": "a|b", "right": "c"}, "left,right", 0) != _identity(
        {"left": "a", "right": "b|c"}, "left,right", 1
    )
    assert _identity({"value": 0}, "value", 0)


def test_healthcare_filter_accepts_timestamp_on_last_date():
    keep = candidate_filter("vinitvek-healthcare-2023")

    assert keep is not None
    assert keep(
        {
            "affected_industry": "Healthcare",
            "affected_organization": "Hospital",
            "event_date": "2023-10-30 00:00:00",
        }
    )


def test_percentiles_use_inclusive_rank_positions():
    summary = _percentiles(list(range(1, 101)))

    assert summary["p90"] == 90
    assert summary["p95"] == 95


def test_failed_documents_are_excluded_from_empty_prediction_metrics():
    summary = _prediction_metrics([1, None, 0], [10, 20, 30])

    assert summary == {
        "documents_processed": 2,
        "predicted_entities": 1,
        "documents_with_entities": 1,
        "empty_prediction_rate": 0.5,
        "entities_per_100_words": 2.5,
    }


def test_prediction_scores_accept_numeric_backend_values():
    assert _prediction_scores([{"entity_group": "IDTY", "score": Decimal("0.75")}]) == [0.75]


def test_prediction_scores_raise_for_invalid_confidence_instead_of_skipping():
    with pytest.raises(ValueError, match="invalid confidence score"):
        _prediction_scores([{"entity_group": "IDTY", "score": "not-a-number"}])
