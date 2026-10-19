"""Canonical entity labels shared by local corpus and inference code."""

from __future__ import annotations

ENTITY_TYPES = ("IDTY", "ACT", "VUL", "LOC")
_LABEL_ALIASES = {"VULID": "VUL", "VULNAME": "VUL"}


def canonicalize_entity_label(label: object) -> str | None:
    """Map BIO-prefixed and model-specific labels to the project's entity types."""

    value = str(label).strip().upper()
    if "-" in value:
        _, value = value.split("-", maxsplit=1)
    value = _LABEL_ALIASES.get(value, value)
    return value if value in ENTITY_TYPES else None
