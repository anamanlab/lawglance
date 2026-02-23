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
        description="Run jurisdictional behavior test suite and emit report artifacts"
    )
    parser.add_argument(
        "--dataset",
        default=None,
        help="Optional dataset JSON path. Defaults to canonical jurisdictional suite.",
    )
    parser.add_argument(
        "--min-case-pass-rate",
        type=float,
        default=95.0,
        help="Minimum overall case pass rate required.",
    )
    parser.add_argument(
        "--min-citation-coverage",
        type=float,
        default=95.0,
        help="Minimum citation coverage for grounded-info cases.",
    )
    parser.add_argument(
        "--min-policy-accuracy",
        type=float,
        default=100.0,
        help="Minimum policy-refusal accuracy required.",
    )
    parser.add_argument(
        "--output-json",
        default="artifacts/evals/jurisdictional-suite-report.json",
        help="Output JSON report path.",
    )
    parser.add_argument(
        "--output-md",
        default="artifacts/evals/jurisdictional-suite-report.md",
        help="Output Markdown report path.",
    )
    return parser.parse_args()


def main() -> int:
    from immcad_api.evaluation import (
        evaluate_jurisdictional_suite,
        load_jurisdictional_suite,
        write_jurisdiction_suite_artifacts,
    )

    args = parse_args()
    dataset_path, dataset_version, cases = load_jurisdictional_suite(args.dataset)
    report = evaluate_jurisdictional_suite(
        cases,
        dataset_path=dataset_path,
        dataset_version=dataset_version,
        min_case_pass_rate=args.min_case_pass_rate,
        min_citation_coverage=args.min_citation_coverage,
        min_policy_accuracy=args.min_policy_accuracy,
    )

    write_jurisdiction_suite_artifacts(
        report,
        json_path=args.output_json,
        markdown_path=args.output_md,
    )

    print(
        "Jurisdictional suite complete "
        f"(status={report.status}, total={report.total_cases}, "
        f"pass={report.passed_cases}, fail={report.failed_cases}, "
        f"citation_coverage={report.citation_coverage_percent}%)."
    )
    print(f"JSON report: {args.output_json}")
    print(f"Markdown report: {args.output_md}")

    return 0 if report.status == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
