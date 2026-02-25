#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = REPO_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))


def _normalize_env_value(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    return normalized


def resolve_default_runtime_environment() -> str:
    explicit_environment = _normalize_env_value(os.getenv("ENVIRONMENT"))
    compatibility_environment = _normalize_env_value(os.getenv("IMMCAD_ENVIRONMENT"))
    if (
        explicit_environment
        and compatibility_environment
        and explicit_environment.lower() != compatibility_environment.lower()
    ):
        raise ValueError("ENVIRONMENT and IMMCAD_ENVIRONMENT must match when both are set")
    return explicit_environment or compatibility_environment or "development"


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
        "--source-policy",
        default=os.getenv("SOURCE_POLICY_PATH") or "config/source_policy.yaml",
        help="Optional path to source policy JSON/YAML (defaults to config/source_policy.yaml).",
    )
    parser.add_argument(
        "--fetch-policy",
        default=os.getenv("FETCH_POLICY_PATH") or "config/fetch_policy.yaml",
        help="Optional path to source fetch policy YAML (defaults to config/fetch_policy.yaml).",
    )
    parser.add_argument(
        "--environment",
        default=resolve_default_runtime_environment(),
        help=(
            "Runtime environment for policy gates "
            "(development/staging/production/prod/ci, including hardened aliases)."
        ),
    )
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=None,
        help=(
            "Optional HTTP timeout override applied to all source fetches "
            "(when omitted, fetch policy defaults are used)."
        ),
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

    try:
        args = parse_args()
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    cadence = None if args.cadence == "all" else args.cadence

    report = run_ingestion_jobs(
        cadence=cadence,
        registry_path=args.registry,
        source_policy_path=args.source_policy,
        fetch_policy_path=args.fetch_policy,
        environment=args.environment,
        timeout_seconds=args.timeout_seconds,
        state_path=args.state_path,
    )

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")

    print(
        "Ingestion report generated "
        f"(cadence={report.cadence}, total={report.total}, "
        f"succeeded={report.succeeded}, not_modified={report.not_modified}, "
        f"blocked={report.blocked}, failed={report.failed})"
    )
    print(f"Report path: {output_path}")
    print(f"State path: {args.state_path}")

    if args.fail_on_error and report.failed > 0:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
