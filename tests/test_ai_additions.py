import json
from pathlib import Path

import pytest

from scripts.validation.validate_ai_additions import (
    load_archive_labels,
    load_archive_texts,
    validate_additions,
)

ROOT = Path(__file__).parents[1]
ADDITIONS = ROOT / "data" / "muse-artifacts" / "annotations" / "ai_assisted_additions.json"
ARCHIVE = ROOT / "data" / "muse-artifacts" / "processed" / "muse_corrected.tar.gz"


def _fixture():
    texts = {"doc-1": "Acme Hospital reported a breach."}
    base = {
        "doc-1": {
            "id": "doc-1",
            "entities": [{"start": 0, "end": 13, "label": "IDTY", "text": "Acme Hospital"}],
        }
    }
    additions = {
        "documents": [
            {
                "id": "doc-1",
                "added_entities": [{"start": 25, "end": 31, "label": "ACT", "text": "breach"}],
            }
        ]
    }
    return additions, texts, base


def test_validate_additions_accepts_non_overlapping_spans():
    additions, texts, base = _fixture()

    errors, stats = validate_additions(additions, texts, base)

    assert errors == []
    assert stats["total_added_entities"] == 1
    assert stats["documents_with_additions"] == 1
    assert stats["added_label_counts"] == {"ACT": 1}
    assert stats["augmented_entities"] == 2


def test_validate_additions_rejects_overlap_with_base_layer():
    additions, texts, base = _fixture()
    additions["documents"][0]["added_entities"][0].update(
        {"start": 5, "end": 13, "text": "Hospital"}
    )

    errors, _ = validate_additions(additions, texts, base)

    assert any("overlaps the base layer" in error for error in errors)


def test_validate_additions_rejects_text_mismatch_and_invalid_label():
    additions, texts, base = _fixture()
    additions["documents"][0]["added_entities"] = [
        {"start": 25, "end": 31, "label": "ACT", "text": "wrong"},
        {"start": 25, "end": 31, "label": "BAD", "text": "breach"},
    ]

    errors, _ = validate_additions(additions, texts, base)

    assert any("text mismatch" in error for error in errors)
    assert any("invalid label" in error for error in errors)


def test_validate_additions_rejects_duplicate_surface_in_same_document():
    additions, texts, base = _fixture()
    additions["documents"][0]["added_entities"] = [
        {"start": 25, "end": 31, "label": "ACT", "text": "breach"},
        {"start": 25, "end": 31, "label": "ACT", "text": "breach"},
    ]

    errors, _ = validate_additions(additions, texts, base)

    assert any("duplicated span" in error or "duplicated surface" in error for error in errors)


@pytest.mark.skipif(
    not ADDITIONS.exists() or not ARCHIVE.exists(), reason="private artifacts unavailable"
)
def test_committed_additions_layer_is_valid():
    additions = json.loads(ADDITIONS.read_text(encoding="utf-8"))
    texts = load_archive_texts(ARCHIVE)
    base = load_archive_labels(ARCHIVE)

    errors, stats = validate_additions(additions, texts, base)

    assert errors == []
    assert stats["total_added_entities"] == 687
    assert stats["documents_with_additions"] == 208
    assert stats["augmented_entities"] == 5798
