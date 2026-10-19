"""Fetch full article text behind the vinitvek incident source URLs.

The generated article records are private local inputs for a separate Muse
annotation extension. Raw article text is written below ``data/raw/`` only.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import subprocess
import tempfile
import time
import urllib.error
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path
from typing import Any

from healthcare_ner_replication.article_fetch import fetch_jina_reader_markdown
from healthcare_ner_replication.local_corpus import (
    clean_reader_article,
    is_unusable_reader_response,
    reader_title,
)
from healthcare_ner_replication.protocol import (
    COLLECTION_PERIOD_END,
    COLLECTION_PERIOD_START,
)

REPOSITORY = "vinitvek/cybersecurityattacks"
REVISION = "92ed82a32fcd6d1bcfae16722e9ff5a7ab50d46b"
FIRECRAWL_COMMAND = "firecrawl.cmd" if os.name == "nt" else "firecrawl"
if os.name == "nt":
    FIRECRAWL_COMMAND = (
        "node",
        str(
            Path(os.environ.get("APPDATA", Path.home() / "AppData/Roaming"))
            / "npm"
            / "node_modules"
            / "firecrawl-cli"
            / "dist"
            / "index.js"
        ),
    )
else:
    FIRECRAWL_COMMAND = ("firecrawl",)
ARTICLE_SCHEMA = Path(__file__).with_name("article_extract_schema.json")
PERIOD_START = date.fromisoformat(COLLECTION_PERIOD_START)
PERIOD_END = date.fromisoformat(COLLECTION_PERIOD_END)
MIN_WORDS = 40


def _healthcare_row(row: dict[str, Any]) -> bool:
    """Return whether incident metadata indicates a healthcare organization."""

    industry = str(row.get("affected_industry", "")).casefold()
    organization = str(row.get("affected_organization", "")).casefold()
    return "health" in industry or any(
        term in organization for term in ("hospital", "medical", "clinic")
    )


def _event_date(row: dict[str, Any]) -> date | None:
    """Parse the source event date, returning ``None`` when it is invalid."""

    value = str(row.get("event_date", ""))[:10]
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def eligible_rows(dataset: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Select unique healthcare incident URLs in the paper's date window."""

    selected: list[dict[str, Any]] = []
    seen_urls: set[str] = set()
    for row in dataset:
        url = str(row.get("source_url", "")).strip()
        current_date = _event_date(row)
        if (
            not _healthcare_row(row)
            or current_date is None
            or not PERIOD_START <= current_date <= PERIOD_END
            or not url.startswith(("http://", "https://"))
            or url in seen_urls
            or not str(row.get("description", "")).strip()
        ):
            continue
        seen_urls.add(url)
        selected.append(row)
    return selected


def fetch_article(url: str, timeout: float = 30.0) -> str:
    """Fetch one source URL through the public Jina Reader endpoint."""
    return fetch_jina_reader_markdown(url, timeout=timeout)


def fetch_firecrawl_article(url: str, timeout: float = 60.0) -> str:
    """Fetch one URL through the authenticated Firecrawl CLI."""

    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".md", delete=False) as handle:
            temporary_path = Path(handle.name)
        result = subprocess.run(
            [
                *FIRECRAWL_COMMAND,
                "scrape",
                url,
                "--only-main-content",
                "--format",
                "markdown",
                "--output",
                str(temporary_path),
            ],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        if result.returncode != 0:
            detail = result.stderr.strip() or result.stdout.strip() or "unknown Firecrawl error"
            raise RuntimeError(detail)
        return temporary_path.read_text(encoding="utf-8")
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def fetch_firecrawl_structured_article(
    url: str, timeout: float = 60.0
) -> tuple[str, str]:
    """Fetch only an article title and body with Firecrawl structured extraction."""

    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as handle:
            temporary_path = Path(handle.name)
        result = subprocess.run(
            [
                *FIRECRAWL_COMMAND,
                "scrape",
                url,
                "--only-main-content",
                "--format",
                "json",
                "--schema-file",
                str(ARTICLE_SCHEMA),
                "--json",
                "--pretty",
                "--output",
                str(temporary_path),
            ],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        if result.returncode != 0:
            detail = result.stderr.strip() or result.stdout.strip() or "unknown Firecrawl error"
            raise RuntimeError(detail)
        payload = json.loads(temporary_path.read_text(encoding="utf-8"))
        extracted = payload.get("json", {})
        title = extracted.get("title")
        body = extracted.get("body")
        if not isinstance(title, str) or not isinstance(body, str):
            raise ValueError("Firecrawl returned no title/body pair")
        return title.strip(), body.strip()
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def fetch_records(
    rows: list[dict[str, Any]],
    limit: int,
    delay: float,
    timeout: float,
    scraper: str,
    workers: int,
    checkpoint: Callable[[list[dict[str, Any]], list[dict[str, str]]], None] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    """Fetch up to ``limit`` usable articles and collect per-URL failures."""

    records: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []

    def retrieve(row: dict[str, Any]) -> tuple[tuple[str, str] | None, str | None]:
        """Fetch and normalize one row, returning either content or an error."""

        url = str(row["source_url"])
        try:
            if scraper == "firecrawl-json":
                title, body = fetch_firecrawl_structured_article(url, timeout=timeout)
            else:
                response = (
                    fetch_firecrawl_article(url, timeout=timeout)
                    if scraper == "firecrawl"
                    else fetch_article(url, timeout=timeout)
                )
                if is_unusable_reader_response(response):
                    raise ValueError("reader returned a block or error page")
                text = clean_reader_article(response)
                title = reader_title(response) or str(row.get("description", "")).strip()
                body = text.removeprefix(title).strip() if title else text
            if len(body.split()) < MIN_WORDS:
                raise ValueError("extracted article body is shorter than 40 words")
            return (title, body), None
        except (
            OSError,
            RuntimeError,
            ValueError,
            urllib.error.URLError,
            subprocess.TimeoutExpired,
        ) as error:
            return None, str(error)

    with ThreadPoolExecutor(max_workers=workers) as executor:
        for start in range(0, len(rows), workers):
            if len(records) >= limit:
                break
            batch = rows[start : start + workers]
            results = executor.map(retrieve, batch)
            for row, (content, error) in zip(batch, results, strict=True):
                url = str(row["source_url"])
                if error is not None:
                    failures.append({"url": url, "reason": error})
                    continue
                assert content is not None
                title, body = content
                text = f"{title}\n{body}".strip()
                records.append(
                    {
                        "id": f"vinitvek-article-2023-{len(records) + 1:04d}",
                        "title": title,
                        "body": body,
                        "text": text,
                        "dataset_identity": url,
                        "source_index": row.get("source_index"),
                        "metadata": {
                            key: value
                            for key, value in row.items()
                            if key != "description"
                            and isinstance(value, (str, int, float, bool))
                        },
                        "article_text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                    }
                )
                if len(records) >= limit:
                    break
            print(
                f"Firecrawl: tested {start + len(batch)} links; "
                f"accepted {len(records)}/{limit}",
                flush=True,
            )
            if checkpoint is not None:
                checkpoint(records, failures)
            if delay:
                time.sleep(delay)
    return records, failures


def load_rows(input_csv: Path | None) -> list[dict[str, Any]]:
    """Load source rows from a supplied CSV or the pinned Hugging Face dataset."""

    if input_csv is not None:
        with input_csv.open(encoding="utf-8-sig", newline="") as handle:
            return [dict(row) for row in csv.DictReader(handle)]

    from datasets import load_dataset

    dataset = load_dataset(REPOSITORY, revision=REVISION, split="train")
    return [dict(row) for row in dataset]


def load_existing_records(output_root: Path) -> list[dict[str, Any]]:
    """Restore batch records, preferring a newer resumable checkpoint."""

    records: list[dict[str, Any]] = []
    for batch_path in sorted(output_root.glob("batch_*.json")):
        records.extend(json.loads(batch_path.read_text(encoding="utf-8")))
    checkpoint_path = output_root / ".checkpoint.json"
    if checkpoint_path.exists():
        checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
        checkpoint_records = checkpoint.get("records", [])
        if isinstance(checkpoint_records, list) and len(checkpoint_records) > len(records):
            records = checkpoint_records
    return records


def write_json_atomic(path: Path, payload: object) -> None:
    """Persist JSON durably before replacing the previous complete file."""

    temporary_path = path.with_name(f".{path.name}.tmp")
    with temporary_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary_path, path)


def main() -> None:
    """Fetch eligible articles, resume if requested, and write batches and manifest."""

    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=60)
    parser.add_argument("--delay", type=float, default=0.5)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument(
        "--scraper", choices=("firecrawl-json", "firecrawl", "jina"), default="firecrawl-json"
    )
    parser.add_argument("--input-csv", type=Path)
    parser.add_argument(
        "--output-root", type=Path, default=Path("data/raw/vinitvek-articles-2023")
    )
    parser.add_argument(
        "--manifest", type=Path, default=Path("data/raw/vinitvek-articles-2023.json")
    )
    args = parser.parse_args()
    if args.limit <= 0:
        parser.error("--limit must be positive")
    if args.delay < 0:
        parser.error("--delay cannot be negative")
    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    if args.workers <= 0:
        parser.error("--workers must be positive")

    rows = eligible_rows(load_rows(args.input_csv))
    args.output_root.mkdir(parents=True, exist_ok=True)
    existing = load_existing_records(args.output_root) if args.resume else []
    checkpoint_path = args.output_root / ".checkpoint.json"
    existing_urls = {
        str(record.get("metadata", {}).get("source_url", record.get("dataset_identity", "")))
        for record in existing
    }
    pending_rows = [row for row in rows if str(row["source_url"]) not in existing_urls]
    remaining = max(args.limit - len(existing), 0)

    def checkpoint(new_records: list[dict[str, Any]], failures: list[dict[str, str]]) -> None:
        """Atomically persist accumulated records and failures for resumption."""

        write_json_atomic(
            checkpoint_path,
            {"records": existing + new_records, "failures": failures},
        )

    new_records, failures = fetch_records(
        pending_rows,
        remaining,
        args.delay,
        args.timeout,
        args.scraper,
        args.workers,
        checkpoint,
    )
    records = existing + new_records
    for index, record in enumerate(records, start=1):
        record["id"] = f"vinitvek-article-2023-{index:04d}"
    if not records:
        raise RuntimeError("no usable linked articles were fetched")

    for old_batch in args.output_root.glob("batch_*.json"):
        old_batch.unlink()
    batch_paths = []
    for batch_number, start in enumerate(range(0, len(records), 50), start=1):
        batch_path = args.output_root / f"batch_{batch_number:04d}.json"
        write_json_atomic(
            batch_path,
            records[start : start + 50],
        )
        batch_paths.append(str(batch_path))
    manifest = {
        "experiment_status": "extension",
        "annotation_method": "pending Muse annotation",
        "repository": REPOSITORY,
        "revision": REVISION,
        "scraper": args.scraper,
        "extraction": "Firecrawl JSON schema with title and body fields"
        if args.scraper == "firecrawl-json"
        else "title/body normalization from scraped Markdown",
        "selection": {
            "period_start": PERIOD_START.isoformat(),
            "period_end": PERIOD_END.isoformat(),
            "healthcare_filter": (
                "health in affected_industry or hospital/medical/clinic "
                "in affected_organization"
            ),
            "deduplication": "source_url",
        },
        "eligible_unique_urls": len(rows),
        "requested_articles": args.limit,
        "fetched_articles": len(records),
        "resumed_articles": len(existing),
        "failures": failures,
        "output": batch_paths,
        "text_policy": (
            "full cleaned article text retained locally; never publish raw text "
            "or per-document labels"
        ),
    }
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    write_json_atomic(args.manifest, manifest)
    checkpoint_path.unlink(missing_ok=True)
    print(json.dumps({"eligible": len(rows), "fetched": len(records), "failures": len(failures)}))


if __name__ == "__main__":
    main()
