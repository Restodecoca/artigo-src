import pytest

from healthcare_ner_replication.local_corpus import (
    LocalArticle,
    clean_article,
    clean_reader_article,
    first_tokens,
    is_blocked_response,
    is_protocol_date,
    is_unusable_reader_response,
    load_pipe_articles,
    reader_title,
    select_keyword_articles,
)


def test_load_pipe_articles_preserves_multiline_text_and_ids(tmp_path):
    path = tmp_path / "articles.csv"
    path.write_bytes(b'1|"First line.\nSecond line with a | pipe."\n2|"Another article."\n')

    articles = load_pipe_articles(path)

    assert [(article.document_id, article.text) for article in articles] == [
        ("1", "First line.\nSecond line with a | pipe."),
        ("2", "Another article."),
    ]


def test_local_article_rejects_non_numeric_document_id():
    with pytest.raises(ValueError):
        LocalArticle("not-numeric", "Article text")


def test_load_pipe_articles_rejects_malformed_rows(tmp_path):
    path = tmp_path / "articles.csv"
    path.write_text('1|"valid"\nmalformed\n', encoding="utf-8")

    with pytest.raises(ValueError, match="row 2"):
        load_pipe_articles(path)


def test_load_pipe_articles_rejects_unclosed_csv_quotes(tmp_path):
    path = tmp_path / "articles.csv"
    path.write_bytes(b'1|"unclosed\n2|"valid"\n')

    with pytest.raises(ValueError, match="CSV syntax"):
        load_pipe_articles(path)


def test_select_keyword_articles_is_case_insensitive_and_ordered():
    articles = [
        LocalArticle("1", "No relevant term."),
        LocalArticle("2", "A Hospital report."),
        LocalArticle("3", "A PATIENT record."),
        LocalArticle("4", "Another hospital report."),
    ]

    selected = select_keyword_articles(
        articles,
        keywords=("healthcare", "hospital", "patient"),
        limit=2,
    )

    assert [article.document_id for article in selected] == ["2", "3"]


def test_first_tokens_limits_text_without_leaking_later_content():
    assert first_tokens("one two three four", limit=3) == "one two three"
    assert first_tokens("one two", limit=3) == "one two"


def test_clean_article_removes_reader_navigation_after_article():
    markdown = (
        "# Title\nPublished\nBody with [a link](https://example.test).\n## Most Read\nSidebar"
    )

    assert clean_article(markdown, "Title") == "Published Body with a link."


def test_clean_article_keeps_markdown_line_content():
    markdown = "# Title\n- A valid bullet.\n# A subheading\nBody.\n## Most Read\nSidebar"

    assert clean_article(markdown, "Title") == "A valid bullet. A subheading Body."


def test_clean_article_preserves_hashes_without_markdown_spacing():
    markdown = "# Title\n#CVE-2023-1234 and -D are content.\n## Most Read\nSidebar"

    assert clean_article(markdown, "Title") == "#CVE-2023-1234 and -D are content."


def test_clean_article_removes_empty_markdown_links():
    markdown = "# Title\nBody [](https://example.test/image.webp) text.\n## Most Read\nSidebar"

    assert clean_article(markdown, "Title") == "Body text."


def test_clean_article_removes_reader_boilerplate():
    markdown = (
        "# Title\nBody.\n## Share This Story\nSocial links\n"
        "Looking for a reprint?\nKEYWORDS: healthcare"
    )

    assert clean_article(markdown, "Title") == "Body."


def test_clean_reader_article_extracts_jina_metadata_wrapped_body():
    markdown = (
        "Title: Article title\nURL Source: https://example.test\n"
        "Markdown Content:\nNavigation links Article title\n"
        "Body with [a link](https://example.test/link).\n## Related\nSidebar"
    )

    assert reader_title(markdown) == "Article title"
    assert clean_reader_article(markdown) == "Article title Body with a link."


def test_clean_reader_article_keeps_only_firecrawl_title_and_body():
    markdown = (
        "![hero](https://example.test/image.png)\n\n"
        "# Article title\n\nBody paragraph.\n\n"
        "- [News Briefs](https://example.test/related)\n\n"
        "## Author\nAuthor biography"
    )

    assert clean_reader_article(markdown) == "Article title Body paragraph."


def test_unusable_reader_response_does_not_require_a_known_title():
    assert is_unusable_reader_response("Title: Unknown\nMarkdown Content:\nCAPTCHA")
    assert not is_unusable_reader_response("Title: Article\nMarkdown Content:\nBody.")


def test_block_page_is_rejected_even_when_it_has_many_words():
    markdown = "# Title\nThis page may be requiring CAPTCHA. " + ("noise " * 50)

    assert is_blocked_response(markdown, "Title")


def test_access_denied_page_is_rejected():
    markdown = "# Title\nAccess Denied\nJust a moment..."

    assert is_blocked_response(markdown, "Title")


def test_common_http_block_page_is_rejected():
    markdown = "# Title\n403 Forbidden\nPlease verify you are human. Empty content."

    assert is_blocked_response(markdown, "Title")


def test_protocol_date_requires_a_real_date_in_the_protocol_window():
    assert is_protocol_date("2023-10-30")
    assert not is_protocol_date("2023-10-31")
    assert not is_protocol_date("2023-02-31")
    assert not is_protocol_date("2023-10-30garbage")
    assert not is_protocol_date("2023-01-01T99:99:99")
    assert not is_protocol_date("20230101")
    assert not is_protocol_date("2023-W01-1")
