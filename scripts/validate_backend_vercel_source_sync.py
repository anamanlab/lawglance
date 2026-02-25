#!/usr/bin/env python3
from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SyncResult:
    missing_in_deploy: tuple[str, ...]
    extra_in_deploy: tuple[str, ...]
    mismatched: tuple[str, ...]

    @property
    def is_synced(self) -> bool:
        return not (self.missing_in_deploy or self.extra_in_deploy or self.mismatched)


def _python_file_set(root: Path) -> set[str]:
    files: set[str] = set()
    for path in root.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        files.add(path.relative_to(root).as_posix())
    return files


def compare_source_trees(*, primary_root: Path, deploy_root: Path) -> SyncResult:
    primary_files = _python_file_set(primary_root)
    deploy_files = _python_file_set(deploy_root)

    missing_in_deploy = tuple(sorted(primary_files - deploy_files))
    extra_in_deploy = tuple(sorted(deploy_files - primary_files))

    mismatched: list[str] = []
    for rel_path in sorted(primary_files & deploy_files):
        primary_path = primary_root / rel_path
        deploy_path = deploy_root / rel_path
        if primary_path.read_bytes() != deploy_path.read_bytes():
            mismatched.append(rel_path)

    return SyncResult(
        missing_in_deploy=missing_in_deploy,
        extra_in_deploy=extra_in_deploy,
        mismatched=tuple(mismatched),
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Validate that backend-vercel runtime Python sources stay synchronized "
            "with root src/immcad_api sources."
        )
    )
    parser.add_argument(
        "--primary-root",
        default="src/immcad_api",
        help="Primary source tree path (default: src/immcad_api).",
    )
    parser.add_argument(
        "--deploy-root",
        default="backend-vercel/src/immcad_api",
        help="Backend Vercel source tree path (default: backend-vercel/src/immcad_api).",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    primary_root = Path(args.primary_root)
    deploy_root = Path(args.deploy_root)

    if not primary_root.exists():
        raise FileNotFoundError(f"Primary source root not found: {primary_root}")
    if not deploy_root.exists():
        raise FileNotFoundError(f"Deploy source root not found: {deploy_root}")

    result = compare_source_trees(primary_root=primary_root, deploy_root=deploy_root)
    if result.is_synced:
        print(
            "Source sync check passed: "
            f"{primary_root} and {deploy_root} contain matching Python files."
        )
        return 0

    if result.missing_in_deploy:
        print("Missing in deploy tree:")
        for path in result.missing_in_deploy:
            print(f"  - {path}")
    if result.extra_in_deploy:
        print("Extra in deploy tree:")
        for path in result.extra_in_deploy:
            print(f"  - {path}")
    if result.mismatched:
        print("Content mismatch:")
        for path in result.mismatched:
            print(f"  - {path}")

    print(
        "Source sync check failed. "
        "Run: rsync -a --exclude '__pycache__/' --exclude '*.pyc' "
        "src/immcad_api/ backend-vercel/src/immcad_api/"
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
