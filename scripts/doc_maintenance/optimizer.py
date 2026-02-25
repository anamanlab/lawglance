from __future__ import annotations

import re
from dataclasses import dataclass

TOC_HEADER = "## Table of Contents"
HEADING_PATTERN = re.compile(r"^(#{2,6})\s+(.*?)\s*$", re.MULTILINE)
H1_PATTERN = re.compile(r"^#\s+.*?$", re.MULTILINE)
TOC_SECTION_PATTERN = re.compile(
    r"^## Table of Contents\s*\n(?:\n)?(?P<body>(?:[-*]\s+\[[^\]]+\]\(#[^)]+\)\s*\n|(?:\s{2,}[-*].*\n))*)",
    re.MULTILINE,
)
TOC_GENERATION_STRIP_PATTERN = re.compile(
    r"^## Table of Contents\s*$\n?.*?(?=^#{2,6}\s+|\Z)",
    re.MULTILINE | re.DOTALL,
)


@dataclass
class TocResult:
    updated_content: str
    changed: bool


def _slugify_heading(title: str) -> str:
    normalized = re.sub(r"[^\w\s-]", "", title.strip().lower())
    normalized = re.sub(r"\s+", "-", normalized).strip("-")
    return normalized


def _dedupe_preserve_order(items: list[str]) -> list[str]:
    deduped: list[str] = []
    seen: set[str] = set()
    for item in items:
        if item in seen:
            continue
        deduped.append(item)
        seen.add(item)
    return deduped


def generate_toc(content: str) -> str:
    headings = HEADING_PATTERN.findall(content)
    if not headings:
        return ""

    toc_lines: list[str] = [TOC_HEADER, ""]
    for level_marks, heading_title in headings:
        nesting = len(level_marks) - 2
        indent = "  " * max(nesting, 0)
        anchor = _slugify_heading(heading_title)
        toc_lines.append(f"{indent}- [{heading_title}](#{anchor})")

    deduped_lines = toc_lines[:2] + _dedupe_preserve_order(toc_lines[2:])
    return "\n".join(deduped_lines).rstrip() + "\n"


def _replace_existing_toc(content: str, toc: str) -> str:
    match = TOC_SECTION_PATTERN.search(content)
    if not match:
        return content
    start, end = match.span()
    # Keep one blank line between TOC block and the next section for idempotence.
    replacement = toc.rstrip("\n") + "\n\n"
    tail = content[end:].lstrip("\n")
    return content[:start] + replacement + tail


def _strip_existing_toc_for_generation(content: str) -> str:
    return TOC_GENERATION_STRIP_PATTERN.sub("", content)


def inject_toc(content: str, min_headings: int = 4) -> TocResult:
    toc_source = _strip_existing_toc_for_generation(content)
    headings = HEADING_PATTERN.findall(toc_source)
    if len(headings) < min_headings:
        return TocResult(updated_content=content, changed=False)

    toc = generate_toc(toc_source)
    if not toc:
        return TocResult(updated_content=content, changed=False)

    if TOC_SECTION_PATTERN.search(content) is not None:
        updated = _replace_existing_toc(content, toc)
        return TocResult(updated_content=updated, changed=(updated != content))

    h1_match = H1_PATTERN.search(content)
    if not h1_match:
        return TocResult(updated_content=content, changed=False)

    insertion_point = h1_match.end()
    updated = content[:insertion_point] + "\n\n" + toc + "\n" + content[insertion_point:].lstrip("\n")
    return TocResult(updated_content=updated, changed=True)
