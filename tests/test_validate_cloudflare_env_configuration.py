from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


SCRIPT_PATH = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "validate_cloudflare_env_configuration.py"
)
SPEC = importlib.util.spec_from_file_location(
    "validate_cloudflare_env_configuration", SCRIPT_PATH
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules["validate_cloudflare_env_configuration"] = MODULE
SPEC.loader.exec_module(MODULE)


def test_validate_runtime_env_vars_passes_for_matching_configs() -> None:
    errors = MODULE._validate_runtime_env_vars(
        vars_by_target={
            "frontend": {
                "ENVIRONMENT": "production",
                "IMMCAD_ENVIRONMENT": "production",
            },
            "backend": {
                "ENVIRONMENT": "production",
                "IMMCAD_ENVIRONMENT": "production",
            },
        },
        expected_environment="production",
    )
    assert errors == []


def test_validate_runtime_env_vars_reports_missing_and_mismatched_values() -> None:
    errors = MODULE._validate_runtime_env_vars(
        vars_by_target={
            "frontend": {
                "ENVIRONMENT": "production",
                "IMMCAD_ENVIRONMENT": "development",
            },
            "backend": {
                "ENVIRONMENT": "staging",
            },
        },
        expected_environment="production",
    )

    assert (
        "frontend: ENVIRONMENT and IMMCAD_ENVIRONMENT must match "
        "(got `production` vs `development`)"
    ) in errors
    assert "backend: missing required var `IMMCAD_ENVIRONMENT`" in errors
    assert "backend: ENVIRONMENT must be `production` (got `staging`)" in errors
