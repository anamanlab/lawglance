from __future__ import annotations

from pathlib import Path


WORKFLOW_PATH = (
    Path(__file__).resolve().parent.parent
    / ".github"
    / "workflows"
    / "cloudflare-frontend-deploy.yml"
)


def test_cloudflare_frontend_deploy_workflow_exists() -> None:
    assert WORKFLOW_PATH.exists()


def test_cloudflare_frontend_deploy_workflow_has_expected_steps() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
    required_steps = [
        "Validate Cloudflare credentials are configured",
        "Install frontend dependencies",
        "Frontend typecheck",
        "Frontend contract tests",
        "Build OpenNext Cloudflare bundle",
        "Deploy frontend to Cloudflare Workers",
    ]
    for step_name in required_steps:
        assert step_name in workflow


def test_cloudflare_frontend_deploy_workflow_keeps_deterministic_order() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
    typecheck_idx = workflow.index("Frontend typecheck")
    tests_idx = workflow.index("Frontend contract tests")
    build_idx = workflow.index("Build OpenNext Cloudflare bundle")
    deploy_idx = workflow.index("Deploy frontend to Cloudflare Workers")
    assert typecheck_idx < tests_idx < build_idx < deploy_idx


def test_cloudflare_frontend_deploy_workflow_has_concurrency_deduplication() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert "concurrency:" in workflow
    assert "cloudflare-frontend-deploy-${{ github.ref }}" in workflow
    assert "cancel-in-progress: true" in workflow
