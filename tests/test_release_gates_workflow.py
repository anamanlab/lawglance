from __future__ import annotations

import re
from pathlib import Path

WORKFLOW_PATH = (
    Path(__file__).resolve().parent.parent
    / ".github"
    / "workflows"
    / "release-gates.yml"
)
REQUIRED_RELEASE_ARTIFACTS = [
    "artifacts/evals/jurisdiction-eval-report.json",
    "artifacts/evals/jurisdiction-eval-report.md",
    "artifacts/evals/jurisdictional-suite-report.json",
    "artifacts/evals/jurisdictional-suite-report.md",
    "artifacts/evals/frontend-test-summary.xml",
    "artifacts/evals/staging-smoke-report.json",
    "artifacts/ingestion/case-law-conformance-report.json",
]
REQUIRED_FRONTEND_RELEASE_STEPS = [
    "Install frontend dependencies",
    "Frontend build",
    "Frontend contract tests",
]
REQUIRED_BACKEND_POLICY_STEP_SNIPPETS = [
    "Run backend policy and export guard tests",
    "tests/test_source_policy.py",
    "tests/test_export_policy_gate.py",
    "tests/test_ops_alert_evaluator.py",
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


def test_release_gates_runs_backend_policy_and_export_guard_tests() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
    for snippet in REQUIRED_BACKEND_POLICY_STEP_SNIPPETS:
        assert snippet in workflow


def test_release_gates_enforces_hardened_synthetic_citation_toggle() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert "Validate hardened runtime safety toggles" in workflow
    assert 'ALLOW_SCAFFOLD_SYNTHETIC_CITATIONS: "false"' in workflow
    assert "CITATION_TRUSTED_DOMAINS:" in workflow


def test_release_gates_links_staging_smoke_rollback_guidance() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert "Rollback trigger guidance" in workflow
    assert "docs/release/staging-smoke-rollback-criteria.md" in workflow


def test_release_gates_runs_on_release_refs() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert "workflow_dispatch" in workflow
    tags_pattern = r'^\s*tags:\s*$[\s\S]*?^\s*-\s*["\']?v\*["\']?\s*$'
    assert re.search(tags_pattern, workflow, re.MULTILINE) is not None
    release_branch_pattern = r'^\s*-\s*["\']?release/\*\*["\']?\s*$'
    assert re.search(release_branch_pattern, workflow, re.MULTILINE) is None
    assert "concurrency:" in workflow
    assert "staging-smoke-${{ github.ref }}" in workflow
    assert "cancel-in-progress: true" in workflow
