"""Fetch a private 20-per-portal sample for the paper's manual evaluation."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import time
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path

from healthcare_ner_replication.local_corpus import (
    clean_article,
    first_tokens,
    is_blocked_response,
    is_protocol_date,
)

PORTALS = ("Security Magazine", "Becker's Hospital Review", "JD Supra")
PERIOD_START = "2023-01-01"
PERIOD_END = "2023-10-30"
PORTAL_SLUGS = {
    "Security Magazine": "sec",
    "Becker's Hospital Review": "bhr",
    "JD Supra": "jds",
}
MIN_WORDS = 40


def fetch_article(url: str) -> str:
    """Fetch one source URL through the public Jina Reader endpoint."""

    reader_url = "https://r.jina.ai/" + url
    request = urllib.request.Request(
        reader_url,
        headers={"User-Agent": "academic-reproduction-probe/1.0"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8", errors="replace")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("metadata_csv", type=Path)
    parser.add_argument("--output", type=Path, default=Path("data/raw/protocol_60_texts.jsonl"))
    parser.add_argument(
        "--metadata-output",
        type=Path,
        default=Path("data/raw/protocol_60_metadata.json"),
    )
    parser.add_argument("--per-portal", type=int, default=20)
    args = parser.parse_args()
    if args.per_portal != 20:
        parser.error("--per-portal must remain 20 for the paper's protocol")

    rows = list(csv.DictReader(args.metadata_csv.open(encoding="utf-8-sig", newline="")))
    documents: list[dict[str, str]] = []
    failures: list[dict[str, str]] = []
    counts = {portal: 0 for portal in PORTALS}
    selected_urls: set[str] = set()
    for portal in PORTALS:
        seen_urls: set[str] = set()
        candidates = (
            row
            for row in rows
            if row["source"] == portal
            and is_protocol_date(row["date"])
            and row["url"] not in seen_urls
            and row["url"] not in selected_urls
            and not seen_urls.add(row["url"])
        )
        for row in candidates:
            if counts[portal] >= args.per_portal:
                break
            try:
                markdown = fetch_article(row["url"])
                if is_blocked_response(markdown, row["title"]):
                    raise ValueError("blocked or missing article title")
                text = clean_article(markdown, row["title"])
                if len(text.split()) < MIN_WORDS:
                    raise ValueError("extracted text is too short")
            except (OSError, ValueError, urllib.error.URLError) as error:
                failures.append({"source": portal, "url": row["url"], "reason": str(error)})
                time.sleep(0.5)
                continue
            counts[portal] += 1
            selected_urls.add(row["url"])
            documents.append(
                {
                    "document_id": (
                        f"protocol-{PORTAL_SLUGS[portal]}-"
                        f"{hashlib.sha256(row['url'].encode()).hexdigest()[:10]}"
                    ),
                    "source": portal,
                    "published_date": row["date"],
                    "title": row["title"],
                    "source_url": row["url"],
                    "text": first_tokens(text, limit=400),
                }
            )
            time.sleep(0.5)
        if counts[portal] != args.per_portal:
            raise RuntimeError(
                f"Could not fetch {args.per_portal} usable articles for {portal}; "
                f"got {counts[portal]}"
            )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as handle:
        for document in documents:
            handle.write(json.dumps(document, ensure_ascii=False) + "\n")
    args.metadata_output.parent.mkdir(parents=True, exist_ok=True)
    args.metadata_output.write_text(
        json.dumps(
            {
                "experiment_status": "extension",
                "access_date": date.today().isoformat(),
                "selection": {
                    "period_start": PERIOD_START,
                    "period_end": PERIOD_END,
                    "portals": PORTALS,
                    "per_portal": args.per_portal,
                    "max_tokens_per_document": 400,
                },
                "counts": counts,
                "documents": len(documents),
                "failures": failures,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(json.dumps({"documents": len(documents), "counts": counts, "failures": len(failures)}))


if __name__ == "__main__":
    main()
