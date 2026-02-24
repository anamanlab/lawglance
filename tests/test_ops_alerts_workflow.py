from __future__ import annotations

from pathlib import Path

import pytest

WORKFLOW_PATH = Path(__file__).resolve().parent.parent / ".github" / "workflows" / "ops-alerts.yml"


@pytest.fixture(scope="module")
def workflow_text() -> str:
    assert WORKFLOW_PATH.exists(), f"ops alerts workflow not found at {WORKFLOW_PATH}"
    return WORKFLOW_PATH.read_text(encoding="utf-8")


def test_ops_alerts_workflow_has_schedule_and_dispatch(workflow_text: str) -> None:
    assert "workflow_dispatch" in workflow_text
    assert "*/15 * * * *" in workflow_text


def test_ops_alerts_workflow_runs_alert_evaluator_with_threshold_config(workflow_text: str) -> None:
    assert "scripts/evaluate_ops_alerts.py" in workflow_text
    assert "config/ops_alert_thresholds.json" in workflow_text
    assert "artifacts/ops/ops-alert-eval.json" in workflow_text


def test_ops_alerts_workflow_references_incident_runbook_on_failure(workflow_text: str) -> None:
    assert "Incident runbook guidance" in workflow_text
    assert "docs/release/incident-observability-runbook.md" in workflow_text
