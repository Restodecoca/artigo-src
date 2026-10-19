"""Measure URL overlap between vinitvek and the reconstructed article corpus."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from healthcare_ner_replication.local_corpus import is_protocol_date
from healthcare_ner_replication.protocol import (
    COLLECTION_PERIOD_END,
    COLLECTION_PERIOD_START,
)

START = COLLECTION_PERIOD_START
END = COLLECTION_PERIOD_END
PROTOCOL_SOURCES = {"Security Magazine", "Becker's Hospital Review", "JD Supra"}


def normalize_url(value: str) -> str:
    """Normalize URL host and path while dropping query and fragment components."""

    parsed = urlsplit(value.strip())
    return urlunsplit(
        (
            parsed.scheme.casefold(),
            parsed.netloc.casefold().removeprefix("www."),
            parsed.path.rstrip("/"),
            "",
            "",
        )
    )


def in_period(value: str) -> bool:
    """Check whether an ISO-formatted date falls within the paper's collection period."""
    return is_protocol_date(value[:10])


def read_vinitvek(path: Path) -> list[dict[str, str]]:
    """Load in-period healthcare events that have a non-empty source URL field."""

    with path.open(encoding="utf-8-sig", newline="") as handle:
        return [
            row
            for row in csv.DictReader(handle)
            if in_period(row.get("event_date", ""))
            and (
                "health" in row.get("affected_industry", "").casefold()
                or any(
                    term in row.get("affected_organization", "").casefold()
                    for term in ("hospital", "medical", "clinic")
                )
            )
            and row.get("source_url", "")
        ]


def read_articles(path: Path) -> list[dict[str, str]]:
    """Load article-corpus rows whose dates fall in the comparison period."""

    with path.open(encoding="utf-8-sig", newline="") as handle:
        return [row for row in csv.DictReader(handle) if in_period(row.get("date", ""))]


def overlap(left: list[dict[str, str]], right: list[dict[str, str]]) -> dict[str, object]:
    """Summarize normalized URL overlap, source counts, and sample matches."""

    left_by_url = {normalize_url(row["source_url"]): row for row in left}
    right_by_url = {normalize_url(row["url"]): row for row in right}
    shared = sorted(set(left_by_url) & set(right_by_url))
    return {
        "left_rows": len(left),
        "left_unique_urls": len(left_by_url),
        "right_rows": len(right),
        "right_unique_urls": len(right_by_url),
        "exact_url_overlap": len(shared),
        "left_overlap_percent": round(100 * len(shared) / max(len(left_by_url), 1), 2),
        "right_overlap_percent": round(100 * len(shared) / max(len(right_by_url), 1), 2),
        "shared_right_sources": dict(
            Counter(right_by_url[url].get("source", "unknown") for url in shared)
        ),
        "examples": [
            {
                "url": left_by_url[url]["source_url"],
                "vinitvek_description": left_by_url[url]["description"],
                "article_title": right_by_url[url]["title"],
            }
            for url in shared[:20]
        ],
    }


def main() -> None:
    """Print URL overlap for all articles and the paper's reported portals."""

    parser = argparse.ArgumentParser()
    parser.add_argument("vinitvek_csv", type=Path)
    parser.add_argument(
        "article_csv",
        type=Path,
        default=Path("data/healthcare_cyber_v10_hybrid_1066.csv"),
        nargs="?",
    )
    args = parser.parse_args()

    vinitvek = read_vinitvek(args.vinitvek_csv)
    articles = read_articles(args.article_csv)
    protocol_articles = [row for row in articles if row.get("source") in PROTOCOL_SOURCES]
    print(
        json.dumps(
            {
                "period": {"start": START, "end": END},
                "all_article_corpus": overlap(vinitvek, articles),
                "reported_portal_corpus": overlap(vinitvek, protocol_articles),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
