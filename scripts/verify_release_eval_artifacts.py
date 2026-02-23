#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

DEFAULT_REQUIRED_ARTIFACTS: tuple[str, ...] = (
    "artifacts/evals/jurisdiction-eval-report.json",
    "artifacts/evals/jurisdiction-eval-report.md",
    "artifacts/evals/jurisdictional-suite-report.json",
    "artifacts/evals/jurisdictional-suite-report.md",
)


def validate_artifacts(artifacts: Sequence[Path]) -> list[str]:
    failures: list[str] = []
    for artifact in artifacts:
        artifact_path = artifact.as_posix()
        if not artifact.exists():
            failures.append(f"missing artifact: {artifact_path}")
            continue
        if not artifact.is_file():
            failures.append(f"artifact path is not a file: {artifact_path}")
            continue

        if artifact.stat().st_size == 0:
            failures.append(f"empty artifact: {artifact_path}")
            continue

        try:
            contents = artifact.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue

        if not contents.strip():
            failures.append(f"empty artifact: {artifact_path}")

    return failures


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Verify required release evaluation artifacts exist and are non-empty."
    )
    parser.add_argument(
        "--artifact",
        action="append",
        default=[],
        help=(
            "Artifact path to validate. Can be provided multiple times. "
            f"Defaults to: {', '.join(DEFAULT_REQUIRED_ARTIFACTS)}"
        ),
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    artifact_paths = (
        [Path(path) for path in args.artifact]
        if args.artifact
        else [Path(path) for path in DEFAULT_REQUIRED_ARTIFACTS]
    )
    failures = validate_artifacts(artifact_paths)

    if failures:
        print("[FAIL] Release artifact verification failed.")
        for failure in failures:
            print(failure)
        return 1

    print(
        f"[OK] Release artifact verification passed "
        f"({len(artifact_paths)} artifacts checked)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
