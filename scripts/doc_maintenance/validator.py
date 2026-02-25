from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import httpx

from audit import AuditIssue

IMAGE_LINK_PATTERN = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
MARKDOWN_LINK_PATTERN = re.compile(r"(?<!!)\[([^\]]+)\]\(([^)]+)\)")
RAW_URL_PATTERN = re.compile(r"https?://[^\s<>)\]]*[^\s<>)\].,;:!?\"'`]")
HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.*?)\s*$")
CODE_FENCE_PATTERN = re.compile(r"^\s*```")


def slugify_heading(title: str) -> str:
    normalized = re.sub(r"[^\w\s-]", "", title.strip().lower())
    normalized = re.sub(r"\s+", "-", normalized).strip("-")
    return normalized


def extract_headings(content: str) -> list[str]:
    anchors: list[str] = []
    in_code = False
    for line in content.splitlines():
        if CODE_FENCE_PATTERN.match(line):
            in_code = not in_code
            continue
        if in_code:
            continue
        match = HEADING_PATTERN.match(line)
        if not match:
            continue
        heading_text = match.group(2).strip()
        if heading_text:
            anchors.append(slugify_heading(heading_text))
    return anchors


def extract_links(content: str) -> tuple[list[tuple[str, str]], list[str]]:
    markdown_links = MARKDOWN_LINK_PATTERN.findall(content)
    image_links = IMAGE_LINK_PATTERN.findall(content)
    raw_urls = RAW_URL_PATTERN.findall(content)

    external_urls: set[str] = set(raw_urls)
    for _, target in markdown_links + image_links:
        if target.startswith("http://") or target.startswith("https://"):
            external_urls.add(target)
    return markdown_links, sorted(external_urls)


def _validate_file_anchor(linked_file: Path, anchor: str) -> tuple[bool, str | None]:
    try:
        content = linked_file.read_text(encoding="utf-8")
    except Exception as exc:
        return False, str(exc)
    anchors = extract_headings(content)
    return slugify_heading(anchor) in anchors, None


def validate_relative_link(base_path: Path, rel_link: str, root_dir: Path) -> AuditIssue | None:
    if rel_link.startswith(("http://", "https://", "mailto:", "tel:")):
        return None

    if rel_link.startswith("#"):
        local_anchor = rel_link[1:]
        if not local_anchor:
            return None
        try:
            content = base_path.read_text(encoding="utf-8")
        except Exception as exc:
            return AuditIssue(
                severity="medium",
                category="link",
                message=f"File read error while validating local anchor {rel_link}: {exc}",
                hint="Ensure the file is readable before validating local anchors.",
            )
        local_anchors = extract_headings(content)
        if slugify_heading(local_anchor) not in local_anchors:
            return AuditIssue(
                severity="high",
                category="link",
                message=f"Broken local anchor: {rel_link}",
                hint="Update the anchor to match an existing section heading.",
            )
        return None

    clean_target, _, anchor = rel_link.partition("#")
    if not clean_target:
        return None

    target_path = (base_path.parent / clean_target).resolve()
    if not target_path.exists():
        return AuditIssue(
            severity="high",
            category="link",
            message=f"Broken relative link: {rel_link}",
            hint="Update link path or add the missing file.",
        )

    try:
        target_path.relative_to(root_dir.resolve())
    except ValueError:
        return AuditIssue(
            severity="medium",
            category="link",
            message=f"Link points outside repository scope: {rel_link}",
            hint="Prefer in-repo references for durability and reviewability.",
        )

    if anchor and target_path.is_file() and target_path.suffix.lower() in {".md", ".mdx"}:
        anchor_valid, anchor_error = _validate_file_anchor(target_path, anchor)
        if anchor_error is not None:
            return AuditIssue(
                severity="medium",
                category="link",
                message=f"File read error while validating heading anchor {rel_link}: {anchor_error}",
                hint="Ensure the target file is readable before validating heading anchors.",
            )
        if not anchor_valid:
            return AuditIssue(
                severity="high",
                category="link",
                message=f"Broken heading anchor in link: {rel_link}",
                hint="Ensure the target section heading exists.",
            )
    return None


def _url_allowed_for_validation(url: str, ignore_domains: list[str]) -> bool:
    domain_match = re.match(r"^https?://([^/:?#]+)", url)
    if not domain_match:
        return False
    domain = domain_match.group(1).lower()
    return not any(domain == ignored or domain.endswith(f".{ignored}") for ignored in ignore_domains)


def validate_external_links(urls: list[str], config: dict[str, Any]) -> list[AuditIssue]:
    validation_cfg = config.get("external_link_validation", {})
    timeout_seconds = float(validation_cfg.get("timeout_seconds", 6))
    retry_count = int(validation_cfg.get("retry_count", 2))
    ignore_domains = [d.lower() for d in validation_cfg.get("ignore_domains", [])]

    issues: list[AuditIssue] = []
    with httpx.Client(
        follow_redirects=True,
        timeout=timeout_seconds,
        headers={"User-Agent": "IMMCAD-DocsMaintenance/1.0"},
    ) as client:
        for url in urls:
            if not _url_allowed_for_validation(url, ignore_domains):
                continue
            last_error: str | None = None
            for _ in range(max(retry_count, 1)):
                try:
                    response = client.head(url)
                    status_code = response.status_code
                    if status_code in {405, 501}:
                        response = client.get(url)
                        status_code = response.status_code
                    if status_code < 400:
                        last_error = None
                        break
                    last_error = f"HTTP {status_code}"
                except Exception as exc:
                    last_error = str(exc)
            if last_error is not None:
                issues.append(
                    AuditIssue(
                        severity="medium",
                        category="external_link",
                        message=f"Unhealthy external link: {url} ({last_error})",
                        hint="Fix URL, remove stale references, or add domain to ignore list if expected.",
                    )
                )
    return issues


def check_images(content: str, base_path: Path) -> list[AuditIssue]:
    issues: list[AuditIssue] = []
    for alt, src in IMAGE_LINK_PATTERN.findall(content):
        if not alt.strip():
            issues.append(
                AuditIssue(
                    severity="medium",
                    category="accessibility",
                    message=f"Missing alt text for image: {src}",
                    hint="Add concise, descriptive alt text.",
                )
            )
        if src.startswith(("http://", "https://", "data:")):
            continue
        image_path = (base_path.parent / src).resolve()
        if not image_path.exists():
            issues.append(
                AuditIssue(
                    severity="high",
                    category="image",
                    message=f"Broken local image reference: {src}",
                    hint="Correct the path or add the missing image asset.",
                )
            )
    return issues
