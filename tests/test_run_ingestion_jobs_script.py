from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import pytest


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "run_ingestion_jobs.py"
SPEC = importlib.util.spec_from_file_location("run_ingestion_jobs_script", SCRIPT_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules["run_ingestion_jobs_script"] = MODULE
SPEC.loader.exec_module(MODULE)


def test_resolve_default_runtime_environment_uses_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production-us-east")
    monkeypatch.delenv("IMMCAD_ENVIRONMENT", raising=False)

    resolved = MODULE.resolve_default_runtime_environment()

    assert resolved == "production-us-east"


def test_resolve_default_runtime_environment_uses_immcad_alias(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    monkeypatch.setenv("IMMCAD_ENVIRONMENT", "prod_blue")

    resolved = MODULE.resolve_default_runtime_environment()

    assert resolved == "prod_blue"


def test_resolve_default_runtime_environment_rejects_mismatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("IMMCAD_ENVIRONMENT", "development")

    with pytest.raises(
        ValueError,
        match="ENVIRONMENT and IMMCAD_ENVIRONMENT must match when both are set",
    ):
        MODULE.resolve_default_runtime_environment()


def test_parse_args_supports_repeated_source_id(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_ingestion_jobs.py",
            "--source-id",
            "SRC_DAILY",
            "--source-id",
            "SRC_WEEKLY",
        ],
    )

    args = MODULE.parse_args()

    assert args.source_id == ["SRC_DAILY", "SRC_WEEKLY"]
