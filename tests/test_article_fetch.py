from unittest.mock import patch

from healthcare_ner_replication.article_fetch import (
    JINA_READER_ENDPOINT,
    READER_USER_AGENT,
    fetch_jina_reader_markdown,
)


class _Response:
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def read(self):
        return b"reader output"


def test_fetch_jina_reader_markdown_uses_endpoint_header_and_timeout():
    with patch("healthcare_ner_replication.article_fetch.urllib.request.urlopen") as urlopen:
        urlopen.return_value = _Response()

        result = fetch_jina_reader_markdown("https://example.test/article", timeout=12)

    request = urlopen.call_args.args[0]
    assert request.full_url == JINA_READER_ENDPOINT + "https://example.test/article"
    assert request.get_header("User-agent") == READER_USER_AGENT
    assert urlopen.call_args.kwargs == {"timeout": 12}
    assert result == "reader output"
