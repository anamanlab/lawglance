from __future__ import annotations

import pytest

from immcad_api.settings import load_settings


@pytest.mark.parametrize("environment", ["production", "prod", "ci"])
def test_load_settings_requires_bearer_token_in_production(
    monkeypatch: pytest.MonkeyPatch,
    environment: str,
) -> None:
    monkeypatch.setenv("ENVIRONMENT", environment)
    monkeypatch.delenv("API_BEARER_TOKEN", raising=False)

    with pytest.raises(ValueError, match="API_BEARER_TOKEN is required"):
        load_settings()


def test_load_settings_allows_missing_bearer_token_in_development(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.delenv("API_BEARER_TOKEN", raising=False)

    settings = load_settings()
    assert settings.api_bearer_token is None


def test_load_settings_has_circuit_breaker_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.delenv("PROVIDER_CIRCUIT_BREAKER_FAILURE_THRESHOLD", raising=False)
    monkeypatch.delenv("PROVIDER_CIRCUIT_BREAKER_OPEN_SECONDS", raising=False)

    settings = load_settings()
    assert settings.provider_circuit_breaker_failure_threshold == 3
    assert settings.provider_circuit_breaker_open_seconds == 30.0


@pytest.mark.parametrize("environment", ["production", "prod", "ci"])
def test_load_settings_rejects_synthetic_citations_in_hardened_modes(
    monkeypatch: pytest.MonkeyPatch,
    environment: str,
) -> None:
    monkeypatch.setenv("ENVIRONMENT", environment)
    monkeypatch.setenv("API_BEARER_TOKEN", "secret-token")
    monkeypatch.setenv("ALLOW_SCAFFOLD_SYNTHETIC_CITATIONS", "true")

    with pytest.raises(ValueError, match="ALLOW_SCAFFOLD_SYNTHETIC_CITATIONS must be false"):
        load_settings()


def test_load_settings_allows_disabled_synthetic_citations_in_production(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("API_BEARER_TOKEN", "secret-token")
    monkeypatch.setenv("ALLOW_SCAFFOLD_SYNTHETIC_CITATIONS", "false")

    settings = load_settings()
    assert settings.allow_scaffold_synthetic_citations is False


def test_load_settings_has_default_cors_origins(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.delenv("CORS_ALLOWED_ORIGINS", raising=False)

    settings = load_settings()
    assert settings.cors_allowed_origins == ("http://127.0.0.1:3000", "http://localhost:3000")


def test_load_settings_parses_cors_origins_csv(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv(
        "CORS_ALLOWED_ORIGINS",
        "https://immcad.example, https://admin.immcad.example ,, ",
    )

    settings = load_settings()
    assert settings.cors_allowed_origins == (
        "https://immcad.example",
        "https://admin.immcad.example",
    )


def test_load_settings_trims_sensitive_env_values(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", " production ")
    monkeypatch.setenv("API_BEARER_TOKEN", " secret-token ")
    monkeypatch.setenv("ALLOW_SCAFFOLD_SYNTHETIC_CITATIONS", "false")

    settings = load_settings()
    assert settings.environment == "production"
    assert settings.api_bearer_token == "secret-token"


def test_load_settings_uses_latest_gemini_default_with_stable_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.delenv("GEMINI_MODEL", raising=False)
    monkeypatch.delenv("GEMINI_MODEL_FALLBACKS", raising=False)

    settings = load_settings()
    assert settings.gemini_model == "gemini-3-flash-preview"
    assert settings.gemini_model_fallbacks == ("gemini-2.5-flash",)


def test_load_settings_excludes_primary_model_from_fallbacks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-3-flash-preview")
    monkeypatch.setenv(
        "GEMINI_MODEL_FALLBACKS",
        "gemini-3-flash-preview, gemini-2.5-flash, gemini-2.5-flash-lite",
    )

    settings = load_settings()
    assert settings.gemini_model_fallbacks == ("gemini-2.5-flash", "gemini-2.5-flash-lite")
