#!/usr/bin/env python3
from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import re
from typing import Iterable, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_SCAN_PATHS: tuple[str, ...] = (
    "app.py",
    "cache.py",
    "chains.py",
    "lawglance_main.py",
    "prompts.py",
    "src/immcad_api",
    "docs",
)

ALLOWLISTED_RELATIVE_PATHS: frozenset[str] = frozenset(
    {
        "docs/IMMCAD_System_Overview.md",
        "docs/architecture/08-architecture-debt-and-improvement-plan.md",
        "docs/features/canada-readiness-execution-plan.md",
        "src/immcad_api/evaluation/jurisdiction.py",
        "src/immcad_api/evaluation/jurisdiction_suite.py",
    }
)

SCANNABLE_SUFFIXES: frozenset[str] = frozenset(
    {
        ".py",
        ".md",
        ".yaml",
        ".yml",
        ".toml",
        ".json",
        ".txt",
    }
)

DISALLOWED_TERMS: tuple[str, ...] = (
    "indian constitution",
    "bharatiya",
    "bnss",
    "bns",
    "bsa",
    "india",
    "indian penal code",
    "code of criminal procedure",
    "ipc",
    "crpc",
)

TERM_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = tuple(
    (term, re.compile(rf"\b{re.escape(term)}\b", re.IGNORECASE))
    for term in DISALLOWED_TERMS
)


@dataclass(frozen=True)
class Violation:
    file_path: Path
    line_number: int
    term: str
    line_text: str


def _to_relative_posix(path: Path, *, repo_root: Path) -> str:
    return path.resolve().relative_to(repo_root.resolve()).as_posix()


def _is_scannable_file(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in SCANNABLE_SUFFIXES


def iter_candidate_files(*, repo_root: Path, scan_paths: Sequence[str]) -> Iterable[Path]:
    seen: set[Path] = set()
    for raw_path in scan_paths:
        candidate = (repo_root / raw_path).resolve()
        if not candidate.exists():
            continue
        if candidate.is_file():
            if _is_scannable_file(candidate) and candidate not in seen:
                seen.add(candidate)
                yield candidate
            continue
        for nested_path in sorted(candidate.rglob("*")):
            if _is_scannable_file(nested_path) and nested_path not in seen:
                seen.add(nested_path)
                yield nested_path


def scan_file(file_path: Path) -> list[Violation]:
    try:
        contents = file_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return []

    violations: list[Violation] = []
    for line_number, line in enumerate(contents.splitlines(), start=1):
        normalized_line = line.strip()
        for term, pattern in TERM_PATTERNS:
            if pattern.search(normalized_line):
                violations.append(
                    Violation(
                        file_path=file_path,
                        line_number=line_number,
                        term=term,
                        line_text=normalized_line,
                    )
                )
    return violations


def scan_repository(
    *,
    repo_root: Path,
    scan_paths: Sequence[str],
    allowlist: frozenset[str] = ALLOWLISTED_RELATIVE_PATHS,
) -> tuple[list[Violation], int]:
    violations: list[Violation] = []
    scanned_files = 0
    for file_path in iter_candidate_files(repo_root=repo_root, scan_paths=scan_paths):
        relative_path = _to_relative_posix(file_path, repo_root=repo_root)
        if relative_path in allowlist:
            continue
        scanned_files += 1
        violations.extend(scan_file(file_path))
    return violations, scanned_files


def format_violation(violation: Violation, *, repo_root: Path) -> str:
    relative_path = _to_relative_posix(violation.file_path, repo_root=repo_root)
    return (
        f"{relative_path}:{violation.line_number}: disallowed term '{violation.term}' | "
        f"{violation.line_text}"
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Scan source/docs files for disallowed India-domain legal terms. "
            "Use allowlist entries only for approved legacy archived files."
        )
    )
    parser.add_argument(
        "--repo-root",
        default=str(REPO_ROOT),
        help="Repository root used for relative path resolution.",
    )
    parser.add_argument(
        "--path",
        action="append",
        default=[],
        help=(
            "Path to scan (relative to repo root). Can be specified multiple times. "
            f"Defaults to: {', '.join(DEFAULT_SCAN_PATHS)}"
        ),
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    repo_root = Path(args.repo_root).resolve()
    scan_paths = tuple(args.path) if args.path else DEFAULT_SCAN_PATHS
    violations, scanned_files = scan_repository(
        repo_root=repo_root,
        scan_paths=scan_paths,
    )

    if violations:
        print(f"[FAIL] Domain leak scan found {len(violations)} violation(s).")
        for violation in violations:
            print(format_violation(violation, repo_root=repo_root))
        return 1

    print(f"[OK] Domain leak scan passed ({scanned_files} files checked).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
