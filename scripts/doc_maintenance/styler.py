from __future__ import annotations

import re
from typing import Any

from audit import AuditIssue

HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.*?)\s*$")
CODE_FENCE_PATTERN = re.compile(r"^\s*```(.*)$")
MARKDOWN_LINK_PATTERN = re.compile(r"(?<!!)\[([^\]]+)\]\(([^)]+)\)")


def _iter_non_code_lines(content: str):
    in_code_block = False
    for line_no, line in enumerate(content.splitlines(), start=1):
        if CODE_FENCE_PATTERN.match(line):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            continue
        yield line_no, line


def _extract_heading_levels(content: str) -> list[int]:
    levels: list[int] = []
    in_code_block = False
    for line in content.splitlines():
        if CODE_FENCE_PATTERN.match(line):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            continue
        match = HEADING_PATTERN.match(line)
        if not match:
            continue
        levels.append(len(match.group(1)))
    return levels


def check_heading_hierarchy(content: str, config: dict[str, Any]) -> list[AuditIssue]:
    issues: list[AuditIssue] = []
    levels = _extract_heading_levels(content)
    if not levels:
        issues.append(
            AuditIssue(
                severity="high",
                category="style",
                message="Document has no headings.",
                hint="Add heading structure starting with an H1 title.",
            )
        )
        return issues

    style_rules = config.get("style_rules", {})
    if style_rules.get("require_h1", True) and levels[0] != 1:
        issues.append(
            AuditIssue(
                severity="high",
                category="style",
                message="Document does not start with an H1 heading.",
                hint="Add an H1 at the top of the document.",
            )
        )
    if style_rules.get("no_h1_skipping", True):
        for previous, current in zip(levels, levels[1:]):
            if current > previous + 1:
                issues.append(
                    AuditIssue(
                        severity="medium",
                        category="style",
                        message=f"Heading level jump detected: H{previous} -> H{current}.",
                        hint="Use intermediate heading levels to keep hierarchy readable.",
                    )
                )
    return issues


def check_code_blocks(content: str) -> list[AuditIssue]:
    missing_language_blocks = 0
    in_code_block = False
    for line in content.splitlines():
        match = CODE_FENCE_PATTERN.match(line)
        if not match:
            continue
        if not in_code_block:
            language = match.group(1).strip()
            if not language:
                missing_language_blocks += 1
            in_code_block = True
        else:
            in_code_block = False
    if missing_language_blocks == 0:
        return []
    return [
        AuditIssue(
            severity="low",
            category="style",
            message=f"Found {missing_language_blocks} fenced code blocks without language.",
            hint="Specify languages (for example ` ```bash ` or ` ```python `).",
        )
    ]


def check_descriptive_links(content: str) -> list[AuditIssue]:
    weak_labels = {"here", "click here", "this", "link", "read more", "more"}
    issues: list[AuditIssue] = []
    filtered_content = "\n".join(line for _, line in _iter_non_code_lines(content))
    for label, target in MARKDOWN_LINK_PATTERN.findall(filtered_content):
        if label.strip().lower() in weak_labels:
            issues.append(
                AuditIssue(
                    severity="low",
                    category="accessibility",
                    message=f"Non-descriptive link label '{label}' for target {target}.",
                    hint="Use descriptive labels that communicate destination/context.",
                )
            )
    return issues


def check_line_length(content: str, max_line_length: int) -> list[AuditIssue]:
    issues: list[AuditIssue] = []
    for line_no, line in _iter_non_code_lines(content):
        if len(line) > max_line_length:
            issues.append(
                AuditIssue(
                    severity="low",
                    category="style",
                    message=f"Line {line_no} exceeds {max_line_length} characters.",
                    hint="Wrap long lines to improve readability and review diffs.",
                )
            )
    return issues


def validate_style(content: str, config: dict[str, Any]) -> list[AuditIssue]:
    style_rules = config.get("style_rules", {})
    issues: list[AuditIssue] = []
    issues.extend(check_heading_hierarchy(content, config))
    if style_rules.get("require_code_lang", True):
        issues.extend(check_code_blocks(content))
    if style_rules.get("require_descriptive_links", True):
        issues.extend(check_descriptive_links(content))
    max_line_length_raw = style_rules.get("max_line_length", 160)
    max_line_length: int | None
    if max_line_length_raw is None:
        max_line_length = None
    elif isinstance(max_line_length_raw, int) and not isinstance(max_line_length_raw, bool):
        max_line_length = max_line_length_raw
    elif isinstance(max_line_length_raw, str):
        try:
            max_line_length = int(max_line_length_raw.strip())
        except ValueError:
            max_line_length = None
    else:
        max_line_length = None
    if max_line_length is not None:
        issues.extend(check_line_length(content, max_line_length))
    return issues
