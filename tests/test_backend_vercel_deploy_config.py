from __future__ import annotations

import json
from pathlib import Path


BACKEND_VERCEL_CONFIG = Path("backend-vercel/vercel.json")
BACKEND_VERCELIGNORE = Path("backend-vercel/.vercelignore")
BACKEND_PYTHON_VERSION = Path("backend-vercel/.python-version")


def _load_backend_vercel_config() -> dict[str, object]:
    return json.loads(BACKEND_VERCEL_CONFIG.read_text(encoding="utf-8"))


def test_backend_vercel_pins_supported_python_runtime_via_python_version_file() -> None:
    assert BACKEND_PYTHON_VERSION.exists(), (
        "backend-vercel/.python-version is required to pin a supported Vercel "
        "Python runtime and avoid defaulting to deprecated versions from stale "
        "prebuilt artifacts."
    )
    pinned_version = BACKEND_PYTHON_VERSION.read_text(encoding="utf-8").strip()
    assert pinned_version == "3.12"

    config = _load_backend_vercel_config()
    functions = config.get("functions")
    assert isinstance(functions, dict), "backend-vercel/vercel.json must define functions config"

    index_config = functions.get("api/index.py")
    assert isinstance(index_config, dict), "api/index.py function config is required"
    assert "runtime" not in index_config, (
        "Use Vercel's documented Python version pinning via .python-version/pyproject "
        "rather than forcing a runtime string in vercel.json."
    )


def test_backend_vercel_blocks_local_env_and_prebuilt_output_from_deploy_context() -> None:
    assert BACKEND_VERCELIGNORE.exists(), "backend-vercel/.vercelignore is required"
    vercelignore_text = BACKEND_VERCELIGNORE.read_text(encoding="utf-8")
    assert ".env.*" in vercelignore_text
    assert ".vercel" in vercelignore_text

    config = _load_backend_vercel_config()
    functions = config["functions"]
    index_config = functions["api/index.py"]
    exclude_files = index_config.get("excludeFiles")
    assert isinstance(exclude_files, str)
    assert ".env" in exclude_files
    assert ".vercel" in exclude_files
