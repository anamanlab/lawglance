#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable

REQUIRED_RELEASE_ARTIFACTS = (
    Path("artifacts/evals/jurisdiction-eval-report.json"),
    Path("artifacts/evals/jurisdiction-eval-report.md"),
    Path("artifacts/evals/jurisdictional-suite-report.json"),
    Path("artifacts/evals/jurisdictional-suite-report.md"),
    Path("artifacts/evals/frontend-test-summary.xml"),
)


def validate_release_artifacts(
    *,
    base_dir: Path = Path("."),
    required_artifacts: Iterable[Path] = REQUIRED_RELEASE_ARTIFACTS,
) -> None:
    missing: list[Path] = []
    unreadable: list[Path] = []
    empty: list[Path] = []
    invalid_json: list[Path] = []

    for relative_path in required_artifacts:
        artifact_path = base_dir / relative_path
        if not artifact_path.exists() or not artifact_path.is_file():
            missing.append(relative_path)
            continue

        try:
            content = artifact_path.read_text(encoding="utf-8")
        except OSError:
            unreadable.append(relative_path)
            continue

        if not content.strip():
            empty.append(relative_path)
            continue

        if artifact_path.suffix.lower() == ".json":
            try:
                json.loads(content)
            except json.JSONDecodeError:
                invalid_json.append(relative_path)

    failures: list[str] = []
    if missing:
        failures.append(f"Missing required artifact(s): {', '.join(str(path) for path in missing)}")
    if unreadable:
        failures.append(f"Unreadable artifact(s): {', '.join(str(path) for path in unreadable)}")
    if empty:
        failures.append(f"Empty artifact(s): {', '.join(str(path) for path in empty)}")
    if invalid_json:
        failures.append(f"Invalid JSON artifact(s): {', '.join(str(path) for path in invalid_json)}")

    if failures:
        raise ValueError("; ".join(failures))


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate required release evaluation artifacts.")
    parser.add_argument(
        "--base-dir",
        default=".",
        help="Directory to resolve required artifact paths from.",
    )
    parser.add_argument(
        "--artifact",
        action="append",
        dest="artifacts",
        help="Relative artifact path to validate. Repeatable. Defaults to required release artifacts.",
    )
    args = parser.parse_args()

    required_paths = (
        tuple(Path(path) for path in args.artifacts)
        if args.artifacts
        else REQUIRED_RELEASE_ARTIFACTS
    )
    validate_release_artifacts(base_dir=Path(args.base_dir), required_artifacts=required_paths)
    print(f"[OK] Release artifacts validated ({len(required_paths)} files).")


if __name__ == "__main__":
    main()
