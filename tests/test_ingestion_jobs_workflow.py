from __future__ import annotations

from pathlib import Path


WORKFLOW_PATH = (
    Path(__file__).resolve().parent.parent
    / ".github"
    / "workflows"
    / "ingestion-jobs.yml"
)


def test_ingestion_jobs_workflow_runs_cloudflare_hourly_schedule() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert 'cron: "15 * * * *"' in workflow
    assert "cadence: cloudflare_hourly" in workflow
    assert "scripts/run_cloudflare_ingestion_hourly.py" in workflow


def test_ingestion_jobs_workflow_gates_matrix_rows_by_schedule_window() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert "matrix.run_on_schedule" in workflow
    assert "github.event_name != 'schedule'" in workflow
    assert "github.event.schedule == matrix.schedule_cron" in workflow


def test_ingestion_jobs_workflow_persists_federal_laws_materialization_state() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert ".cache/immcad/federal-laws-materialization-checkpoints.json" in workflow
    assert ".cache/immcad/federal-laws-sections" in workflow
