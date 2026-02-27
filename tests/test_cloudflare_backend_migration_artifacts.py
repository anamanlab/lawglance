from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
WORKER_PATH = REPO_ROOT / "backend-cloudflare" / "src" / "worker.ts"
NATIVE_ENTRY_PATH = REPO_ROOT / "backend-cloudflare" / "src" / "entry.py"
DOCKERFILE_PATH = REPO_ROOT / "backend-cloudflare" / "Dockerfile"
WRANGLER_PATH = REPO_ROOT / "backend-cloudflare" / "wrangler.backend-proxy.jsonc"
NATIVE_WRANGLER_TOML = REPO_ROOT / "backend-cloudflare" / "wrangler.toml"
NATIVE_PYPROJECT = REPO_ROOT / "backend-cloudflare" / "pyproject.toml"
README_PATH = REPO_ROOT / "backend-cloudflare" / "README.md"


def test_cloudflare_backend_spike_artifacts_exist() -> None:
    assert WORKER_PATH.exists()
    assert NATIVE_ENTRY_PATH.exists()
    assert DOCKERFILE_PATH.exists()
    assert WRANGLER_PATH.exists()
    assert NATIVE_WRANGLER_TOML.exists()
    assert NATIVE_PYPROJECT.exists()
    assert README_PATH.exists()


def test_backend_proxy_worker_uses_allowlist_and_origin_env() -> None:
    worker = WORKER_PATH.read_text(encoding="utf-8")
    assert "ALLOWED_PATH_PREFIXES" in worker
    assert '"/api/"' in worker
    assert '"/ops/"' in worker
    assert '"/healthz"' in worker
    assert "BACKEND_ORIGIN" in worker
    assert "BACKEND_REQUEST_TIMEOUT_MS" in worker
    assert "BACKEND_RETRY_ATTEMPTS" in worker
    assert "RETRYABLE_STATUS_CODES" in worker
    assert "x-trace-id" in worker
    assert "x-immcad-trace-id" in worker
    assert "error: {" in worker
    assert "code," in worker
    assert "trace_id:" in worker


def test_backend_cloudflare_dockerfile_targets_fastapi_app() -> None:
    dockerfile = DOCKERFILE_PATH.read_text(encoding="utf-8")
    assert "immcad_api.main:app" in dockerfile
    assert "backend-vercel/src" in dockerfile
    assert "backend-vercel/config" in dockerfile


def test_backend_cloudflare_wrangler_uses_placeholder_origin() -> None:
    wrangler = WRANGLER_PATH.read_text(encoding="utf-8")
    assert '"BACKEND_ORIGIN": "https://backend-origin.example"' in wrangler


def test_backend_native_python_entry_uses_asgi_bridge() -> None:
    entry = NATIVE_ENTRY_PATH.read_text(encoding="utf-8")
    assert "class Default(WorkerEntrypoint)" in entry
    assert "return await asgi.fetch(app, request, self.env)" in entry
    assert "def _bootstrap_os_environ_from_worker_env" in entry
    assert "def _bootstrap_os_environ_from_global_worker_env" in entry
    assert 'import_from_javascript("cloudflare:workers")' in entry
    assert "from immcad_api.main import app" in entry


def test_backend_native_wrangler_enables_python_workers_flag() -> None:
    wrangler_toml = NATIVE_WRANGLER_TOML.read_text(encoding="utf-8")
    assert 'compatibility_flags = ["python_workers"]' in wrangler_toml
    assert 'main = "src/entry.py"' in wrangler_toml


def test_backend_native_pyproject_includes_workers_tooling() -> None:
    pyproject = NATIVE_PYPROJECT.read_text(encoding="utf-8")
    assert "workers-py" in pyproject
    assert "workers-runtime-sdk" in pyproject
