from __future__ import annotations

from pathlib import Path

WORKFLOW_PATH = Path(__file__).resolve().parent.parent / ".github" / "workflows" / "ops-alerts.yml"


def test_ops_alerts_workflow_has_schedule_and_dispatch() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert "workflow_dispatch" in workflow
    assert "*/15 * * * *" in workflow


def test_ops_alerts_workflow_runs_alert_evaluator_with_threshold_config() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert "scripts/evaluate_ops_alerts.py" in workflow
    assert "config/ops_alert_thresholds.json" in workflow
    assert "artifacts/ops/ops-alert-eval.json" in workflow


def test_ops_alerts_workflow_references_incident_runbook_on_failure() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert "Incident runbook guidance" in workflow
    assert "docs/release/incident-observability-runbook.md" in workflow
