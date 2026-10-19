"""Versioned facts and guardrails for the selected paper's reproduction."""

from __future__ import annotations

from collections import abc
from dataclasses import dataclass, field
from itertools import pairwise

COLLECTION_PERIOD_START = "2023-01-01"
COLLECTION_PERIOD_END = "2023-10-30"


@dataclass(frozen=True)
class ReproductionProtocol:
    """The original protocol plus explicit evidence and limitation flags.

    This object describes the paper; it does not imply that the original corpus or
    annotations are available locally. A faithful reproduction must clear that
    evidence gap before reporting equivalent results.
    """

    article_title: str
    models: tuple[str, ...]
    entity_types: tuple[str, ...]
    evaluation_modes: tuple[str, ...]
    collection_date: str
    collection_period: tuple[str, str]
    collection_queries: tuple[str, ...]
    source_portals: tuple[str, ...]
    manually_annotated_documents: int
    max_tokens_per_document: int
    corpus_stage_counts: abc.Mapping[str, int]
    original_corpus_available: bool = False
    known_limitations: tuple[str, ...] = field(default_factory=tuple)


def default_protocol() -> ReproductionProtocol:
    """Return the paper's reported protocol without silently filling missing data."""

    return ReproductionProtocol(
        article_title=(
            "An Analysis of Pre-trained Models to Identify Cybersecurity Incidents "
            "Entities in the Healthcare Industry"
        ),
        models=("SecureBERT-NER", "SecureBERT-APTNER"),
        entity_types=("IDTY", "ACT", "VUL", "LOC"),
        evaluation_modes=("strict", "partial"),
        collection_date="2023-10-30",
        collection_period=(COLLECTION_PERIOD_START, COLLECTION_PERIOD_END),
        collection_queries=(
            "hospital AND cyberattack",
            "hospital AND cybersecurity AND incident",
            "healthcare AND cyberattack",
            "healthcare AND cybersecurity AND incident",
        ),
        source_portals=(
            "Security Magazine",
            "Becker's Hospital Review",
            "JD Supra",
        ),
        manually_annotated_documents=60,
        max_tokens_per_document=400,
        corpus_stage_counts={
            "collected": 24_108,
            "unique_links": 15_705,
            "selected_portals": 1_449,
            "final_corpus": 1_039,
        },
        known_limitations=(
            "The original corpus and manual annotations are not distributed with the paper.",
            "The source archive is time-dependent and may contain dead or changed pages.",
            "The paper does not fully specify model revisions, thresholds, and preprocessing.",
            "The manual evaluation protocol does not report independent double annotation.",
            "The paper names Security Magazine in the text but SC Magazine in a results table.",
        ),
    )


def validate_protocol(protocol: ReproductionProtocol) -> ReproductionProtocol:
    """Reject incomplete protocol definitions before data collection or training."""

    if not protocol.models:
        raise ValueError("The protocol must define at least one model")
    if not protocol.entity_types:
        raise ValueError("The protocol must define at least one entity type")
    if not protocol.evaluation_modes:
        raise ValueError("The protocol must define at least one evaluation mode")
    if protocol.manually_annotated_documents <= 0:
        raise ValueError("The protocol must include manually annotated documents")
    if protocol.max_tokens_per_document <= 0:
        raise ValueError("The document token limit must be positive")
    if any(count < 0 for count in protocol.corpus_stage_counts.values()):
        raise ValueError("Corpus stage counts cannot be negative")

    counts = protocol.corpus_stage_counts
    ordered_stages = ("collected", "unique_links", "selected_portals", "final_corpus")
    if any(stage not in counts for stage in ordered_stages):
        raise ValueError(f"Corpus counts must include: {', '.join(ordered_stages)}")
    stage_values = tuple(counts[stage] for stage in ordered_stages)
    if any(left < right for left, right in pairwise(stage_values)):
        raise ValueError("Corpus counts cannot increase after filtering")

    return protocol
