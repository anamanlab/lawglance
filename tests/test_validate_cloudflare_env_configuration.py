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


def test_validate_cloud_only_defaults_passes_for_cloudflare_native_baseline() -> None:
    errors = MODULE._validate_cloud_only_defaults(
        frontend_wrangler_path=Path("frontend-web/wrangler.jsonc"),
        frontend_vars={
            "IMMCAD_API_BASE_URL": "https://immcad-backend-native-python.example.workers.dev",
        },
        backend_wrangler_path=Path("backend-cloudflare/wrangler.toml"),
        backend_vars={
            "ENABLE_SCAFFOLD_PROVIDER": "false",
            "ALLOW_SCAFFOLD_SYNTHETIC_CITATIONS": "false",
            "ENABLE_OPENAI_PROVIDER": "false",
            "PRIMARY_PROVIDER": "gemini",
            "ENABLE_CASE_SEARCH": "true",
            "ENABLE_OFFICIAL_CASE_SOURCES": "true",
            "CASE_SEARCH_OFFICIAL_ONLY_RESULTS": "true",
            "EXPORT_POLICY_GATE_ENABLED": "true",
            "DOCUMENT_REQUIRE_HTTPS": "true",
            "GEMINI_MODEL": "gemini-2.5-flash-lite",
            "CITATION_TRUSTED_DOMAINS": "laws-lois.justice.gc.ca,canlii.org",
        },
    )
    assert errors == []


def test_validate_cloud_only_defaults_accepts_custom_https_domain() -> None:
    errors = MODULE._validate_cloud_only_defaults(
        frontend_wrangler_path=Path("frontend-web/wrangler.jsonc"),
        frontend_vars={
            "IMMCAD_API_BASE_URL": "https://api.immcad.example.ca",
        },
        backend_wrangler_path=Path("backend-cloudflare/wrangler.toml"),
        backend_vars={
            "ENABLE_SCAFFOLD_PROVIDER": "false",
            "ALLOW_SCAFFOLD_SYNTHETIC_CITATIONS": "false",
            "ENABLE_OPENAI_PROVIDER": "false",
            "PRIMARY_PROVIDER": "gemini",
            "ENABLE_CASE_SEARCH": "true",
            "ENABLE_OFFICIAL_CASE_SOURCES": "true",
            "CASE_SEARCH_OFFICIAL_ONLY_RESULTS": "true",
            "EXPORT_POLICY_GATE_ENABLED": "true",
            "DOCUMENT_REQUIRE_HTTPS": "true",
            "GEMINI_MODEL": "gemini-2.5-flash-lite",
            "CITATION_TRUSTED_DOMAINS": "laws-lois.justice.gc.ca,canlii.org",
        },
    )
    assert errors == []


def test_validate_cloud_only_defaults_reports_legacy_or_unsafe_config() -> None:
    errors = MODULE._validate_cloud_only_defaults(
        frontend_wrangler_path=Path("frontend-web/wrangler.jsonc"),
        frontend_vars={
            "IMMCAD_API_BASE_URL": "http://backend-vercel.example.vercel.app",
            "IMMCAD_API_BASE_URL_FALLBACK": "https://legacy.vercel.app",
        },
        backend_wrangler_path=Path("backend-cloudflare/wrangler.toml"),
        backend_vars={
            "ENABLE_SCAFFOLD_PROVIDER": "true",
            "ALLOW_SCAFFOLD_SYNTHETIC_CITATIONS": "true",
            "ENABLE_OPENAI_PROVIDER": "true",
            "PRIMARY_PROVIDER": "openai",
            "ENABLE_CASE_SEARCH": "true",
            "ENABLE_OFFICIAL_CASE_SOURCES": "true",
            "CASE_SEARCH_OFFICIAL_ONLY_RESULTS": "false",
            "EXPORT_POLICY_GATE_ENABLED": "false",
            "DOCUMENT_REQUIRE_HTTPS": "false",
            "GEMINI_MODEL": "",
            "CITATION_TRUSTED_DOMAINS": "",
        },
    )

    def _contains(snippet: str) -> bool:
        return any(snippet in error for error in errors)

    assert _contains(
        "IMMCAD_API_BASE_URL must start with `https://` "
        "(got `http://backend-vercel.example.vercel.app`)"
    )
    assert _contains(
        "IMMCAD_API_BASE_URL_FALLBACK must be unset for cloud-only production baseline"
    )
    assert _contains("missing required var `GEMINI_MODEL`")
    assert _contains("missing required var `CITATION_TRUSTED_DOMAINS`")
    assert _contains(
        "ENABLE_SCAFFOLD_PROVIDER must be `false` for cloud-only production baseline (got `true`)"
    )
    assert _contains(
        "ENABLE_OPENAI_PROVIDER must be `false` for cloud-only production baseline (got `true`)"
    )
    assert _contains(
        "PRIMARY_PROVIDER must be `gemini` for cloud-only production baseline (got `openai`)"
    )
