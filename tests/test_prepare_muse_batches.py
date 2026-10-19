import json

import pytest

from scripts.data.prepare_muse_batches import (
    DatasetSpec,
    _batch_ranges,
    _select_unique_records,
    _write_batches,
)


def _spec() -> DatasetSpec:
    return DatasetSpec(
        name="fixture",
        repository="fixture/repo",
        revision="revision",
        split="train",
        config=None,
        text_column="text",
        identity_columns=("url",),
        selection=lambda row: bool(str(row.get("text", "")).strip()),
    )


def test_select_unique_records_filters_and_deduplicates_by_identity():
    records, duplicates = _select_unique_records(
        [
            {"url": "https://example.test/1", "text": " first "},
            {"url": "https://example.test/1", "text": "duplicate"},
            {"url": "https://example.test/2", "text": " "},
            {"url": "https://example.test/3", "text": "third"},
        ],
        _spec(),
    )

    assert duplicates == 1
    assert [identity for identity, _ in records] == [
        "https://example.test/1",
        "https://example.test/3",
    ]
    assert records[0][1]["text"] == "first"


def test_batch_ranges_respects_record_and_character_limits():
    records = [(str(index), {"text": text}) for index, text in enumerate(("aa", "bb", "ccc"))]

    assert _batch_ranges(records, batch_size=2, max_chars=4) == [(0, 2), (2, 3)]
    assert _batch_ranges(records, batch_size=1, max_chars=None) == [(0, 1), (1, 2), (2, 3)]


def test_write_batches_validates_and_writes_expected_source_shape(tmp_path):
    selected, _ = _select_unique_records(
        [{"url": "https://example.test/1", "text": "article", "year": 2023}], _spec()
    )

    count = _write_batches(_spec(), tmp_path, selected, batch_size=10, max_chars=None)

    assert count == 1
    record = json.loads((tmp_path / "batch_0001.json").read_text(encoding="utf-8"))[0]
    assert record == {
        "id": "fixture-000001",
        "text": "article",
        "dataset_identity": "https://example.test/1",
        "source_index": 0,
        "metadata": {"url": "https://example.test/1", "year": 2023},
    }


@pytest.mark.parametrize("batch_size,max_chars", [(0, None), (1, 0)])
def test_prepare_dataset_rejects_nonpositive_limits(batch_size, max_chars, tmp_path):
    from scripts.data.prepare_muse_batches import prepare_dataset

    with pytest.raises(ValueError, match="must be positive"):
        prepare_dataset(_spec(), tmp_path, batch_size=batch_size, max_chars=max_chars)
