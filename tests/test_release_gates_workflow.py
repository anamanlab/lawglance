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
    "Frontend typecheck",
    "Frontend contract tests",
]
REQUIRED_BACKEND_POLICY_STEP_SNIPPETS = [
    "Run backend policy and export guard tests",
    "Backend typecheck",
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
    assert "../artifacts/evals/frontend-test-summary.xml" in workflow


def test_release_gates_keeps_deterministic_frontend_step_order() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
    build_idx = workflow.index("Frontend build")
    typecheck_idx = workflow.index("Frontend typecheck")
    tests_idx = workflow.index("Frontend contract tests")
    assert build_idx < typecheck_idx < tests_idx


def test_release_gates_runs_backend_policy_and_export_guard_tests() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert "Validate Cloudflare edge-proxy contract" in workflow
    assert "scripts/check_cloudflare_edge_proxy_contract.sh" in workflow
    for snippet in REQUIRED_BACKEND_POLICY_STEP_SNIPPETS:
        assert snippet in workflow
    assert "Validate Cloudflare environment configuration" in workflow
    assert "scripts/validate_cloudflare_env_configuration.py" in workflow
    assert "Validate backend runtime source-of-truth" in workflow
    assert "scripts/validate_backend_runtime_source_of_truth.py" in workflow
    assert "GIT_DIFF_BASE:" in workflow
    assert "GIT_DIFF_HEAD:" in workflow
    assert "uv run mypy" in workflow


def test_release_gates_enforces_hardened_synthetic_citation_toggle() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert "Validate hardened runtime safety toggles" in workflow
    assert "IMMCAD_ENVIRONMENT: ci-smoke" in workflow
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


def test_release_gates_uses_read_only_job_permissions() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert "permissions:" in workflow
    assert "contents: read" in workflow


def test_release_gates_pins_core_actions_to_commit_shas() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
    for action_name in (
        "actions/checkout",
        "astral-sh/setup-uv",
        "actions/setup-node",
        "actions/upload-artifact",
    ):
        pattern = rf"{re.escape(action_name)}@[0-9a-f]{{40}}"
        assert re.search(pattern, workflow), f"missing pinned SHA for {action_name}"
