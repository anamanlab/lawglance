from __future__ import annotations

from pathlib import Path


WORKFLOW_PATH = (
    Path(__file__).resolve().parent.parent
    / ".github"
    / "workflows"
    / "cloudflare-backend-native-deploy.yml"
)


def test_cloudflare_backend_native_deploy_workflow_exists() -> None:
    assert WORKFLOW_PATH.exists()


def test_cloudflare_backend_native_deploy_workflow_has_expected_steps() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
    required_steps = [
        "Validate Cloudflare credentials are configured",
        "Sync backend runtime source for native worker",
        "Setup Python worker toolchain",
        "Deploy backend native Python worker",
    ]
    for step_name in required_steps:
        assert step_name in workflow


def test_cloudflare_backend_native_deploy_workflow_has_concurrency_deduplication() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert "concurrency:" in workflow
    assert "cloudflare-backend-native-deploy-${{ github.ref }}" in workflow
    assert "cancel-in-progress: true" in workflow


def test_cloudflare_backend_native_deploy_workflow_uses_pywrangler() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert "uv run pywrangler deploy" in workflow
