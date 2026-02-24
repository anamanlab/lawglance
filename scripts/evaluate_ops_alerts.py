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

from immcad_api.ops import (  # noqa: E402
    build_alert_report,
    build_metrics_url,
    evaluate_alert_rules,
    fetch_ops_metrics,
    load_alert_rules,
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate IMMCAD operational metrics against alert thresholds.")
    parser.add_argument(
        "--metrics-url",
        default=None,
        help="Full URL to /ops/metrics. If omitted, derived from IMMCAD_API_BASE_URL.",
    )
    parser.add_argument(
        "--base-url-env",
        default="IMMCAD_API_BASE_URL",
        help="Environment variable containing API base URL when --metrics-url is not provided.",
    )
    parser.add_argument(
        "--bearer-token",
        default=None,
        help="Bearer token for operational endpoint auth. Falls back to IMMCAD_API_BEARER_TOKEN/API_BEARER_TOKEN.",
    )
    parser.add_argument(
        "--thresholds",
        default="config/ops_alert_thresholds.json",
        help="Path to alert threshold config JSON.",
    )
    parser.add_argument(
        "--output",
        default="artifacts/ops/ops-alert-eval.json",
        help="Path to write alert evaluation JSON report.",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=10.0,
        help="HTTP timeout for metrics fetch.",
    )
    parser.add_argument(
        "--allow-missing-metrics",
        action="store_true",
        help="Downgrade missing metrics from failure to warning.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()

    metrics_url = args.metrics_url
    if not metrics_url:
        base_url = os.getenv(args.base_url_env, "").strip()
        if not base_url:
            raise ValueError(
                f"Missing --metrics-url and environment variable {args.base_url_env} is not set"
            )
        metrics_url = build_metrics_url(base_url)

    bearer_token = (
        args.bearer_token
        or os.getenv("IMMCAD_API_BEARER_TOKEN")
        or os.getenv("API_BEARER_TOKEN")
        or None
    )

    rules = load_alert_rules(args.thresholds)
    metrics_payload = fetch_ops_metrics(
        metrics_url=metrics_url,
        bearer_token=bearer_token,
        timeout_seconds=args.timeout_seconds,
    )
    checks = evaluate_alert_rules(
        metrics_payload=metrics_payload,
        rules=rules,
        fail_on_missing=not args.allow_missing_metrics,
    )
    report = build_alert_report(metrics_url=metrics_url, checks=checks)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")

    print(
        "Ops alert evaluation complete "
        f"(status={report.status}, total_checks={report.total_checks}, "
        f"failing_checks={report.failing_checks}, warning_checks={report.warning_checks})."
    )
    print(f"Report path: {output_path}")

    if report.status == "fail":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
