from __future__ import annotations

import ast
import importlib.util
from pathlib import Path
import re

REPO_ROOT = Path(__file__).resolve().parents[1]
APP_PATH = REPO_ROOT / "app.py"
LEGACY_ARCHIVE_ROOT = REPO_ROOT / "legacy" / "local_rag"
LEGACY_NOTEBOOK_PATH = REPO_ROOT / "test.ipynb"
LEGACY_ROOT_PACKAGE_INIT = REPO_ROOT / "legacy" / "__init__.py"
LEGACY_PACKAGE_INIT = LEGACY_ARCHIVE_ROOT / "__init__.py"

FORBIDDEN_APP_PATTERNS = (
    r"from lawglance_main import",
    r"\bimport lawglance_main\b",
    r"from chains import",
    r"\bimport chains\b",
    r"from cache import",
    r"\bimport cache\b",
    r"from prompts import",
    r"\bimport prompts\b",
    r"from langchain",
    r"langchain_",
    r"OpenAIEmbeddings",
    r"ChatOpenAI",
    r"Chroma\(",
)

LEGACY_DEPRECATION_FILES = (
    LEGACY_ARCHIVE_ROOT / "lawglance_main.py",
    LEGACY_ARCHIVE_ROOT / "chains.py",
    LEGACY_ARCHIVE_ROOT / "cache.py",
    LEGACY_ARCHIVE_ROOT / "prompts.py",
)


def test_streamlit_app_is_thin_api_client() -> None:
    assert APP_PATH.exists(), f"expected streamlit app at {APP_PATH}"
    app_source = APP_PATH.read_text(encoding="utf-8")
    assert "LegacyApiClient" in app_source
    assert "client.send_chat(" in app_source
    assert "/api/chat" in app_source


def test_streamlit_app_does_not_embed_local_rag_runtime() -> None:
    assert APP_PATH.exists(), f"expected streamlit app at {APP_PATH}"
    app_source = APP_PATH.read_text(encoding="utf-8")
    for pattern in FORBIDDEN_APP_PATTERNS:
        assert re.search(pattern, app_source) is None


def test_root_legacy_modules_are_removed() -> None:
    assert not (REPO_ROOT / "lawglance_main.py").exists()
    assert not (REPO_ROOT / "chains.py").exists()
    assert not (REPO_ROOT / "cache.py").exists()
    assert not (REPO_ROOT / "prompts.py").exists()


def test_root_legacy_module_imports_are_absent_from_root_notebook() -> None:
    assert LEGACY_NOTEBOOK_PATH.exists(), f"expected notebook at {LEGACY_NOTEBOOK_PATH}"
    notebook_source = LEGACY_NOTEBOOK_PATH.read_text(encoding="utf-8")
    for pattern in FORBIDDEN_APP_PATTERNS[:8]:
        assert re.search(pattern, notebook_source) is None


def test_legacy_archive_is_explicit_python_package() -> None:
    assert LEGACY_ROOT_PACKAGE_INIT.exists()
    assert LEGACY_PACKAGE_INIT.exists()


def test_legacy_archive_orchestrator_uses_package_relative_imports() -> None:
    legacy_orchestrator = LEGACY_ARCHIVE_ROOT / "lawglance_main.py"
    assert legacy_orchestrator.exists(), f"expected legacy orchestrator at {legacy_orchestrator}"
    source = legacy_orchestrator.read_text(encoding="utf-8")
    assert "from .cache import RedisCache" in source
    assert "from .chains import get_rag_chain" in source
    assert "from .prompts import SYSTEM_PROMPT, QA_PROMPT" in source
    assert "from cache import RedisCache" not in source
    assert "from chains import get_rag_chain" not in source
    assert "from prompts import SYSTEM_PROMPT, QA_PROMPT" not in source


def test_legacy_archive_orchestrator_module_imports_via_package_path() -> None:
    spec = importlib.util.find_spec("legacy.local_rag.lawglance_main")
    assert spec is not None

    legacy_orchestrator = LEGACY_ARCHIVE_ROOT / "lawglance_main.py"
    assert legacy_orchestrator.exists(), f"expected legacy orchestrator at {legacy_orchestrator}"
    source = legacy_orchestrator.read_text(encoding="utf-8")
    tree = ast.parse(source)
    assert any(
        isinstance(node, ast.ClassDef) and node.name == "Lawglance" for node in tree.body
    )


def test_legacy_modules_are_explicitly_marked_deprecated() -> None:
    for path in LEGACY_DEPRECATION_FILES:
        assert path.exists(), f"expected legacy deprecation file at {path}"
        source = path.read_text(encoding="utf-8")
        assert "deprecated" in source.lower()
