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
    missing_mapped_primary: tuple[str, ...] = ()
    missing_mapped_deploy: tuple[str, ...] = ()
    mapped_mismatched: tuple[str, ...] = ()

    @property
    def is_synced(self) -> bool:
        return not (
            self.missing_in_deploy
            or self.extra_in_deploy
            or self.mismatched
            or self.missing_mapped_primary
            or self.missing_mapped_deploy
            or self.mapped_mismatched
        )


DEFAULT_MAPPED_FILE_PAIRS: tuple[tuple[str, str], ...] = (
    ("config/source_policy.yaml", "backend-vercel/config/source_policy.yaml"),
)


def _python_file_set(root: Path) -> set[str]:
    files: set[str] = set()
    for path in root.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        files.add(path.relative_to(root).as_posix())
    return files


def compare_source_trees(
    *,
    primary_root: Path,
    deploy_root: Path,
    mapped_file_pairs: tuple[tuple[Path, Path], ...] = (),
) -> SyncResult:
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

    missing_mapped_primary: list[str] = []
    missing_mapped_deploy: list[str] = []
    mapped_mismatched: list[str] = []
    for primary_path, deploy_path in mapped_file_pairs:
        primary_exists = primary_path.exists()
        deploy_exists = deploy_path.exists()
        if not primary_exists:
            missing_mapped_primary.append(primary_path.as_posix())
        if not deploy_exists:
            missing_mapped_deploy.append(deploy_path.as_posix())
        if primary_exists and deploy_exists:
            if primary_path.read_bytes() != deploy_path.read_bytes():
                mapped_mismatched.append(
                    f"{primary_path.as_posix()} <-> {deploy_path.as_posix()}"
                )

    return SyncResult(
        missing_in_deploy=missing_in_deploy,
        extra_in_deploy=extra_in_deploy,
        mismatched=tuple(mismatched),
        missing_mapped_primary=tuple(sorted(missing_mapped_primary)),
        missing_mapped_deploy=tuple(sorted(missing_mapped_deploy)),
        mapped_mismatched=tuple(sorted(mapped_mismatched)),
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Validate that deploy runtime Python sources stay synchronized with "
            "root src/immcad_api sources."
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
        help="Deploy source tree path (default: backend-vercel/src/immcad_api).",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    primary_root = Path(args.primary_root)
    deploy_root = Path(args.deploy_root)
    repo_root = Path(__file__).resolve().parents[1]

    if not primary_root.exists():
        raise FileNotFoundError(f"Primary source root not found: {primary_root}")
    if not deploy_root.exists():
        raise FileNotFoundError(f"Deploy source root not found: {deploy_root}")

    mapped_file_pairs = tuple(
        (repo_root / primary_rel_path, repo_root / deploy_rel_path)
        for primary_rel_path, deploy_rel_path in DEFAULT_MAPPED_FILE_PAIRS
    )

    result = compare_source_trees(
        primary_root=primary_root,
        deploy_root=deploy_root,
        mapped_file_pairs=mapped_file_pairs,
    )
    if result.is_synced:
        print(
            "Source sync check passed: "
            f"{primary_root} and {deploy_root} contain matching Python files "
            "and required mapped config files."
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
    if result.missing_mapped_primary:
        print("Missing mapped files in primary tree:")
        for path in result.missing_mapped_primary:
            print(f"  - {path}")
    if result.missing_mapped_deploy:
        print("Missing mapped files in deploy tree:")
        for path in result.missing_mapped_deploy:
            print(f"  - {path}")
    if result.mapped_mismatched:
        print("Mapped file content mismatch:")
        for pair in result.mapped_mismatched:
            print(f"  - {pair}")

    print(
        "Source sync check failed. "
        "Run: rsync -a --exclude '__pycache__/' --exclude '*.pyc' "
        "src/immcad_api/ backend-vercel/src/immcad_api/"
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
