import json

from scripts.fetch_vinitvek_articles import eligible_rows, write_json_atomic


def test_eligible_rows_applies_healthcare_period_and_url_deduplication():
    rows = [
        {
            "event_date": "2023-01-02 00:00:00",
            "affected_industry": "Health Care and Social Assistance",
            "affected_organization": "Example Hospital",
            "source_url": "https://example.test/article",
            "description": "summary",
        },
        {
            "event_date": "2023-01-03 00:00:00",
            "affected_industry": "Health Care and Social Assistance",
            "affected_organization": "Example Hospital",
            "source_url": "https://example.test/article",
            "description": "duplicate",
        },
        {
            "event_date": "2023-10-31 00:00:00",
            "affected_industry": "Health Care and Social Assistance",
            "affected_organization": "Late Hospital",
            "source_url": "https://example.test/late",
            "description": "outside period",
        },
        {
            "event_date": "2023-01-02 00:00:00",
            "affected_industry": "Information",
            "affected_organization": "News Company",
            "source_url": "https://example.test/non-health",
            "description": "wrong domain",
        },
    ]

    selected = eligible_rows(rows)

    assert [row["source_url"] for row in selected] == ["https://example.test/article"]


def test_write_json_atomic_replaces_target_with_durable_json(tmp_path):
    output = tmp_path / "checkpoint.json"

    write_json_atomic(output, {"records": [1, 2]})

    assert json.loads(output.read_text(encoding="utf-8")) == {"records": [1, 2]}
    assert not (tmp_path / ".checkpoint.json.tmp").exists()
