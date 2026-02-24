#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def _utc_now_iso() -> str:
    return datetime.now(tz=UTC).isoformat().replace("+00:00", "Z")


def _parse_iso_utc(value: str) -> datetime:
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    return datetime.fromisoformat(normalized).astimezone(UTC)


def _safe_int(value: Any, default: int = 0) -> int:
    if value is None:
        return default
    if isinstance(value, bool):
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def build_case_law_scorecard(
    ingestion_report: dict[str, Any],
    *,
    generated_at: datetime | None = None,
) -> dict[str, Any]:
    generated_dt = generated_at or datetime.now(tz=UTC)
    generated_iso = generated_dt.isoformat().replace("+00:00", "Z")
    completed_at = ingestion_report.get("completed_at")

    raw_results = ingestion_report.get("results")
    if not isinstance(raw_results, list):
        raise ValueError("ingestion report must include a list at 'results'")

    sources: list[dict[str, Any]] = []
    records_total_sum = 0
    records_valid_sum = 0
    records_invalid_sum = 0
    failed_sources = 0

    for item in raw_results:
        if not isinstance(item, dict):
            continue

        source_id = str(item.get("source_id", "unknown"))
        status = str(item.get("status", "unknown"))
        records_total = _safe_int(item.get("records_total"), default=0)
        records_valid = _safe_int(item.get("records_valid"), default=0)
        records_invalid = _safe_int(item.get("records_invalid"), default=0)
        fetched_at = item.get("fetched_at")

        freshness_lag_seconds: int | None = None
        if isinstance(fetched_at, str) and fetched_at.strip():
            try:
                fetched_dt = _parse_iso_utc(fetched_at)
            except ValueError:
                freshness_lag_seconds = None
            else:
                freshness_lag_seconds = max(int((generated_dt - fetched_dt).total_seconds()), 0)

        records_total_sum += records_total
        records_valid_sum += records_valid
        records_invalid_sum += records_invalid
        if status == "error":
            failed_sources += 1

        sources.append(
            {
                "source_id": source_id,
                "status": status,
                "records_total": records_total,
                "records_valid": records_valid,
                "records_invalid": records_invalid,
                "freshness_lag_seconds": freshness_lag_seconds,
            }
        )

    return {
        "generated_at": generated_iso,
        "ingestion_completed_at": completed_at,
        "overall": {
            "sources_total": len(sources),
            "sources_failed": failed_sources,
            "records_total": records_total_sum,
            "records_valid": records_valid_sum,
            "records_invalid": records_invalid_sum,
        },
        "sources": sources,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a pilot scorecard from an ingestion execution report."
    )
    parser.add_argument(
        "--ingestion-report",
        required=True,
        help="Path to ingestion execution report JSON (from run_ingestion_jobs.py).",
    )
    parser.add_argument(
        "--output",
        default="artifacts/ingestion/case-law-scorecard.json",
        help="Path to write the scorecard JSON.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    ingestion_report_path = Path(args.ingestion_report)
    payload = json.loads(ingestion_report_path.read_text(encoding="utf-8"))
    scorecard = build_case_law_scorecard(payload)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(scorecard, indent=2) + "\n", encoding="utf-8")

    overall = scorecard["overall"]
    print(
        "Case-law scorecard generated "
        f"(sources={overall['sources_total']}, failed={overall['sources_failed']}, "
        f"records_total={overall['records_total']}, records_invalid={overall['records_invalid']})"
    )
    print(f"Scorecard path: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
