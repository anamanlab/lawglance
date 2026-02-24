#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = REPO_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run IMMCAD ingestion jobs from source registry")
    parser.add_argument(
        "--cadence",
        choices=["all", "daily", "weekly", "scheduled_incremental"],
        default="all",
        help="Select which cadence bucket to execute.",
    )
    parser.add_argument(
        "--registry",
        default=None,
        help="Optional path to source registry JSON (defaults to canonical registry).",
    )
    parser.add_argument(
        "--court-validation-max-invalid-ratio",
        type=float,
        default=0.0,
        help="Maximum tolerated invalid-record ratio for supported court feeds (0.0-1.0).",
    )
    parser.add_argument(
        "--court-validation-min-valid-records",
        type=int,
        default=1,
        help="Minimum valid court records required for supported court feeds.",
    )
    parser.add_argument(
        "--court-validation-expected-year",
        type=int,
        default=None,
        help="Optional expected court decision year for supported court feeds.",
    )
    parser.add_argument(
        "--court-validation-year-window",
        type=int,
        default=0,
        help="Allowed +/- year window when --court-validation-expected-year is set.",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=30.0,
        help="HTTP timeout applied to source fetches.",
    )
    parser.add_argument(
        "--output",
        default="artifacts/ingestion/ingestion-job-report.json",
        help="JSON output path for ingestion report.",
    )
    parser.add_argument(
        "--state-path",
        default="artifacts/ingestion/checkpoints.json",
        help="Checkpoint state path used for conditional requests (ETag/Last-Modified).",
    )
    parser.add_argument(
        "--fail-on-error",
        action="store_true",
        help="Exit non-zero when any source ingestion fails.",
    )
    return parser.parse_args()


def main() -> int:
    from immcad_api.ingestion import run_ingestion_jobs

    args = parse_args()
    cadence = None if args.cadence == "all" else args.cadence

    report = run_ingestion_jobs(
        cadence=cadence,
        registry_path=args.registry,
        court_validation_max_invalid_ratio=args.court_validation_max_invalid_ratio,
        court_validation_min_valid_records=args.court_validation_min_valid_records,
        court_validation_expected_year=args.court_validation_expected_year,
        court_validation_year_window=args.court_validation_year_window,
        timeout_seconds=args.timeout_seconds,
        state_path=args.state_path,
    )

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")

    print(
        "Ingestion report generated "
        f"(cadence={report.cadence}, total={report.total}, "
        f"succeeded={report.succeeded}, not_modified={report.not_modified}, failed={report.failed})"
    )
    print(f"Report path: {output_path}")
    print(f"State path: {args.state_path}")

    if args.fail_on_error and report.failed > 0:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
