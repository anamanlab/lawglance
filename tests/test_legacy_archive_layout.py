from __future__ import annotations

import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
LEGACY_ARCHIVE_ROOT = REPO_ROOT / "legacy" / "local_rag"
LEGACY_ROOT_PACKAGE_INIT = REPO_ROOT / "legacy" / "__init__.py"
LEGACY_PACKAGE_INIT = LEGACY_ARCHIVE_ROOT / "__init__.py"

LEGACY_DEPRECATION_FILES = (
    LEGACY_ARCHIVE_ROOT / "lawglance_main.py",
    LEGACY_ARCHIVE_ROOT / "chains.py",
    LEGACY_ARCHIVE_ROOT / "cache.py",
    LEGACY_ARCHIVE_ROOT / "prompts.py",
)


def test_root_legacy_modules_are_removed() -> None:
    assert not (REPO_ROOT / "lawglance_main.py").exists()
    assert not (REPO_ROOT / "chains.py").exists()
    assert not (REPO_ROOT / "cache.py").exists()
    assert not (REPO_ROOT / "prompts.py").exists()


def test_legacy_archive_is_explicit_python_package() -> None:
    assert LEGACY_ROOT_PACKAGE_INIT.exists()
    assert LEGACY_PACKAGE_INIT.exists()


def test_legacy_archive_orchestrator_uses_package_relative_imports() -> None:
    source = (LEGACY_ARCHIVE_ROOT / "lawglance_main.py").read_text(encoding="utf-8")
    assert "from .cache import RedisCache" in source
    assert "from .chains import get_rag_chain" in source
    assert "from .prompts import SYSTEM_PROMPT, QA_PROMPT" in source


def test_legacy_archive_orchestrator_module_has_lawglance_class() -> None:
    module_path = LEGACY_ARCHIVE_ROOT / "lawglance_main.py"
    assert module_path.exists()

    source = module_path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    assert any(
        isinstance(node, ast.ClassDef) and node.name == "Lawglance" for node in tree.body
    )


def test_legacy_modules_are_marked_deprecated() -> None:
    for path in LEGACY_DEPRECATION_FILES:
        source = path.read_text(encoding="utf-8")
        assert "deprecated" in source.lower()
