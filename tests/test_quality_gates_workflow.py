from __future__ import annotations

import re
from pathlib import Path

WORKFLOW_PATH = Path(__file__).resolve().parent.parent / ".github" / "workflows" / "quality-gates.yml"
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
    pattern = r"actions/dependency-review-action@[0-9a-f]{40}\b"
    match = re.search(pattern, workflow)
    assert match is not None, f"expected pattern {pattern!r} in workflow snippet: {workflow[:220]!r}"
