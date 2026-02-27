from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

import asgi
from workers import WorkerEntrypoint, import_from_javascript


def _ensure_backend_source_on_path() -> None:
    """Allow local/dev packaging to import the backend runtime source tree."""
    backend_src = Path(__file__).resolve().parents[2] / "backend-vercel" / "src"
    backend_src_str = str(backend_src)
    if backend_src.exists() and backend_src_str not in sys.path:
        sys.path.insert(0, backend_src_str)


_ensure_backend_source_on_path()

_WORKER_ENV_KEYS = (
    "ENVIRONMENT",
    "IMMCAD_ENVIRONMENT",
    "ENABLE_SCAFFOLD_PROVIDER",
    "ALLOW_SCAFFOLD_SYNTHETIC_CITATIONS",
    "ENABLE_OPENAI_PROVIDER",
    "PRIMARY_PROVIDER",
    "ENABLE_CASE_SEARCH",
    "ENABLE_OFFICIAL_CASE_SOURCES",
    "CASE_SEARCH_OFFICIAL_ONLY_RESULTS",
    "EXPORT_POLICY_GATE_ENABLED",
    "DOCUMENT_REQUIRE_HTTPS",
    "GEMINI_MODEL",
    "OPENAI_MODEL",
    "CITATION_TRUSTED_DOMAINS",
    "IMMCAD_API_BEARER_TOKEN",
    "API_BEARER_TOKEN",
    "GEMINI_API_KEY",
    "OPENAI_API_KEY",
    "CANLII_API_KEY",
    "REDIS_URL",
)


def _read_worker_env_value(env: Any, key: str) -> Any | None:
    if env is None:
        return None
    try:
        value = getattr(env, key)
        if value is not None:
            return value
    except Exception:
        pass
    get_attr = getattr(env, "get", None)
    if callable(get_attr):
        try:
            value = get_attr(key)
            if value is not None:
                return value
        except Exception:
            pass
    try:
        value = env[key]  # type: ignore[index]
        if value is not None:
            return value
    except Exception:
        pass
    return None


def _bootstrap_os_environ_from_worker_env(env: Any) -> None:
    for key in _WORKER_ENV_KEYS:
        value = _read_worker_env_value(env, key)
        if value is None:
            continue
        if isinstance(value, bool):
            os.environ[key] = "true" if value else "false"
            continue
        if isinstance(value, (str, int, float)):
            os.environ[key] = str(value)


def _bootstrap_os_environ_from_global_worker_env() -> None:
    try:
        workers_module = import_from_javascript("cloudflare:workers")
        global_env = getattr(workers_module, "env", None)
        _bootstrap_os_environ_from_worker_env(global_env)
    except Exception:
        # Local/unit-test runtime does not provide cloudflare:workers globals.
        return


_bootstrap_os_environ_from_global_worker_env()

from immcad_api.main import app  # noqa: E402


class Default(WorkerEntrypoint):
    async def fetch(self, request):
        _bootstrap_os_environ_from_worker_env(self.env)
        return await asgi.fetch(app, request, self.env)
