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
        timeout_seconds=args.timeout_seconds,
    )

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")

    print(
        "Ingestion report generated "
        f"(cadence={report.cadence}, total={report.total}, "
        f"succeeded={report.succeeded}, failed={report.failed})"
    )
    print(f"Report path: {output_path}")

    if args.fail_on_error and report.failed > 0:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
