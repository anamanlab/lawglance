from __future__ import annotations

import fnmatch
import glob
import logging
import pathlib
import re
import subprocess
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

WORD_PATTERN = re.compile(r"\w+")
TODO_PATTERN = re.compile(r"(TODO|FIXME)\s*:?\s*(.*)", re.IGNORECASE)
_FRONTMATTER_PATTERN = re.compile(r"\A---\s*\n.*?\n---\s*(?:\n|$)", re.DOTALL)
_CODE_BLOCK_PATTERN = re.compile(r"^(?:```|~~~).*?^(?:```|~~~)\s*$", re.MULTILINE | re.DOTALL)
_INLINE_CODE_PATTERN = re.compile(r"`[^`\n]+`")
_URL_PATTERN = re.compile(r"https?://[^\s<>)\]]+")
LOGGER = logging.getLogger(__name__)


@dataclass
class AuditIssue:
    severity: str
    category: str
    message: str
    hint: str | None = None


@dataclass
class FileAudit:
    path: str
    word_count: int
    last_commit_iso: str | None
    age_days: int | None
    issues: list[AuditIssue] = field(default_factory=list)
    todos: list[str] = field(default_factory=list)


def _relative_posix(path: Path, root_dir: Path) -> str:
    return path.resolve().relative_to(root_dir.resolve()).as_posix()


def _matches_any(path: str, patterns: list[str]) -> bool:
    pure_path = pathlib.PurePath(path)
    full_match = getattr(pure_path, "full_match", None)
    for pattern in patterns:
        if callable(full_match):
            if full_match(pattern):
                return True
            continue
        try:
            translated = glob.translate(pattern)
        except AttributeError:
            translated = _translate_glob_pattern_compat(pattern)
        if re.fullmatch(translated, path):
            return True
    return False


def _translate_glob_pattern_compat(pattern: str) -> str:
    """Separator-aware glob translation for Python versions without glob.translate."""
    i = 0
    parts: list[str] = []
    while i < len(pattern):
        char = pattern[i]
        if char == "*":
            if pattern[i : i + 3] == "**/":
                parts.append(r"(?:[^/]+/)*")
                i += 3
                continue
            if pattern[i : i + 2] == "**":
                parts.append(r".*")
                i += 2
                continue
            parts.append(r"[^/]*")
            i += 1
            continue
        if char == "?":
            parts.append(r"[^/]")
            i += 1
            continue
        if char == "[":
            end = pattern.find("]", i + 1)
            if end != -1:
                parts.append(fnmatch.translate(pattern[i : end + 1])[4:-3])
                i = end + 1
                continue
        parts.append(re.escape(char))
        i += 1
    return r"\A" + "".join(parts) + r"\Z"


def discover_markdown_files(root_dir: Path, config: dict[str, Any]) -> list[Path]:
    include_paths = config.get("include_paths", ["docs"])
    exclude_globs = config.get("exclude_globs", [])
    discovered: set[Path] = set()

    for include in include_paths:
        include_path = (root_dir / include).resolve()
        if not include_path.exists():
            continue
        if include_path.is_file() and include_path.suffix.lower() in {".md", ".mdx"}:
            rel_posix = _relative_posix(include_path, root_dir)
            if not _matches_any(rel_posix, exclude_globs):
                discovered.add(include_path)
            continue
        if not include_path.is_dir():
            continue

        for file_path in include_path.rglob("*"):
            if not file_path.is_file() or file_path.suffix.lower() not in {".md", ".mdx"}:
                continue
            rel_posix = _relative_posix(file_path, root_dir)
            if _matches_any(rel_posix, exclude_globs):
                continue
            discovered.add(file_path.resolve())

    return sorted(discovered, key=lambda p: _relative_posix(p, root_dir))


def get_git_last_commit_date(file_path: Path) -> datetime | None:
    try:
        result = subprocess.run(
            ["git", "log", "-1", "--format=%ct", "--", str(file_path)],
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
            cwd=str(file_path.parent),
        )
    except Exception:
        return None
    if result.returncode != 0:
        return None
    raw = result.stdout.strip()
    if not raw:
        return None
    try:
        return datetime.fromtimestamp(int(raw), tz=UTC)
    except ValueError:
        return None


def _is_freshness_exempt(relative_path: str, config: dict[str, Any]) -> bool:
    thresholds = config.get("quality_thresholds", {})
    stale_exceptions = thresholds.get("stale_exceptions", [])
    return _matches_any(relative_path, stale_exceptions)


def _parse_threshold_int(thresholds: dict[str, Any], key: str, default: int) -> int:
    raw_value = thresholds.get(key, default)
    try:
        if isinstance(raw_value, bool):
            raise TypeError("boolean is not a valid integer threshold")
        return int(raw_value)
    except (TypeError, ValueError):
        LOGGER.warning(
            "Invalid quality threshold for %s=%r; using default=%s",
            key,
            raw_value,
            default,
        )
        return default


def analyze_markdown_file(file_path: Path, root_dir: Path, config: dict[str, Any]) -> FileAudit:
    relative_path = _relative_posix(file_path, root_dir)
    try:
        content = file_path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, PermissionError, OSError) as exc:
        return FileAudit(
            path=relative_path,
            word_count=0,
            last_commit_iso=None,
            age_days=None,
            issues=[
                AuditIssue(
                    severity="high",
                    category="read",
                    message=f"Failed to read markdown file: {exc}",
                    hint="Ensure file encoding and permissions are valid for UTF-8 reads.",
                )
            ],
            todos=[],
        )
    prose = _FRONTMATTER_PATTERN.sub("", content)
    prose = _CODE_BLOCK_PATTERN.sub("", prose)
    prose = _INLINE_CODE_PATTERN.sub("", prose)
    prose = _URL_PATTERN.sub("", prose)
    word_count = len(WORD_PATTERN.findall(prose))
    last_commit = get_git_last_commit_date(file_path)
    age_days: int | None = None
    issues: list[AuditIssue] = []

    thresholds = config.get("quality_thresholds", {})
    min_word_count = _parse_threshold_int(thresholds, "min_word_count", 50)
    max_freshness_days = _parse_threshold_int(thresholds, "max_freshness_days", 90)

    if word_count < min_word_count:
        issues.append(
            AuditIssue(
                severity="low",
                category="content",
                message=f"Low word count: {word_count} (< {min_word_count})",
                hint="Expand context, examples, or procedural steps.",
            )
        )

    if last_commit is not None:
        age_days = max((datetime.now(tz=UTC) - last_commit).days, 0)
        if age_days > max_freshness_days and not _is_freshness_exempt(relative_path, config):
            issues.append(
                AuditIssue(
                    severity="medium",
                    category="freshness",
                    message=f"Content appears stale: {age_days} days since last git update.",
                    hint="Review content against the latest product/runtime behavior.",
                )
            )

    todos = [match[1].strip() for match in TODO_PATTERN.findall(content) if match[1].strip()]
    if todos:
        issues.append(
            AuditIssue(
                severity="medium",
                category="todo",
                message=f"Found {len(todos)} TODO/FIXME markers.",
                hint="Resolve or convert TODO markers into tracked backlog issues.",
            )
        )

    return FileAudit(
        path=relative_path,
        word_count=word_count,
        last_commit_iso=last_commit.isoformat() if last_commit else None,
        age_days=age_days,
        issues=issues,
        todos=todos,
    )
