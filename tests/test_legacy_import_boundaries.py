from __future__ import annotations

from pathlib import Path
import re

REPO_ROOT = Path(__file__).resolve().parents[1]
SCAN_ROOTS = (
    REPO_ROOT / "src",
    REPO_ROOT / "scripts",
    REPO_ROOT / "tests",
    REPO_ROOT / "app.py",
    REPO_ROOT / "legacy_api_client.py",
)
LEGACY_MODULES = ("cache", "chains", "lawglance_main", "prompts")
LEGACY_IMPORT_PATTERNS = tuple(
    re.compile(rf"^\s*(?:from|import)\s+{module}\b", re.MULTILINE) for module in LEGACY_MODULES
)


def _iter_python_files() -> list[Path]:
    files: list[Path] = []
    for root in SCAN_ROOTS:
        if not root.exists():
            continue
        if root.is_file() and root.suffix == ".py":
            files.append(root)
            continue
        if root.is_dir():
            files.extend(sorted(path for path in root.rglob("*.py") if path.is_file()))
    return files


def test_active_codepaths_do_not_import_legacy_modules() -> None:
    violations: list[str] = []
    for file_path in _iter_python_files():
        source = file_path.read_text(encoding="utf-8")
        relative = file_path.relative_to(REPO_ROOT).as_posix()
        for pattern in LEGACY_IMPORT_PATTERNS:
            for match in pattern.finditer(source):
                statement = match.group(0).strip()
                violations.append(f"{relative}: {statement}")

    assert not violations, (
        "Legacy module imports are not allowed in active codepaths:\n"
        + "\n".join(violations)
    )
