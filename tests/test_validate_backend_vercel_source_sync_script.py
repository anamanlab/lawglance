from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


SCRIPT_PATH = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "validate_backend_vercel_source_sync.py"
)
SPEC = importlib.util.spec_from_file_location(
    "validate_backend_vercel_source_sync", SCRIPT_PATH
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules["validate_backend_vercel_source_sync"] = MODULE
SPEC.loader.exec_module(MODULE)


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_compare_source_trees_passes_with_matching_mapped_files(tmp_path: Path) -> None:
    primary_root = tmp_path / "src" / "immcad_api"
    deploy_root = tmp_path / "backend-vercel" / "src" / "immcad_api"
    _write(primary_root / "module.py", "VALUE = 1\n")
    _write(deploy_root / "module.py", "VALUE = 1\n")

    primary_policy = tmp_path / "config" / "source_policy.yaml"
    deploy_policy = tmp_path / "backend-vercel" / "config" / "source_policy.yaml"
    _write(primary_policy, "version: test\n")
    _write(deploy_policy, "version: test\n")

    result = MODULE.compare_source_trees(
        primary_root=primary_root,
        deploy_root=deploy_root,
        mapped_file_pairs=((primary_policy, deploy_policy),),
    )

    assert result.is_synced is True
    assert result.mapped_mismatched == ()


def test_compare_source_trees_detects_mapped_file_mismatch(tmp_path: Path) -> None:
    primary_root = tmp_path / "src" / "immcad_api"
    deploy_root = tmp_path / "backend-vercel" / "src" / "immcad_api"
    _write(primary_root / "module.py", "VALUE = 1\n")
    _write(deploy_root / "module.py", "VALUE = 1\n")

    primary_policy = tmp_path / "config" / "source_policy.yaml"
    deploy_policy = tmp_path / "backend-vercel" / "config" / "source_policy.yaml"
    _write(primary_policy, "version: 2026-02-25\n")
    _write(deploy_policy, "version: 2026-02-24\n")

    result = MODULE.compare_source_trees(
        primary_root=primary_root,
        deploy_root=deploy_root,
        mapped_file_pairs=((primary_policy, deploy_policy),),
    )

    assert result.is_synced is False
    assert result.mapped_mismatched == (
        f"{primary_policy.as_posix()} <-> {deploy_policy.as_posix()}",
    )


def test_compare_source_trees_detects_missing_mapped_deploy_file(tmp_path: Path) -> None:
    primary_root = tmp_path / "src" / "immcad_api"
    deploy_root = tmp_path / "backend-vercel" / "src" / "immcad_api"
    _write(primary_root / "module.py", "VALUE = 1\n")
    _write(deploy_root / "module.py", "VALUE = 1\n")

    primary_policy = tmp_path / "config" / "source_policy.yaml"
    deploy_policy = tmp_path / "backend-vercel" / "config" / "source_policy.yaml"
    _write(primary_policy, "version: 2026-02-25\n")

    result = MODULE.compare_source_trees(
        primary_root=primary_root,
        deploy_root=deploy_root,
        mapped_file_pairs=((primary_policy, deploy_policy),),
    )

    assert result.is_synced is False
    assert result.missing_mapped_deploy == (deploy_policy.as_posix(),)
