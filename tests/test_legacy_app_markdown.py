from __future__ import annotations

from app import build_assistant_markdown


def test_build_assistant_markdown_escapes_citation_text_and_rejects_unsafe_urls() -> None:
    markdown = build_assistant_markdown(
        answer="Answer",
        citations=(
            {
                "title": "Unsafe [title]*",
                "url": "javascript:alert(1)",
                "pin": "s. [11]_`x`",
            },
        ),
        disclaimer=None,
        trace_id=None,
    )

    assert "javascript:alert(1)" not in markdown
    assert "- Unsafe \\[title\\]\\*" in markdown
    assert "s\\. \\[11\\]\\_\\`x\\`" in markdown


def test_build_assistant_markdown_preserves_http_https_links_and_encodes_spaces() -> None:
    markdown = build_assistant_markdown(
        answer="Answer",
        citations=(
            {
                "title": "Source",
                "url": "https://example.com/path with space?q=a b",
                "pin": "",
            },
        ),
        disclaimer=None,
        trace_id=None,
    )

    assert "(https://example.com/path%20with%20space?q=a%20b)" in markdown
