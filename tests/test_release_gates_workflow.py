from __future__ import annotations

from pathlib import Path

WORKFLOW_PATH = Path(".github/workflows/release-gates.yml")
REQUIRED_RELEASE_ARTIFACTS = [
    "artifacts/evals/jurisdiction-eval-report.json",
    "artifacts/evals/jurisdiction-eval-report.md",
    "artifacts/evals/jurisdictional-suite-report.json",
    "artifacts/evals/jurisdictional-suite-report.md",
    "artifacts/evals/frontend-test-summary.xml",
]
REQUIRED_FRONTEND_RELEASE_STEPS = [
    "Install frontend dependencies",
    "Frontend build",
    "Frontend contract tests",
]


def test_release_gates_enforces_strict_legal_checklist_validation() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert "validate_legal_review_checklist.py --require-checked" in workflow
    assert "inputs.require_legal_checkboxes" not in workflow


def test_release_gates_keeps_required_release_evidence_artifacts() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
    for artifact_path in REQUIRED_RELEASE_ARTIFACTS:
        assert artifact_path in workflow


def test_release_gates_runs_frontend_build_and_tests() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
    for step_name in REQUIRED_FRONTEND_RELEASE_STEPS:
        assert step_name in workflow


def test_release_gates_enforces_hardened_synthetic_citation_toggle() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert "Validate hardened runtime safety toggles" in workflow
    assert "ALLOW_SCAFFOLD_SYNTHETIC_CITATIONS: \"false\"" in workflow
