from __future__ import annotations

from pathlib import Path

WORKFLOW_PATH = Path(".github/workflows/quality-gates.yml")
REQUIRED_FRONTEND_QUALITY_STEPS = [
    "Install frontend dependencies",
    "Frontend build",
    "Frontend contract tests",
]


def test_quality_gates_runs_frontend_build_and_tests() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
    for step_name in REQUIRED_FRONTEND_QUALITY_STEPS:
        assert step_name in workflow


def test_quality_gates_enforces_hardened_synthetic_citation_toggle() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert "Validate hardened runtime safety toggles" in workflow
    assert "ALLOW_SCAFFOLD_SYNTHETIC_CITATIONS: \"false\"" in workflow
