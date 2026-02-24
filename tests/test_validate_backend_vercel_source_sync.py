from __future__ import annotations

from pathlib import Path

from scripts.validate_backend_vercel_source_sync import compare_source_trees


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_compare_source_trees_reports_synced_python_files(tmp_path: Path) -> None:
    primary = tmp_path / "src" / "immcad_api"
    deploy = tmp_path / "backend-vercel" / "src" / "immcad_api"

    _write(primary / "a.py", "print('a')\n")
    _write(primary / "nested" / "b.py", "print('b')\n")
    _write(deploy / "a.py", "print('a')\n")
    _write(deploy / "nested" / "b.py", "print('b')\n")

    result = compare_source_trees(primary_root=primary, deploy_root=deploy)

    assert result.is_synced is True
    assert result.missing_in_deploy == ()
    assert result.extra_in_deploy == ()
    assert result.mismatched == ()


def test_compare_source_trees_reports_missing_extra_and_mismatch(tmp_path: Path) -> None:
    primary = tmp_path / "src" / "immcad_api"
    deploy = tmp_path / "backend-vercel" / "src" / "immcad_api"

    _write(primary / "shared.py", "print('primary')\n")
    _write(primary / "missing.py", "print('only-primary')\n")
    _write(deploy / "shared.py", "print('deploy')\n")
    _write(deploy / "extra.py", "print('only-deploy')\n")

    result = compare_source_trees(primary_root=primary, deploy_root=deploy)

    assert result.is_synced is False
    assert result.missing_in_deploy == ("missing.py",)
    assert result.extra_in_deploy == ("extra.py",)
    assert result.mismatched == ("shared.py",)
