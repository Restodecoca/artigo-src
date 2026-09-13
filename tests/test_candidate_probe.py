import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))

from run_colab_candidate_probe import (
    build_dataset_kwargs,
    select_first_nonempty_texts,
    validate_probe_limit,
)


def test_select_first_nonempty_texts_returns_aggregate_metadata_only():
    rows = [
        {"Summary": None},
        {"Summary": "  "},
        {"Summary": "First incident"},
        {"Summary": "Second incident"},
    ]

    selected = select_first_nonempty_texts(rows, "Summary", limit=2)

    assert selected["documents"] == 2
    assert selected["characters_total"] == 29
    assert selected["words_total"] == 4
    assert "records" not in selected
    assert "source_index" not in selected


def test_validate_probe_limit_requires_exactly_five_records():
    assert validate_probe_limit(5) == 5
    with pytest.raises(ValueError, match="exactly 5"):
        validate_probe_limit(6)


def test_build_dataset_kwargs_keeps_optional_config_explicit():
    assert build_dataset_kwargs("org/dataset", None, "train") == {
        "path": "org/dataset",
        "split": "train",
        "revision": None,
    }
    assert build_dataset_kwargs("org/dataset", "knowledge_base", "corpus") == {
        "path": "org/dataset",
        "name": "knowledge_base",
        "split": "corpus",
        "revision": None,
    }
