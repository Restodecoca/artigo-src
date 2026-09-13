"""Public data references and the boundary between them and the target corpus."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from healthcare_ner_replication.metrics import EntitySpan

REFERENCE_LABEL_ALIASES = {
    "identity": "IDTY",
    "attack-pattern": "ACT",
    "vulnerability": "VUL",
    "location": "LOC",
}


@dataclass(frozen=True)
class DatasetCandidate:
    """A public dataset that can support validation, not faithful substitution."""

    repository: str
    role: str
    is_original_corpus: bool
    rationale: str
    revision: str | None = None


def public_reference_candidates() -> tuple[DatasetCandidate, ...]:
    """Return public Hugging Face datasets relevant to the reproduction.

    None of these repositories contains the paper's 2023 healthcare-news corpus
    and manual annotations. They are useful for smoke tests, model sanity checks,
    or a clearly labeled external validation experiment.
    """

    return (
        DatasetCandidate(
            repository="zefang-liu/cyberbench",
            role="reference_only",
            is_original_corpus=False,
            rationale="Aggregates APTNER and CyNER benchmarks with different domains and labels.",
        ),
        DatasetCandidate(
            repository="chairulridjal/arcspan-cyber-ner",
            role="reference_only",
            is_original_corpus=False,
            rationale="Provides public cybersecurity NER material, including APTNER-derived files.",
        ),
        DatasetCandidate(
            repository="priamai/AnnoCTR",
            role="reference_only",
            is_original_corpus=False,
            rationale=(
                "Contains annotated cyber-threat reports, not the selected healthcare-news corpus."
            ),
        ),
        DatasetCandidate(
            repository="mrmoor/cyber-threat-intelligence",
            role="reference_only",
            is_original_corpus=False,
            rationale=(
                "Provides 9,732 CC-BY-4.0 cybersecurity texts with character spans; its "
                "identity, attack-pattern, vulnerability, and location labels can be mapped "
                "to IDTY, ACT, VUL, and LOC for external validation, but the text is not "
                "healthcare news."
            ),
            revision="d8783e04f46039f3624df6958dd4d34405d8c72a",
        ),
        DatasetCandidate(
            repository="vinitvek/cybersecurityattacks",
            role="reference_only",
            is_original_corpus=False,
            rationale=(
                "Provides 13,407 cybersecurity incident summaries with source URLs and "
                "structured industry metadata. A reproducible healthcare filter yields "
                "1,852 records, including 367 in the paper's 2023-01-01 to 2023-10-30 "
                "collection period. It has no manual NER spans and is therefore suitable "
                "for a separately documented annotation sample, not immediate scoring."
            ),
            revision="92ed82a32fcd6d1bcfae16722e9ff5a7ab50d46b",
        ),
        DatasetCandidate(
            repository="ScortonAI/Cyber-Security-Breaches",
            role="reference_only",
            is_original_corpus=False,
            rationale=(
                "Provides 1,055 healthcare-breach summaries with directly annotatable text. "
                "The records also include non-cyber loss, theft, and mis-mailing events, so "
                "it is a manual-annotation candidate rather than an immediate evaluation set."
            ),
            revision="1da6a89a887067a29fa536441d3f32dce0a5879c",
        ),
    )


def normalize_reference_entities(
    raw_entities: Iterable[Mapping[str, object]],
) -> list[EntitySpan]:
    """Map the selected HF dataset's target labels to the paper's four labels."""

    spans: list[EntitySpan] = []
    for entity in raw_entities:
        raw_label = str(entity.get("label", "")).strip().lower()
        label = REFERENCE_LABEL_ALIASES.get(raw_label)
        if label is None:
            continue
        start = entity.get("start_offset")
        end = entity.get("end_offset")
        if not isinstance(start, int) or not isinstance(end, int):
            raise ValueError("Reference entities must provide integer character offsets")
        spans.append(EntitySpan(start, end, label))
    return spans
