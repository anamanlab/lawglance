from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.build_case_law_scorecard import build_case_law_scorecard, main  # noqa: E402


def test_build_case_law_scorecard_schema_and_aggregation() -> None:
    ingestion_report = {
        "completed_at": "2026-02-24T18:10:00Z",
        "results": [
            {
                "source_id": "SCC_DECISIONS",
                "status": "success",
                "records_total": 5,
                "records_valid": 4,
                "records_invalid": 1,
                "fetched_at": "2026-02-24T18:00:00Z",
            },
            {
                "source_id": "FC_DECISIONS",
                "status": "success",
                "records_total": 3,
                "records_valid": 3,
                "records_invalid": 0,
                "fetched_at": "2026-02-24T17:30:00Z",
            },
        ],
    }
    generated_at = datetime(2026, 2, 24, 20, 0, 0, tzinfo=UTC)

    scorecard = build_case_law_scorecard(ingestion_report, generated_at=generated_at)

    assert scorecard["generated_at"] == "2026-02-24T20:00:00Z"
    assert scorecard["ingestion_completed_at"] == "2026-02-24T18:10:00Z"
    assert scorecard["overall"] == {
        "sources_total": 2,
        "sources_failed": 0,
        "records_total": 8,
        "records_valid": 7,
        "records_invalid": 1,
    }
    assert len(scorecard["sources"]) == 2

    scc = scorecard["sources"][0]
    assert scc["source_id"] == "SCC_DECISIONS"
    assert scc["records_total"] == 5
    assert scc["records_valid"] == 4
    assert scc["records_invalid"] == 1
    assert isinstance(scc["freshness_lag_seconds"], int)
    assert scc["freshness_lag_seconds"] > 0

    fc = scorecard["sources"][1]
    assert fc["source_id"] == "FC_DECISIONS"
    assert fc["records_total"] == 3
    assert fc["records_valid"] == 3
    assert fc["records_invalid"] == 0
    assert isinstance(fc["freshness_lag_seconds"], int)
    assert fc["freshness_lag_seconds"] > 0


def test_build_case_law_scorecard_cli_writes_output(tmp_path: Path) -> None:
    ingestion_report_path = tmp_path / "ingestion-report.json"
    output_path = tmp_path / "scorecard.json"
    ingestion_report_path.write_text(
        json.dumps(
            {
                "completed_at": "2026-02-24T10:00:00Z",
                "results": [
                    {
                        "source_id": "FCA_DECISIONS",
                        "status": "error",
                        "records_total": 0,
                        "records_valid": 0,
                        "records_invalid": 0,
                        "fetched_at": "2026-02-24T09:00:00Z",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    exit_code = main(
        [
            "--ingestion-report",
            str(ingestion_report_path),
            "--output",
            str(output_path),
        ]
    )

    assert exit_code == 0
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["overall"]["sources_total"] == 1
    assert payload["overall"]["sources_failed"] == 1
    assert payload["sources"][0]["source_id"] == "FCA_DECISIONS"
