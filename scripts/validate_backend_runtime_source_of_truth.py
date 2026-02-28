#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import subprocess
from dataclasses import dataclass
from typing import Iterable


DEFAULT_PROTECTED_ROOT = "backend-vercel/src/immcad_api"
DEFAULT_ALLOWED_PATHS: tuple[str, ...] = (
    "backend-vercel/src/immcad_api/README.md",
)


@dataclass(frozen=True)
class ValidationResult:
    changed_paths: tuple[str, ...]
    blocked_paths: tuple[str, ...]
    source_description: str

    @property
    def is_valid(self) -> bool:
        return len(self.blocked_paths) == 0


def normalize_repo_path(path: str) -> str:
    normalized = path.replace("\\", "/").strip()
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized.rstrip("/")


def find_blocked_paths(
    *,
    changed_paths: Iterable[str],
    protected_root: str,
    allow_paths: Iterable[str] = (),
) -> tuple[str, ...]:
    normalized_protected_root = normalize_repo_path(protected_root)
    protected_prefix = f"{normalized_protected_root}/"
    normalized_allow_paths = {
        normalize_repo_path(path) for path in allow_paths if normalize_repo_path(path)
    }
    blocked: list[str] = []
    for path in changed_paths:
        normalized_path = normalize_repo_path(path)
        if not normalized_path:
            continue
        if not normalized_path.startswith(protected_prefix):
            continue
        if normalized_path in normalized_allow_paths:
            continue
        blocked.append(normalized_path)
    return tuple(sorted(set(blocked)))


def _run_git(args: list[str]) -> str:
    process = subprocess.run(
        ["git", *args],
        check=False,
        capture_output=True,
        text=True,
    )
    if process.returncode != 0:
        stderr = process.stderr.strip()
        stdout = process.stdout.strip()
        details = stderr or stdout or "git command failed"
        raise RuntimeError(f"git {' '.join(args)}: {details}")
    return process.stdout


def _paths_from_command(args: list[str]) -> tuple[str, ...]:
    output = _run_git(args)
    paths = [normalize_repo_path(line) for line in output.splitlines()]
    return tuple(path for path in paths if path)


def _read_changed_paths(base_ref: str | None, head_ref: str | None) -> tuple[tuple[str, ...], str]:
    normalized_base = (base_ref or "").strip()
    normalized_head = (head_ref or "").strip()
    if normalized_base and normalized_head:
        try:
            paths = _paths_from_command(
                [
                    "diff",
                    "--name-only",
                    "--diff-filter=ACDMRTUXB",
                    f"{normalized_base}...{normalized_head}",
                ]
            )
            return paths, f"git diff {normalized_base}...{normalized_head}"
        except RuntimeError as error:
            raise RuntimeError(
                "explicit diff refs could not be resolved: "
                f"{normalized_base}...{normalized_head}"
            ) from error

    staged = set(_paths_from_command(["diff", "--name-only", "--cached"]))
    unstaged = set(_paths_from_command(["diff", "--name-only"]))
    worktree_paths = tuple(sorted(staged | unstaged))
    if worktree_paths:
        return worktree_paths, "git diff (staged + unstaged)"

    try:
        _run_git(["rev-parse", "--verify", "HEAD~1"])
        paths = _paths_from_command(
            ["diff", "--name-only", "--diff-filter=ACDMRTUXB", "HEAD~1...HEAD"]
        )
        return paths, "git diff HEAD~1...HEAD"
    except RuntimeError:
        return worktree_paths, "git diff (staged + unstaged)"


def validate_runtime_source_of_truth(
    *,
    base_ref: str | None = None,
    head_ref: str | None = None,
    protected_root: str = DEFAULT_PROTECTED_ROOT,
    allow_paths: Iterable[str] = DEFAULT_ALLOWED_PATHS,
) -> ValidationResult:
    changed_paths, source_description = _read_changed_paths(base_ref, head_ref)
    blocked_paths = find_blocked_paths(
        changed_paths=changed_paths,
        protected_root=protected_root,
        allow_paths=allow_paths,
    )
    return ValidationResult(
        changed_paths=changed_paths,
        blocked_paths=blocked_paths,
        source_description=source_description,
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Fail when runtime code is edited under backend-vercel/src/immcad_api. "
            "Use src/immcad_api as the canonical backend runtime source."
        )
    )
    parser.add_argument(
        "--base-ref",
        default=None,
        help=(
            "Diff base ref. Defaults to GIT_DIFF_BASE when set, otherwise "
            "falls back to HEAD~1...HEAD or working-tree diff."
        ),
    )
    parser.add_argument(
        "--head-ref",
        default=None,
        help="Diff head ref. Defaults to GIT_DIFF_HEAD when set.",
    )
    parser.add_argument(
        "--protected-root",
        default=DEFAULT_PROTECTED_ROOT,
        help=(
            "Protected runtime mirror root "
            f"(default: {DEFAULT_PROTECTED_ROOT})."
        ),
    )
    parser.add_argument(
        "--allow-path",
        action="append",
        default=[],
        help=(
            "Allowlist path under protected root. May be repeated. "
            f"Default allowlist: {', '.join(DEFAULT_ALLOWED_PATHS)}"
        ),
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    base_ref = args.base_ref or os.getenv("GIT_DIFF_BASE")
    head_ref = args.head_ref or os.getenv("GIT_DIFF_HEAD")
    allow_paths = tuple(DEFAULT_ALLOWED_PATHS) + tuple(args.allow_path)

    try:
        result = validate_runtime_source_of_truth(
            base_ref=base_ref,
            head_ref=head_ref,
            protected_root=args.protected_root,
            allow_paths=allow_paths,
        )
    except RuntimeError as error:
        print("Backend runtime source-of-truth check failed.")
        print(f"Unable to determine changed paths: {error}")
        return 1
    if result.is_valid:
        print(
            "Backend runtime source-of-truth check passed. "
            f"No blocked changes under {normalize_repo_path(args.protected_root)} "
            f"({result.source_description})."
        )
        return 0

    print(
        "Backend runtime source-of-truth check failed. "
        "Do not edit runtime code under backend-vercel/src/immcad_api."
    )
    print(f"Changed paths source: {result.source_description}")
    print("Blocked paths:")
    for path in result.blocked_paths:
        print(f"  - {path}")
    print("Use src/immcad_api as the canonical runtime source.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
