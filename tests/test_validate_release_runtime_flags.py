from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "validate_release_runtime_flags.py"
SPEC = importlib.util.spec_from_file_location("validate_release_runtime_flags", SCRIPT_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_validate_env_accepts_prod_safe_ci_flags() -> None:
    MODULE.validate_env(
        {
            "ENVIRONMENT": "ci",
            "API_BEARER_TOKEN": "release-smoke-token",
            "ENABLE_SCAFFOLD_PROVIDER": "false",
            "ALLOW_SCAFFOLD_SYNTHETIC_CITATIONS": "false",
        }
    )


def test_validate_env_rejects_missing_or_unsafe_flags() -> None:
    with pytest.raises(ValueError) as exc_info:
        MODULE.validate_env(
            {
                "ENVIRONMENT": "development",
                "API_BEARER_TOKEN": "",
                "ENABLE_SCAFFOLD_PROVIDER": "true",
                "ALLOW_SCAFFOLD_SYNTHETIC_CITATIONS": "yes",
            }
        )

    message = str(exc_info.value)
    assert "ENVIRONMENT" in message
    assert "API_BEARER_TOKEN" in message
    assert "ENABLE_SCAFFOLD_PROVIDER" in message
    assert "ALLOW_SCAFFOLD_SYNTHETIC_CITATIONS" in message


def test_main_returns_nonzero_and_prints_failures(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "ci")
    monkeypatch.setenv("ENABLE_SCAFFOLD_PROVIDER", "true")
    monkeypatch.delenv("ALLOW_SCAFFOLD_SYNTHETIC_CITATIONS", raising=False)
    monkeypatch.delenv("API_BEARER_TOKEN", raising=False)

    exit_code = MODULE.main()
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "[FAIL]" in captured.out
    assert "API_BEARER_TOKEN" in captured.out
    assert "ENABLE_SCAFFOLD_PROVIDER" in captured.out
