from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
WORKER_PATH = REPO_ROOT / "backend-cloudflare" / "src" / "worker.ts"
DOCKERFILE_PATH = REPO_ROOT / "backend-cloudflare" / "Dockerfile"
WRANGLER_PATH = REPO_ROOT / "backend-cloudflare" / "wrangler.backend-proxy.jsonc"
README_PATH = REPO_ROOT / "backend-cloudflare" / "README.md"


def test_cloudflare_backend_spike_artifacts_exist() -> None:
    assert WORKER_PATH.exists()
    assert DOCKERFILE_PATH.exists()
    assert WRANGLER_PATH.exists()
    assert README_PATH.exists()


def test_backend_proxy_worker_uses_allowlist_and_origin_env() -> None:
    worker = WORKER_PATH.read_text(encoding="utf-8")
    assert "ALLOWED_PATH_PREFIXES" in worker
    assert '"/api/"' in worker
    assert '"/ops/"' in worker
    assert '"/healthz"' in worker
    assert "BACKEND_ORIGIN" in worker


def test_backend_cloudflare_dockerfile_targets_fastapi_app() -> None:
    dockerfile = DOCKERFILE_PATH.read_text(encoding="utf-8")
    assert "immcad_api.main:app" in dockerfile
    assert "backend-vercel/src" in dockerfile
    assert "backend-vercel/config" in dockerfile


def test_backend_cloudflare_wrangler_uses_placeholder_origin() -> None:
    wrangler = WRANGLER_PATH.read_text(encoding="utf-8")
    assert '"BACKEND_ORIGIN": "https://backend-origin.example"' in wrangler
