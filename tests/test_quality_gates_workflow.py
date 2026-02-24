from __future__ import annotations

import re
from pathlib import Path

WORKFLOW_PATH = Path(".github/workflows/quality-gates.yml")
REQUIRED_FRONTEND_QUALITY_STEPS = [
    "Install frontend dependencies",
    "Frontend build",
    "Frontend contract tests",
]
REQUIRED_SECURITY_AND_INGESTION_STEPS = [
    "Dependency review (PR)",
    "Run ingestion smoke checks",
    "Upload ingestion smoke artifact",
]


def test_quality_gates_runs_frontend_build_and_tests() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
    for step_name in REQUIRED_FRONTEND_QUALITY_STEPS:
        assert step_name in workflow


def test_quality_gates_enforces_hardened_synthetic_citation_toggle() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert "Validate hardened runtime safety toggles" in workflow
    assert "ALLOW_SCAFFOLD_SYNTHETIC_CITATIONS: \"false\"" in workflow
    assert "CITATION_TRUSTED_DOMAINS:" in workflow


def test_quality_gates_includes_dependency_review_and_ingestion_smoke() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
    for step_name in REQUIRED_SECURITY_AND_INGESTION_STEPS:
        assert step_name in workflow
    assert re.search(r"actions/dependency-review-action@[0-9a-f]{40}\b", workflow)


def test_quality_gates_runs_case_law_conformance_warning_only() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert "Run case-law conformance (warning-only)" in workflow
    assert "scripts/run_case_law_conformance.py --output artifacts/ingestion/case-law-conformance-report.json" in workflow
    warning_step_block = workflow.split("Run case-law conformance (warning-only)", 1)[1]
    warning_step_block = warning_step_block.split("\n      - name:", 1)[0]
    assert "--strict" not in warning_step_block


def test_quality_gates_uploads_case_law_conformance_artifact() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert "Upload case-law conformance artifact" in workflow
    assert "artifacts/ingestion/case-law-conformance-report.json" in workflow
