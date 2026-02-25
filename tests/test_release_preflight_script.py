from __future__ import annotations

from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parent.parent / "scripts" / "release_preflight.sh"


def test_release_preflight_script_exists() -> None:
    assert SCRIPT_PATH.exists()


def test_release_preflight_runs_cloudflare_preflight_checks() -> None:
    script = SCRIPT_PATH.read_text(encoding="utf-8")
    assert "scripts/check_cloudflare_free_plan_readiness.sh" in script
    assert "scripts/check_cloudflare_edge_proxy_contract.sh" in script
    assert "SKIP_CLOUDFLARE_FREE_PLAN_CHECK" in script
    assert "SKIP_CLOUDFLARE_EDGE_CONTRACT_CHECK" in script


def test_release_preflight_keeps_hygiene_and_wrangler_checks() -> None:
    script = SCRIPT_PATH.read_text(encoding="utf-8")
    assert "scripts/check_repository_hygiene.sh" in script
    assert "wrangler@4.68.1 --version" in script
    assert "wrangler@4.68.1 whoami" in script
