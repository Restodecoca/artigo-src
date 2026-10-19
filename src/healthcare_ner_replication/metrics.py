"""Entity-level metrics matching the paper's Strict and Partial definitions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

MatchingMode = Literal["strict", "partial"]


@dataclass(frozen=True)
class EntitySpan:
    """A half-open character span with its predicted or gold entity type."""

    start: int
    end: int
    label: str

    def __post_init__(self) -> None:
        """Reject invalid half-open offsets and empty entity labels."""

        if self.start < 0 or self.end <= self.start:
            raise ValueError("Entity spans must satisfy 0 <= start < end")
        if not self.label:
            raise ValueError("Entity spans must have a label")


@dataclass(frozen=True)
class EntityMetrics:
    """Counts and derived precision, recall, and F1 for one document or corpus."""

    true_positive: int
    false_positive: int
    false_negative: int

    @property
    def precision(self) -> float:
        """Return true positives divided by all predicted entities."""

        denominator = self.true_positive + self.false_positive
        return self.true_positive / denominator if denominator else 0.0

    @property
    def recall(self) -> float:
        """Return true positives divided by all gold entities."""

        denominator = self.true_positive + self.false_negative
        return self.true_positive / denominator if denominator else 0.0

    @property
    def f1(self) -> float:
        """Return the harmonic mean of precision and recall."""

        denominator = self.precision + self.recall
        return 2 * self.precision * self.recall / denominator if denominator else 0.0


def _matches(
    gold: EntitySpan,
    predicted: EntitySpan,
    mode: MatchingMode,
    same_label: bool = False,
) -> bool:
    """Check a strict typed match or overlap with an optional label constraint."""

    if mode == "strict":
        return (
            gold.start == predicted.start
            and gold.end == predicted.end
            and gold.label == predicted.label
        )
    overlaps = gold.start < predicted.end and predicted.start < gold.end
    return overlaps and (not same_label or gold.label == predicted.label)


def _maximum_matching(
    gold: list[EntitySpan],
    predicted: list[EntitySpan],
    mode: MatchingMode,
    same_label: bool = False,
) -> int:
    """Find the maximum one-to-one number of compatible gold/predicted spans."""

    edges = [
        [
            gold_index
            for gold_index, gold_span in enumerate(gold)
            if _matches(gold_span, span, mode, same_label)
        ]
        for span in predicted
    ]
    gold_to_prediction: dict[int, int] = {}

    def visit(prediction_index: int, visited: set[int]) -> bool:
        """Assign a prediction to an available compatible gold span recursively."""

        for gold_index in edges[prediction_index]:
            if gold_index in visited:
                continue
            visited.add(gold_index)
            previous_prediction = gold_to_prediction.get(gold_index)
            if previous_prediction is None or visit(previous_prediction, visited):
                gold_to_prediction[gold_index] = prediction_index
                return True
        return False

    return sum(visit(index, set()) for index in range(len(predicted)))


def score_entities(
    gold: list[EntitySpan],
    predicted: list[EntitySpan],
    *,
    mode: MatchingMode,
    same_label: bool = False,
) -> EntityMetrics:
    """Score spans one-to-one, optionally requiring equal labels for partial matches."""

    if mode not in {"strict", "partial"}:
        raise ValueError("mode must be either 'strict' or 'partial'")

    true_positive = _maximum_matching(gold, predicted, mode, same_label)
    return EntityMetrics(
        true_positive=true_positive,
        false_positive=len(predicted) - true_positive,
        false_negative=len(gold) - true_positive,
    )
