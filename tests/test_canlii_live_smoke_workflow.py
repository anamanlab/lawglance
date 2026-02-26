from __future__ import annotations

from pathlib import Path


WORKFLOW_PATH = (
    Path(__file__).resolve().parents[1]
    / ".github"
    / "workflows"
    / "canlii-live-smoke.yml"
)


def test_canlii_live_smoke_workflow_exists() -> None:
    assert WORKFLOW_PATH.exists()


def test_canlii_live_smoke_workflow_runs_free_tier_runtime_validation_bundle() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert "Run free-tier runtime validation bundle" in workflow
    assert "scripts/run_free_tier_runtime_validation.sh" in workflow
    assert "IMMCAD_FRONTEND_URL" in workflow

