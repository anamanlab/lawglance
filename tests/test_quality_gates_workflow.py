from __future__ import annotations

import re
from pathlib import Path

WORKFLOW_PATH = (
    Path(__file__).resolve().parent.parent
    / ".github"
    / "workflows"
    / "quality-gates.yml"
)
REQUIRED_FRONTEND_QUALITY_STEPS = [
    "Install frontend dependencies",
    "Frontend build",
    "Frontend typecheck",
    "Frontend contract tests",
]
REQUIRED_SECURITY_AND_INGESTION_STEPS = [
    "Dependency review (PR)",
    "Backend typecheck",
    "Validate Cloudflare environment configuration",
    "Validate backend runtime source sync",
    "Run SCC/FC API smoke checks",
    "Run ingestion smoke checks",
    "Upload SCC/FC API smoke artifact",
    "Upload ingestion smoke artifact",
]


def test_quality_gates_runs_frontend_build_and_tests() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
    for step_name in REQUIRED_FRONTEND_QUALITY_STEPS:
        assert step_name in workflow


def test_quality_gates_keeps_deterministic_frontend_step_order() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
    build_idx = workflow.index("Frontend build")
    typecheck_idx = workflow.index("Frontend typecheck")
    tests_idx = workflow.index("Frontend contract tests")
    assert build_idx < typecheck_idx < tests_idx


def test_quality_gates_enforces_hardened_synthetic_citation_toggle() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert "Validate hardened runtime safety toggles" in workflow
    assert "IMMCAD_ENVIRONMENT: ci-smoke" in workflow
    assert 'ALLOW_SCAFFOLD_SYNTHETIC_CITATIONS: "false"' in workflow
    assert "CITATION_TRUSTED_DOMAINS:" in workflow


def test_quality_gates_includes_dependency_review_and_ingestion_smoke() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert "Validate Cloudflare edge-proxy contract" in workflow
    assert "scripts/check_cloudflare_edge_proxy_contract.sh" in workflow
    for step_name in REQUIRED_SECURITY_AND_INGESTION_STEPS:
        assert step_name in workflow
    pattern = r"actions/dependency-review-action@[0-9a-f]{40}\b"
    match = re.search(pattern, workflow)
    assert match is not None, (
        f"expected pattern {pattern!r} in workflow snippet: {workflow[:220]!r}"
    )


def test_quality_gates_has_concurrency_deduplication() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert "concurrency:" in workflow
    assert "quality-gates-${{ github.ref }}" in workflow
    assert "cancel-in-progress: true" in workflow


def test_quality_gates_runs_backend_typecheck_before_unit_tests() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
    typecheck_idx = workflow.index("Backend typecheck")
    unit_tests_idx = workflow.index("Run unit tests")
    assert typecheck_idx < unit_tests_idx
    assert "uv run mypy" in workflow


def test_quality_gates_pins_core_actions_to_commit_shas() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
    for action_name in (
        "actions/checkout",
        "astral-sh/setup-uv",
        "actions/setup-node",
        "actions/upload-artifact",
    ):
        pattern = rf"{re.escape(action_name)}@[0-9a-f]{{40}}"
        assert re.search(pattern, workflow), f"missing pinned SHA for {action_name}"
