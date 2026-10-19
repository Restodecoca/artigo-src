"""Load the locally supplied multiline cybersecurity article export."""

from __future__ import annotations

import csv
import re
from collections.abc import Iterable
from datetime import date
from pathlib import Path
from typing import Annotated

from pydantic import ConfigDict, Field
from pydantic.dataclasses import dataclass

from healthcare_ner_replication.protocol import (
    COLLECTION_PERIOD_END,
    COLLECTION_PERIOD_START,
)


@dataclass(frozen=True)
class LocalArticle:
    """Validated article record from the local two-column export."""

    __pydantic_config__ = ConfigDict(extra="forbid")

    document_id: Annotated[str, Field(pattern=r"^\d+$")]
    text: str


def load_pipe_articles(path: str | Path) -> list[LocalArticle]:
    """Load ``id|multiline quoted text`` records without altering article text."""

    articles: list[LocalArticle] = []
    with Path(path).open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle, delimiter="|", strict=True)
        try:
            for row_number, row in enumerate(reader, start=1):
                if len(row) != 2 or not row[0].isdigit():
                    raise ValueError(f"Malformed row {row_number}: expected numeric id and text")
                articles.append(LocalArticle(document_id=row[0], text=row[1]))
        except csv.Error as error:
            raise ValueError(f"CSV syntax error near row {reader.line_num}: {error}") from error
    return articles


def select_keyword_articles(
    articles: Iterable[LocalArticle], *, keywords: Iterable[str], limit: int
) -> list[LocalArticle]:
    """Select the first records containing any keyword, preserving source order."""

    if limit <= 0:
        raise ValueError("limit must be positive")
    normalized_keywords = tuple(keyword.casefold() for keyword in keywords if keyword)
    selected = [
        article
        for article in articles
        if any(keyword in article.text.casefold() for keyword in normalized_keywords)
    ]
    if len(selected) < limit:
        raise ValueError(f"Only {len(selected)} records matched the selection keywords")
    return selected[:limit]


def first_tokens(text: str, *, limit: int) -> str:
    """Return the first whitespace-delimited tokens in normalized form."""

    if limit <= 0:
        raise ValueError("limit must be positive")
    return " ".join(text.split()[:limit])


def clean_article(markdown: str, title: str) -> str:
    """Extract a readable article body from a Jina Reader Markdown response."""

    marker = f"# {title}"
    body = markdown.split(marker, 1)[1] if marker in markdown else markdown
    for stop_marker in (
        "\n## Most Read",
        "\n## Related",
        "\n## Share This Story",
        "\n### Share This Story",
        "\n# Recommended",
        "\nLooking for a reprint",
        "\nKEYWORDS:",
        "\n**This article originally",
        "\nCopyright ©",
    ):
        body = body.split(stop_marker, 1)[0]
    body = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", body)
    body = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", body)
    body = re.sub(r"https?://\S+", " ", body)
    body = re.sub(r"^[>#*_`-]+(?:\s+|$)", "", body, flags=re.MULTILINE)
    body = re.sub(r"[*_`]", "", body)
    return re.sub(r"\s+", " ", body).strip()


def reader_title(markdown: str) -> str:
    """Return the title exposed in a Jina Reader response, when available."""

    for line in markdown.splitlines():
        if line.startswith("Title:"):
            return line.removeprefix("Title:").strip()
        if line.startswith("# "):
            return line.removeprefix("# ").strip()
    return ""


def clean_reader_article(markdown: str) -> str:
    """Extract article text from the metadata-wrapped Jina Reader response."""

    body = markdown.split("Markdown Content:", 1)[-1]
    title = reader_title(markdown)
    if body == markdown and title:
        body = clean_article(markdown, title)
    elif title and title in body:
        body = body.split(title, 1)[1]
    for stop_marker in (
        "\n## Most Read",
        "\n## Related",
        "\n## Briefs",
        "\n## Share This Story",
        "\n### Share This Story",
        "\n# Recommended",
        "\n- [News Briefs]",
        "\n\n- [News Briefs]",
        "\nNews Briefs",
        " News Briefs",
        "\nNo previous article",
        "\nLooking for a reprint",
        "\nKEYWORDS:",
        "\n**This article originally",
        "\nCopyright ©",
    ):
        body = body.split(stop_marker, 1)[0]
    body = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", body)
    body = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", body)
    body = re.sub(r"https?://\S+", " ", body)
    body = re.sub(r"^[>#*_`-]+(?:\s+|$)", "", body, flags=re.MULTILINE)
    body = re.sub(r"[*_`]", "", body)
    body = re.sub(r"\s+", " ", body).strip()
    return f"{title} {body}".strip() if title else body


def is_unusable_reader_response(markdown: str) -> bool:
    """Identify a reader response that is not usable article content."""

    lowered = markdown.casefold()
    return any(
        marker in lowered
        for marker in (
            "captcha",
            "access denied",
            "just a moment",
            "403 forbidden",
            "please verify you are human",
            "enable javascript",
            "too many requests",
            "rate limit exceeded",
            "empty content",
            "page not found",
            "page cannot be found",
            "requiring captcha",
            "\n429\n",
        )
    )


def is_blocked_response(markdown: str, title: str) -> bool:
    """Identify reader responses that are not an article body."""

    lowered = markdown.casefold()
    return (
        title.casefold() not in lowered
        or "captcha" in lowered
        or "access denied" in lowered
        or "just a moment" in lowered
        or "403 forbidden" in lowered
        or "please verify you are human" in lowered
        or "enable javascript" in lowered
        or "too many requests" in lowered
        or "rate limit exceeded" in lowered
        or "empty content" in lowered
        or "\n429\n" in lowered
        or "page not found" in lowered
        or "page cannot be found" in lowered
        or "requiring captcha" in lowered
    )


def is_protocol_date(value: str) -> bool:
    """Return whether an ISO date falls within the paper's collection window."""

    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return False
    try:
        current = date.fromisoformat(value)
    except ValueError:
        return False
    return date.fromisoformat(COLLECTION_PERIOD_START) <= current <= date.fromisoformat(
        COLLECTION_PERIOD_END
    )
