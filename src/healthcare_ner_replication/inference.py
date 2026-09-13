"""Model registry and safe conversion of Transformers NER outputs to spans."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from healthcare_ner_replication.metrics import EntitySpan


@dataclass(frozen=True)
class ModelSpec:
    """A public checkpoint and its label encoding as observed on Hugging Face."""

    repository: str
    label_encoding: str
    revision: str


MODEL_SPECS = {
    "SecureBERT-NER": ModelSpec(
        repository="CyberPeace-Institute/SecureBERT-NER",
        label_encoding="BIO",
        revision="7f935a4f7db13697580c881e381bb2636dfa779a",
    ),
    "SecureBERT-APTNER": ModelSpec(
        repository="Cyber-ThreaD/SecureBERT-APTNER",
        label_encoding="BIOES",
        revision="f220a5fbeb8ed9b60a516cf420fc816d9705ce7d",
    ),
}


def canonicalize_entity_label(label: object) -> str | None:
    """Map checkpoint-specific labels to the paper's four shared entity types."""

    value = str(label).strip().upper()
    if "-" in value:
        _, value = value.split("-", maxsplit=1)
    if value in {"VUL", "VULID", "VULNAME"}:
        return "VUL"
    if value in {"IDTY", "ACT", "LOC"}:
        return value
    return None


def filter_model_entities(raw_entities: Iterable[Mapping[str, object]]) -> list[EntitySpan]:
    """Keep the paper's labels while preserving model-provided character offsets."""

    spans: list[EntitySpan] = []
    for entity in raw_entities:
        raw_label = entity.get("entity_group", entity.get("entity"))
        label = canonicalize_entity_label(raw_label)
        if label is None:
            continue
        start = entity.get("start")
        end = entity.get("end")
        if not isinstance(start, int) or not isinstance(end, int):
            raise ValueError("Model entities must provide integer start and end offsets")
        spans.append(EntitySpan(start, end, label))
    return spans


def infer_text(
    text: str,
    model_name: str,
    *,
    device: str = "auto",
) -> list[EntitySpan]:
    """Run a public token-classification checkpoint and return canonical spans.

    ``transformers`` and a compatible PyTorch build are optional dependencies. The
    import remains inside the function so protocol and metric tests stay CPU-only.
    """

    if model_name not in MODEL_SPECS:
        raise ValueError(f"Unknown model: {model_name}")
    if device not in {"auto", "cpu", "cuda"}:
        raise ValueError("device must be 'auto', 'cpu', or 'cuda'")

    import torch
    from transformers import pipeline

    if device == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA/ROCm was requested but no accelerator is available")
    pipeline_device = (
        0 if device == "cuda" or (device == "auto" and torch.cuda.is_available()) else -1
    )
    spec = MODEL_SPECS[model_name]
    tagger = pipeline(
        "token-classification",
        model=spec.repository,
        revision=spec.revision,
        aggregation_strategy="simple",
        device=pipeline_device,
    )
    return filter_model_entities(tagger(text))
