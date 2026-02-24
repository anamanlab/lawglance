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

from immcad_api.ops.case_law_conformance import run_case_law_conformance  # noqa: E402


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Probe SCC/FC/FCA endpoints and validate parser conformance."
    )
    parser.add_argument(
        "--output",
        default="artifacts/ingestion/case-law-conformance-report.json",
        help="Path to write the conformance report JSON.",
    )
    parser.add_argument(
        "--registry",
        default=None,
        help="Optional path to source registry JSON.",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=20.0,
        help="HTTP timeout per source.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Return non-zero when the conformance report has failures.",
    )
    parser.add_argument(
        "--max-invalid-ratio",
        type=float,
        default=0.10,
        help="Maximum tolerated invalid record ratio before a source fails.",
    )
    parser.add_argument(
        "--min-records",
        type=int,
        default=1,
        help="Minimum records expected from each source.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = run_case_law_conformance(
        registry_path=args.registry,
        timeout_seconds=args.timeout_seconds,
        strict=args.strict,
        max_invalid_ratio=args.max_invalid_ratio,
        min_records=args.min_records,
    )

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    results = report.get("results", [])
    fail_count = sum(1 for item in results if item.get("status") == "fail")
    warn_count = sum(1 for item in results if item.get("status") == "warn")
    pass_count = sum(1 for item in results if item.get("status") == "pass")
    print(
        "Case-law conformance "
        f"status={report.get('overall_status')} pass={pass_count} "
        f"warn={warn_count} fail={fail_count}"
    )
    print(f"Conformance report: {output_path}")

    if args.strict and report.get("overall_status") == "fail":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
