#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = REPO_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a jurisdictional readiness evaluation report"
    )
    parser.add_argument(
        "--threshold",
        type=int,
        default=95,
        help="Minimum score required for success.",
    )
    parser.add_argument(
        "--output-json",
        default="artifacts/evals/jurisdiction-eval-report.json",
        help="Output JSON report path.",
    )
    parser.add_argument(
        "--output-md",
        default="artifacts/evals/jurisdiction-eval-report.md",
        help="Output Markdown report path.",
    )
    return parser.parse_args()


def main() -> int:
    from immcad_api.evaluation import (
        evaluate_jurisdictional_readiness,
        write_jurisdiction_report_artifacts,
    )

    args = parse_args()
    report = evaluate_jurisdictional_readiness(threshold=args.threshold)

    write_jurisdiction_report_artifacts(
        report,
        json_path=args.output_json,
        markdown_path=args.output_md,
    )

    print(
        "Jurisdiction evaluation complete "
        f"(score={report.score}/{report.max_score}, "
        f"threshold={report.threshold}, status={report.status})."
    )
    print(f"JSON report: {args.output_json}")
    print(f"Markdown report: {args.output_md}")

    return 0 if report.status == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
