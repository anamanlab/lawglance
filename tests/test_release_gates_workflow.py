from __future__ import annotations

from pathlib import Path

WORKFLOW_PATH = Path(".github/workflows/release-gates.yml")
REQUIRED_RELEASE_ARTIFACTS = [
    "artifacts/evals/jurisdiction-eval-report.json",
    "artifacts/evals/jurisdiction-eval-report.md",
    "artifacts/evals/jurisdictional-suite-report.json",
    "artifacts/evals/jurisdictional-suite-report.md",
]


def test_release_gates_enforces_strict_legal_checklist_validation() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert "validate_legal_review_checklist.py --require-checked" in workflow
    assert "inputs.require_legal_checkboxes" not in workflow


def test_release_gates_keeps_required_release_evidence_artifacts() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
    for artifact_path in REQUIRED_RELEASE_ARTIFACTS:
        assert artifact_path in workflow
