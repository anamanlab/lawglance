from __future__ import annotations

from pathlib import Path


WORKFLOW_PATH = (
    Path(__file__).resolve().parent.parent
    / ".github"
    / "workflows"
    / "cloudflare-backend-proxy-deploy.yml"
)


def test_cloudflare_backend_proxy_deploy_workflow_exists() -> None:
    assert WORKFLOW_PATH.exists()


def test_cloudflare_backend_proxy_deploy_workflow_has_expected_steps() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
    required_steps = [
        "Validate Cloudflare free-plan proxy readiness",
        "Validate Cloudflare edge-proxy contract",
        "Validate Cloudflare credentials are configured",
        "Inject backend origin",
        "Deploy backend proxy to Cloudflare Workers",
    ]
    for step_name in required_steps:
        assert step_name in workflow


def test_cloudflare_backend_proxy_deploy_workflow_requires_backend_origin_secret() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert "IMMCAD_BACKEND_ORIGIN" in workflow


def test_cloudflare_backend_proxy_deploy_workflow_scopes_push_paths_to_proxy_files() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert "backend-cloudflare/src/worker.ts" in workflow
    assert "backend-cloudflare/wrangler.backend-proxy.jsonc" in workflow
    assert "backend-cloudflare/**" not in workflow


def test_cloudflare_backend_proxy_deploy_workflow_has_concurrency_deduplication() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert "concurrency:" in workflow
    assert "cloudflare-backend-proxy-deploy-${{ github.ref }}" in workflow
    assert "cancel-in-progress: true" in workflow
