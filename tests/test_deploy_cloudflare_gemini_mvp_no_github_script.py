from __future__ import annotations

from pathlib import Path


SCRIPT_PATH = (
    Path(__file__).resolve().parent.parent
    / "scripts"
    / "deploy_cloudflare_gemini_mvp_no_github.sh"
)


def test_gemini_mvp_no_github_deploy_script_exists() -> None:
    assert SCRIPT_PATH.exists()


def test_gemini_mvp_no_github_deploy_script_syncs_and_deploys() -> None:
    script = SCRIPT_PATH.read_text(encoding="utf-8")
    assert "sync_cloudflare_backend_native_secrets.sh" in script
    assert "GEMINI_API_KEY" in script
    assert "Cloudflare backend secret GEMINI_API_KEY is missing" in script
    assert "--format json" in script
    assert "ALLOW_GENERATE_BEARER_TOKEN" in script
    assert "IMMCAD_API_BEARER_TOKEN is missing" in script
    assert "Loaded %s from %s" in script
    assert ">&2" in script
    assert "pywrangler deploy" in script
    assert "wrangler@" in script
    assert "frontend-web/wrangler.jsonc" in script
    assert "whoami" in script
