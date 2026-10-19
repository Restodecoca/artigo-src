"""Network helpers for retrieving article text through supported reader services."""

from __future__ import annotations

import urllib.request

JINA_READER_ENDPOINT = "https://r.jina.ai/"
READER_USER_AGENT = "academic-reproduction-probe/1.0"


def fetch_jina_reader_markdown(url: str, *, timeout: float = 30.0) -> str:
    """Fetch a URL through Jina Reader and decode its Markdown response."""

    request = urllib.request.Request(
        JINA_READER_ENDPOINT + url,
        headers={"User-Agent": READER_USER_AGENT},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="replace")
