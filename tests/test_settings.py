from __future__ import annotations

import pytest

from immcad_api.settings import load_settings


def _set_hardened_env(
    monkeypatch: pytest.MonkeyPatch,
    environment: str,
) -> None:
    monkeypatch.setenv("ENVIRONMENT", environment)
    monkeypatch.setenv("API_BEARER_TOKEN", "secret-token")
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
    monkeypatch.setenv("CANLII_API_KEY", "test-canlii-key")
    monkeypatch.setenv("ENABLE_SCAFFOLD_PROVIDER", "false")
    monkeypatch.setenv("ALLOW_SCAFFOLD_SYNTHETIC_CITATIONS", "false")
    monkeypatch.setenv("CITATION_TRUSTED_DOMAINS", "laws-lois.justice.gc.ca,canlii.org")


def _set_hardened_env_without_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    monkeypatch.setenv("API_BEARER_TOKEN", "secret-token")
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
    monkeypatch.setenv("CANLII_API_KEY", "test-canlii-key")
    monkeypatch.setenv("ENABLE_SCAFFOLD_PROVIDER", "false")
    monkeypatch.setenv("ALLOW_SCAFFOLD_SYNTHETIC_CITATIONS", "false")
    monkeypatch.setenv("CITATION_TRUSTED_DOMAINS", "laws-lois.justice.gc.ca,canlii.org")


@pytest.mark.parametrize("environment", ["production", "prod", "ci"])
def test_load_settings_requires_bearer_token_in_production(
    monkeypatch: pytest.MonkeyPatch,
    environment: str,
) -> None:
    _set_hardened_env(monkeypatch, environment)
    monkeypatch.delenv("API_BEARER_TOKEN", raising=False)

    with pytest.raises(ValueError, match="API_BEARER_TOKEN is required"):
        load_settings()


def test_load_settings_defaults_to_production_when_vercel_env_is_production(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_hardened_env_without_environment(monkeypatch)
    monkeypatch.setenv("VERCEL_ENV", "production")

    settings = load_settings()

    assert settings.environment == "production"


def test_load_settings_requires_hardened_guards_when_vercel_env_is_production(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_hardened_env_without_environment(monkeypatch)
    monkeypatch.setenv("VERCEL_ENV", "production")
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


def test_load_settings_has_circuit_breaker_defaults(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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
    _set_hardened_env(monkeypatch, environment)
    monkeypatch.setenv("ALLOW_SCAFFOLD_SYNTHETIC_CITATIONS", "true")

    with pytest.raises(
        ValueError, match="ALLOW_SCAFFOLD_SYNTHETIC_CITATIONS must be false"
    ):
        load_settings()


def test_load_settings_allows_disabled_synthetic_citations_in_production(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_hardened_env(monkeypatch, "production")

    settings = load_settings()
    assert settings.allow_scaffold_synthetic_citations is False


@pytest.mark.parametrize("environment", ["production", "prod", "ci"])
def test_load_settings_requires_explicit_trusted_domains_in_hardened_modes(
    monkeypatch: pytest.MonkeyPatch,
    environment: str,
) -> None:
    _set_hardened_env(monkeypatch, environment)
    monkeypatch.delenv("CITATION_TRUSTED_DOMAINS", raising=False)

    with pytest.raises(
        ValueError, match="CITATION_TRUSTED_DOMAINS must be explicitly set"
    ):
        load_settings()


@pytest.mark.parametrize("environment", ["production", "prod", "ci"])
def test_load_settings_rejects_empty_parsed_trusted_domains_in_hardened_modes(
    monkeypatch: pytest.MonkeyPatch,
    environment: str,
) -> None:
    _set_hardened_env(monkeypatch, environment)
    monkeypatch.setenv("CITATION_TRUSTED_DOMAINS", ",,")

    with pytest.raises(
        ValueError,
        match="CITATION_TRUSTED_DOMAINS must define at least one trusted domain",
    ):
        load_settings()


def test_load_settings_has_default_cors_origins(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.delenv("CORS_ALLOWED_ORIGINS", raising=False)

    settings = load_settings()
    assert settings.cors_allowed_origins == (
        "http://127.0.0.1:3000",
        "http://localhost:3000",
    )


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


def test_load_settings_has_default_trusted_citation_domains(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.delenv("CITATION_TRUSTED_DOMAINS", raising=False)

    settings = load_settings()
    assert "laws-lois.justice.gc.ca" in settings.citation_trusted_domains
    assert "canlii.org" in settings.citation_trusted_domains


def test_load_settings_parses_trusted_citation_domains_csv(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv(
        "CITATION_TRUSTED_DOMAINS",
        "laws-lois.justice.gc.ca,canlii.org,",
    )

    settings = load_settings()
    assert settings.citation_trusted_domains == (
        "laws-lois.justice.gc.ca",
        "canlii.org",
    )


def test_load_settings_trims_sensitive_env_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_hardened_env(monkeypatch, "production")
    monkeypatch.setenv("ENVIRONMENT", " production ")
    monkeypatch.setenv("API_BEARER_TOKEN", " secret-token ")
    monkeypatch.setenv("CITATION_TRUSTED_DOMAINS", " laws-lois.justice.gc.ca,canlii.org ")
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
    assert settings.gemini_model_fallbacks == (
        "gemini-2.5-flash",
        "gemini-2.5-flash-lite",
    )


def test_load_settings_primary_provider_defaults(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.delenv("PRIMARY_PROVIDER", raising=False)

    settings = load_settings()
    assert settings.primary_provider == "openai"
    assert settings.enable_openai_provider is True


def test_load_settings_accepts_gemini_primary_and_openai_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("PRIMARY_PROVIDER", "gemini")
    monkeypatch.setenv("ENABLE_OPENAI_PROVIDER", "false")

    settings = load_settings()
    assert settings.primary_provider == "gemini"
    assert settings.enable_openai_provider is False


def test_load_settings_rejects_invalid_primary_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("PRIMARY_PROVIDER", "unknown")

    with pytest.raises(ValueError, match="PRIMARY_PROVIDER must be one of"):
        load_settings()


def test_load_settings_rejects_openai_primary_when_openai_provider_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("PRIMARY_PROVIDER", "openai")
    monkeypatch.setenv("ENABLE_OPENAI_PROVIDER", "false")

    with pytest.raises(
        ValueError, match="PRIMARY_PROVIDER=openai requires ENABLE_OPENAI_PROVIDER=true"
    ):
        load_settings()


def test_load_settings_defaults_export_policy_gate_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.delenv("EXPORT_POLICY_GATE_ENABLED", raising=False)

    settings = load_settings()
    assert settings.export_policy_gate_enabled is False


@pytest.mark.parametrize("environment", ["production", "prod", "ci"])
def test_load_settings_defaults_export_policy_gate_enabled_in_hardened_modes(
    monkeypatch: pytest.MonkeyPatch,
    environment: str,
) -> None:
    _set_hardened_env(monkeypatch, environment)
    monkeypatch.delenv("EXPORT_POLICY_GATE_ENABLED", raising=False)

    settings = load_settings()
    assert settings.export_policy_gate_enabled is True


@pytest.mark.parametrize("environment", ["production", "prod", "ci"])
def test_load_settings_rejects_disabled_export_policy_gate_in_hardened_modes(
    monkeypatch: pytest.MonkeyPatch,
    environment: str,
) -> None:
    _set_hardened_env(monkeypatch, environment)
    monkeypatch.setenv("EXPORT_POLICY_GATE_ENABLED", "false")

    with pytest.raises(ValueError, match="EXPORT_POLICY_GATE_ENABLED must be true"):
        load_settings()


def test_load_settings_has_default_export_max_download_bytes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.delenv("EXPORT_MAX_DOWNLOAD_BYTES", raising=False)

    settings = load_settings()
    assert settings.export_max_download_bytes == 10 * 1024 * 1024


def test_load_settings_rejects_non_positive_export_max_download_bytes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("EXPORT_MAX_DOWNLOAD_BYTES", "0")

    with pytest.raises(ValueError, match="EXPORT_MAX_DOWNLOAD_BYTES must be >= 1"):
        load_settings()


@pytest.mark.parametrize("environment", ["production", "prod", "ci"])
def test_load_settings_requires_gemini_key_in_hardened_modes(
    monkeypatch: pytest.MonkeyPatch,
    environment: str,
) -> None:
    _set_hardened_env(monkeypatch, environment)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    with pytest.raises(ValueError, match="GEMINI_API_KEY is required"):
        load_settings()


@pytest.mark.parametrize("environment", ["production", "prod", "ci"])
def test_load_settings_requires_canlii_key_in_hardened_modes(
    monkeypatch: pytest.MonkeyPatch,
    environment: str,
) -> None:
    _set_hardened_env(monkeypatch, environment)
    monkeypatch.delenv("CANLII_API_KEY", raising=False)

    with pytest.raises(ValueError, match="CANLII_API_KEY is required"):
        load_settings()


@pytest.mark.parametrize("environment", ["production", "prod", "ci"])
def test_load_settings_requires_openai_key_when_openai_enabled_in_hardened_modes(
    monkeypatch: pytest.MonkeyPatch,
    environment: str,
) -> None:
    _set_hardened_env(monkeypatch, environment)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(ValueError, match="OPENAI_API_KEY is required"):
        load_settings()


@pytest.mark.parametrize("environment", ["production", "prod", "ci"])
def test_load_settings_rejects_scaffold_provider_in_hardened_modes(
    monkeypatch: pytest.MonkeyPatch,
    environment: str,
) -> None:
    _set_hardened_env(monkeypatch, environment)
    monkeypatch.setenv("ENABLE_SCAFFOLD_PROVIDER", "true")

    with pytest.raises(ValueError, match="ENABLE_SCAFFOLD_PROVIDER must be false"):
        load_settings()


@pytest.mark.parametrize("environment", ["production", "prod", "ci"])
def test_load_settings_rejects_scaffold_primary_in_hardened_modes(
    monkeypatch: pytest.MonkeyPatch,
    environment: str,
) -> None:
    _set_hardened_env(monkeypatch, environment)
    monkeypatch.setenv("PRIMARY_PROVIDER", "scaffold")

    with pytest.raises(ValueError, match="PRIMARY_PROVIDER cannot be scaffold"):
        load_settings()
