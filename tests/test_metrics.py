import pytest

from healthcare_ner_replication.metrics import EntitySpan, score_entities


def test_strict_matching_requires_same_boundaries_and_entity_type():
    gold = [EntitySpan(0, 7, "B-IDTY")]
    predicted = [EntitySpan(0, 7, "B-ACT")]

    result = score_entities(gold, predicted, mode="strict")

    assert result.true_positive == 0
    assert result.false_positive == 1
    assert result.false_negative == 1
    assert result.f1 == 0.0


def test_partial_matching_accepts_overlapping_boundaries_without_type_match():
    gold = [EntitySpan(0, 14, "B-IDTY")]
    predicted = [EntitySpan(5, 10, "B-ACT")]

    result = score_entities(gold, predicted, mode="partial")

    assert result.true_positive == 1
    assert result.false_positive == 0
    assert result.false_negative == 0
    assert result.f1 == 1.0


def test_partial_matching_is_one_to_one_and_does_not_reward_duplicate_predictions():
    gold = [EntitySpan(0, 8, "B-ACT")]
    predicted = [EntitySpan(0, 8, "B-ACT"), EntitySpan(0, 8, "B-ACT")]

    result = score_entities(gold, predicted, mode="partial")

    assert result.true_positive == 1
    assert result.false_positive == 1
    assert result.false_negative == 0


def test_metrics_reject_unknown_matching_modes():
    with pytest.raises(ValueError, match=r"strict.*partial"):
        score_entities([], [], mode="token")
