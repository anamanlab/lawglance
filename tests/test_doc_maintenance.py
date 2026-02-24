from __future__ import annotations

import sys
from pathlib import Path


DOC_MAINTENANCE_DIR = Path(__file__).resolve().parents[1] / "scripts" / "doc_maintenance"
if str(DOC_MAINTENANCE_DIR) not in sys.path:
    sys.path.insert(0, str(DOC_MAINTENANCE_DIR))

from audit import analyze_markdown_file, discover_markdown_files  # noqa: E402
from optimizer import inject_toc  # noqa: E402
from styler import check_descriptive_links, validate_style  # noqa: E402
from validator import validate_relative_link  # noqa: E402


def test_discover_markdown_files_respects_include_and_exclude(tmp_path: Path) -> None:
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "good.md").write_text("# Title\n", encoding="utf-8")
    (docs_dir / "skip.mdx").write_text("# Skip\n", encoding="utf-8")
    hidden_dir = docs_dir / "generated"
    hidden_dir.mkdir()
    (hidden_dir / "ignore.md").write_text("# Ignore\n", encoding="utf-8")

    config = {
        "include_paths": ["docs"],
        "exclude_globs": ["docs/generated/**", "docs/skip.mdx"],
    }
    files = discover_markdown_files(tmp_path, config)
    relative = [path.relative_to(tmp_path).as_posix() for path in files]
    assert relative == ["docs/good.md"]


def test_discover_markdown_files_glob_semantics_keep_nested_file_when_excluding_docs_star_md(
    tmp_path: Path,
) -> None:
    docs_dir = tmp_path / "docs"
    nested_dir = docs_dir / "nested"
    nested_dir.mkdir(parents=True)
    (docs_dir / "top.md").write_text("# Top\n", encoding="utf-8")
    (nested_dir / "child.md").write_text("# Child\n", encoding="utf-8")

    config = {
        "include_paths": ["docs"],
        "exclude_globs": ["docs/*.md"],
    }
    files = discover_markdown_files(tmp_path, config)
    relative = [path.relative_to(tmp_path).as_posix() for path in files]

    assert relative == ["docs/nested/child.md"]


def test_analyze_markdown_file_finds_todo_and_low_word_count(tmp_path: Path) -> None:
    file_path = tmp_path / "docs" / "sample.md"
    file_path.parent.mkdir()
    file_path.write_text("# Title\n\nTODO: add details\n", encoding="utf-8")

    config = {"quality_thresholds": {"min_word_count": 20, "max_freshness_days": 3650}}
    audit = analyze_markdown_file(file_path, tmp_path, config)

    categories = {issue.category for issue in audit.issues}
    assert "content" in categories
    assert "todo" in categories
    assert audit.todos == ["add details"]


def test_inject_toc_replaces_existing_table_of_contents() -> None:
    content = (
        "# Doc\n\n"
        "## Table of Contents\n\n"
        "- [Old](#old)\n"
        "- [Old](#old)\n\n"
        "## Alpha\n\n"
        "## Beta\n"
    )
    result = inject_toc(content, min_headings=2)

    assert result.changed is True
    assert result.updated_content.count("## Table of Contents") == 1
    assert result.updated_content.count("- [Alpha](#alpha)") == 1


def test_validate_relative_link_reports_missing_anchor(tmp_path: Path) -> None:
    file_path = tmp_path / "docs" / "index.md"
    file_path.parent.mkdir()
    file_path.write_text("# Title\n\n## Intro\n", encoding="utf-8")

    issue = validate_relative_link(file_path, "#missing-anchor", tmp_path)
    assert issue is not None
    assert issue.category == "link"


def test_analyze_markdown_file_word_count_ignores_frontmatter_code_inline_code_and_urls(
    tmp_path: Path,
) -> None:
    file_path = tmp_path / "docs" / "sample.md"
    file_path.parent.mkdir()
    file_path.write_text(
        "---\n"
        "title: Example Doc\n"
        "---\n\n"
        "# Title\n\n"
        "Use `make test` at https://example.com/docs for validation.\n\n"
        "```bash\n"
        "curl https://example.com/api\n"
        "echo TODO ignored in code block\n"
        "```\n\n"
        "Real prose words stay countable.\n",
        encoding="utf-8",
    )

    config = {"quality_thresholds": {"min_word_count": 1, "max_freshness_days": 3650}}
    audit = analyze_markdown_file(file_path, tmp_path, config)

    assert audit.word_count == 10


def test_inject_toc_does_not_include_table_of_contents_heading_in_generated_toc() -> None:
    content = (
        "# Doc\n\n"
        "## Table of Contents\n\n"
        "- [Old](#old)\n\n"
        "## Alpha\n\n"
        "### Beta\n"
    )

    result = inject_toc(content, min_headings=2)

    assert result.changed is True
    assert "- [Table of Contents](#table-of-contents)" not in result.updated_content
    assert "## Table of Contents\n\n- [Alpha](#alpha)\n  - [Beta](#beta)\n" in result.updated_content


def test_check_descriptive_links_ignores_links_inside_fenced_code_blocks() -> None:
    content = (
        "```md\n"
        "[click here](https://example.com)\n"
        "```\n\n"
        "See [Documentation](https://example.com/docs).\n"
    )

    issues = check_descriptive_links(content)

    assert issues == []


def test_validate_style_skips_line_length_for_code_blocks_and_invalid_config() -> None:
    content = (
        "# Doc\n\n"
        "```python\n"
        "x = 'this line is intentionally very long and should be ignored by line-length checks'\n"
        "```\n"
    )

    issues_none = validate_style(content, {"style_rules": {"max_line_length": None}})
    issues_invalid = validate_style(content, {"style_rules": {"max_line_length": "abc"}})
    issues_bool = validate_style(content, {"style_rules": {"max_line_length": True}})
    issues_short = validate_style(content, {"style_rules": {"max_line_length": 20}})

    assert all(issue.category != "style" or "Line " not in issue.message for issue in issues_none)
    assert all(issue.category != "style" or "Line " not in issue.message for issue in issues_invalid)
    assert all(issue.category != "style" or "Line " not in issue.message for issue in issues_bool)
    assert all(issue.category != "style" or "Line " not in issue.message for issue in issues_short)


def test_validate_relative_link_returns_issue_when_base_file_unreadable(tmp_path: Path) -> None:
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()

    issue = validate_relative_link(docs_dir, "#intro", tmp_path)

    assert issue is not None
    assert issue.category == "link"
    assert "File read error" in issue.message
