from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "scan_domain_leaks.py"
SPEC = importlib.util.spec_from_file_location("scan_domain_leaks", SCRIPT_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def test_scan_repository_reports_file_line_and_term(tmp_path: Path) -> None:
    leak_file = tmp_path / "src" / "immcad_api" / "chat.py"
    leak_file.parent.mkdir(parents=True)
    leak_file.write_text("subject = 'Indian Constitution'\n", encoding="utf-8")

    violations, scanned_files = MODULE.scan_repository(
        repo_root=tmp_path,
        scan_paths=("src",),
        allowlist=frozenset(),
    )

    assert scanned_files == 1
    assert len(violations) == 1
    assert violations[0].line_number == 1
    assert violations[0].term == "indian constitution"
    rendered = MODULE.format_violation(violations[0], repo_root=tmp_path)
    assert "src/immcad_api/chat.py:1:" in rendered


def test_scan_repository_respects_allowlist(tmp_path: Path) -> None:
    leak_file = tmp_path / "src" / "immcad_api" / "chat.py"
    leak_file.parent.mkdir(parents=True)
    leak_file.write_text("subject = 'India'\n", encoding="utf-8")

    violations, scanned_files = MODULE.scan_repository(
        repo_root=tmp_path,
        scan_paths=("src",),
        allowlist=frozenset({"src/immcad_api/chat.py"}),
    )

    assert scanned_files == 0
    assert violations == []


def test_main_returns_nonzero_and_prints_context_for_violation(
    tmp_path: Path, capsys
) -> None:
    leak_file = tmp_path / "docs" / "scope.md"
    leak_file.parent.mkdir(parents=True)
    leak_file.write_text("This still references India legal sources.\n", encoding="utf-8")

    exit_code = MODULE.main(
        [
            "--repo-root",
            str(tmp_path),
            "--path",
            "docs",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "docs/scope.md:1:" in captured.out


def test_main_returns_zero_for_clean_paths(tmp_path: Path, capsys) -> None:
    clean_file = tmp_path / "src" / "immcad_api" / "chat.py"
    clean_file.parent.mkdir(parents=True)
    clean_file.write_text("subject = 'Canadian immigration law'\n", encoding="utf-8")

    exit_code = MODULE.main(
        [
            "--repo-root",
            str(tmp_path),
            "--path",
            "src",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "[OK] Domain leak scan passed" in captured.out
