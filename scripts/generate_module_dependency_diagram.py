#!/usr/bin/env python3
"""Generate a Mermaid module dependency diagram from project Python imports."""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TARGET_DIR = ROOT / "docs" / "architecture" / "diagrams"
TARGET_FILE = TARGET_DIR / "generated-module-dependencies.mmd"

LEGACY_ROOT_FILES = {"app.py", "lawglance_main.py", "chains.py", "cache.py", "prompts.py"}


def module_name_from_path(path: Path) -> str:
    relative = path.relative_to(ROOT)
    if relative.parts[0] == "src":
        parts = list(relative.with_suffix("").parts[1:])
        if parts and parts[-1] == "__init__":
            parts = parts[:-1]
        return ".".join(parts)
    return path.stem


def collect_import_edges(py_file: Path, known_modules: set[str]) -> set[tuple[str, str]]:
    tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
    src = module_name_from_path(py_file)
    edges: set[tuple[str, str]] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported = alias.name
                if imported in known_modules and imported != src:
                    edges.add((src, imported))
                else:
                    top = imported.split(".", 1)[0]
                    matches = sorted(
                        mod
                        for mod in known_modules
                        if mod == top or mod.startswith(f"{top}.")
                    )
                    for match in matches[:1]:
                        if match != src:
                            edges.add((src, match))
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imported = node.module
                if imported in known_modules and imported != src:
                    edges.add((src, imported))
                else:
                    top = imported.split(".", 1)[0]
                    matches = sorted(
                        mod
                        for mod in known_modules
                        if mod == top or mod.startswith(f"{top}.")
                    )
                    for match in matches[:1]:
                        if match != src:
                            edges.add((src, match))

    return edges


def main() -> None:
    legacy_files = [ROOT / file_name for file_name in LEGACY_ROOT_FILES if (ROOT / file_name).exists()]
    api_files = [
        path
        for path in (ROOT / "src").rglob("*.py")
        if "__pycache__" not in path.parts
    ]
    py_files = sorted(legacy_files + api_files)
    known_modules = {module_name_from_path(path) for path in py_files}

    edges: set[tuple[str, str]] = set()
    for py_file in py_files:
        edges |= collect_import_edges(py_file, known_modules)

    TARGET_DIR.mkdir(parents=True, exist_ok=True)

    lines = [
        "%% AUTO-GENERATED. DO NOT EDIT DIRECTLY.",
        "graph TD",
    ]

    if not edges:
        lines.append("    no_deps[\"No internal module dependencies detected\"]")
    else:
        for src, dst in sorted(edges):
            lines.append(f"    {src} --> {dst}")

    TARGET_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Generated {TARGET_FILE.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
