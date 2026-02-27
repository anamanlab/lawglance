from __future__ import annotations

import pytest

from immcad_api.settings import load_settings


def _set_hardened_env(
    monkeypatch: pytest.MonkeyPatch,
    environment: str,
) -> None:
    monkeypatch.setenv("ENVIRONMENT", environment)
    monkeypatch.setenv("IMMCAD_API_BEARER_TOKEN", "secret-token")
    monkeypatch.setenv("API_BEARER_TOKEN", "secret-token")
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
    monkeypatch.setenv("CANLII_API_KEY", "test-canlii-key")
    monkeypatch.setenv("ENABLE_SCAFFOLD_PROVIDER", "false")
    monkeypatch.setenv("ALLOW_SCAFFOLD_SYNTHETIC_CITATIONS", "false")
    monkeypatch.setenv("CITATION_TRUSTED_DOMAINS", "laws-lois.justice.gc.ca,canlii.org")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-2.5-flash-lite")
    monkeypatch.setenv("GEMINI_MODEL_FALLBACKS", "gemini-2.5-flash")


def _set_hardened_env_without_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    monkeypatch.setenv("IMMCAD_API_BEARER_TOKEN", "secret-token")
    monkeypatch.setenv("API_BEARER_TOKEN", "secret-token")
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
    monkeypatch.setenv("CANLII_API_KEY", "test-canlii-key")
    monkeypatch.setenv("ENABLE_SCAFFOLD_PROVIDER", "false")
    monkeypatch.setenv("ALLOW_SCAFFOLD_SYNTHETIC_CITATIONS", "false")
    monkeypatch.setenv("CITATION_TRUSTED_DOMAINS", "laws-lois.justice.gc.ca,canlii.org")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-2.5-flash-lite")
    monkeypatch.setenv("GEMINI_MODEL_FALLBACKS", "gemini-2.5-flash")


@pytest.mark.parametrize("environment", ["production", "prod", "ci"])
def test_load_settings_requires_bearer_token_in_production(
    monkeypatch: pytest.MonkeyPatch,
    environment: str,
) -> None:
    _set_hardened_env(monkeypatch, environment)
    monkeypatch.delenv("API_BEARER_TOKEN", raising=False)
    monkeypatch.delenv("IMMCAD_API_BEARER_TOKEN", raising=False)

    with pytest.raises(ValueError, match="IMMCAD_API_BEARER_TOKEN is required"):
        load_settings()


@pytest.mark.parametrize("environment", ["production-us-east", "prod_blue", "ci-smoke"])
def test_load_settings_treats_environment_variants_as_hardened(
    monkeypatch: pytest.MonkeyPatch,
    environment: str,
) -> None:
    _set_hardened_env(monkeypatch, environment)
    monkeypatch.delenv("API_BEARER_TOKEN", raising=False)
    monkeypatch.delenv("IMMCAD_API_BEARER_TOKEN", raising=False)

    with pytest.raises(ValueError, match="IMMCAD_API_BEARER_TOKEN is required"):
        load_settings()


@pytest.mark.parametrize("environment", ["production-us-east", "prod_blue", "ci-smoke"])
def test_load_settings_supports_immcad_environment_alias(
    monkeypatch: pytest.MonkeyPatch,
    environment: str,
) -> None:
    _set_hardened_env_without_environment(monkeypatch)
    monkeypatch.setenv("IMMCAD_ENVIRONMENT", environment)

    settings = load_settings()

    assert settings.environment == environment


def test_load_settings_rejects_mismatched_environment_aliases(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("IMMCAD_ENVIRONMENT", "development")

    with pytest.raises(
        ValueError,
        match="ENVIRONMENT and IMMCAD_ENVIRONMENT must match when both are set",
    ):
        load_settings()


def test_load_settings_defaults_to_production_when_vercel_env_is_production(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_hardened_env_without_environment(monkeypatch)
    monkeypatch.setenv("VERCEL_ENV", "production")

    settings = load_settings()

    assert settings.environment == "production"


def test_load_settings_defaults_to_production_when_node_env_is_production(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_hardened_env_without_environment(monkeypatch)
    monkeypatch.setenv("NODE_ENV", "production")

    settings = load_settings()

    assert settings.environment == "production"


def test_load_settings_prefers_explicit_environment_over_node_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_hardened_env_without_environment(monkeypatch)
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("IMMCAD_ENVIRONMENT", "development")
    monkeypatch.setenv("NODE_ENV", "production")
    monkeypatch.delenv("VERCEL_ENV", raising=False)

    settings = load_settings()

    assert settings.environment == "development"


def test_load_settings_requires_hardened_guards_when_vercel_env_is_production(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_hardened_env_without_environment(monkeypatch)
    monkeypatch.setenv("VERCEL_ENV", "production")
    monkeypatch.delenv("API_BEARER_TOKEN", raising=False)
    monkeypatch.delenv("IMMCAD_API_BEARER_TOKEN", raising=False)

    with pytest.raises(ValueError, match="IMMCAD_API_BEARER_TOKEN is required"):
        load_settings()


def test_load_settings_requires_hardened_guards_when_node_env_is_production(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_hardened_env_without_environment(monkeypatch)
    monkeypatch.setenv("NODE_ENV", "production")
    monkeypatch.delenv("API_BEARER_TOKEN", raising=False)
    monkeypatch.delenv("IMMCAD_API_BEARER_TOKEN", raising=False)

    with pytest.raises(ValueError, match="IMMCAD_API_BEARER_TOKEN is required"):
        load_settings()


def test_load_settings_accepts_canonical_bearer_token_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_hardened_env(monkeypatch, "production")
    monkeypatch.delenv("API_BEARER_TOKEN", raising=False)
    monkeypatch.setenv("IMMCAD_API_BEARER_TOKEN", "secret-token")

    settings = load_settings()

    assert settings.api_bearer_token == "secret-token"


def test_load_settings_rejects_mismatched_bearer_token_aliases(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("IMMCAD_API_BEARER_TOKEN", "token-a")
    monkeypatch.setenv("API_BEARER_TOKEN", "token-b")

    with pytest.raises(
        ValueError,
        match="IMMCAD_API_BEARER_TOKEN and API_BEARER_TOKEN must match when both are set",
    ):
        load_settings()


def test_load_settings_allows_missing_bearer_token_in_development(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.delenv("API_BEARER_TOKEN", raising=False)
    monkeypatch.delenv("IMMCAD_API_BEARER_TOKEN", raising=False)

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


def test_load_settings_defaults_document_https_requirement_to_false_in_development(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.delenv("DOCUMENT_REQUIRE_HTTPS", raising=False)

    settings = load_settings()
    assert settings.document_require_https is False


@pytest.mark.parametrize("environment", ["production", "prod", "ci"])
def test_load_settings_defaults_document_https_requirement_to_true_in_hardened_modes(
    monkeypatch: pytest.MonkeyPatch,
    environment: str,
) -> None:
    _set_hardened_env(monkeypatch, environment)
    monkeypatch.delenv("DOCUMENT_REQUIRE_HTTPS", raising=False)

    settings = load_settings()
    assert settings.document_require_https is True


@pytest.mark.parametrize("environment", ["production", "prod", "ci"])
def test_load_settings_rejects_document_https_disabled_in_hardened_modes(
    monkeypatch: pytest.MonkeyPatch,
    environment: str,
) -> None:
    _set_hardened_env(monkeypatch, environment)
    monkeypatch.setenv("DOCUMENT_REQUIRE_HTTPS", "false")

    with pytest.raises(ValueError, match="DOCUMENT_REQUIRE_HTTPS must be true"):
        load_settings()


def test_load_settings_defaults_to_in_memory_rate_limiter_when_redis_url_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.delenv("REDIS_URL", raising=False)

    settings = load_settings()
    assert settings.redis_url == ""


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
    assert "decisions.scc-csc.ca" in settings.citation_trusted_domains
    assert "decisions.fct-cf.gc.ca" in settings.citation_trusted_domains
    assert "decisions.fca-caf.gc.ca" in settings.citation_trusted_domains


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
    monkeypatch.setenv("IMMCAD_API_BEARER_TOKEN", " secret-token ")
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
    assert settings.gemini_model == "gemini-2.5-flash-lite"
    assert settings.gemini_model_fallbacks == ("gemini-2.5-flash",)


def test_load_settings_excludes_primary_model_from_fallbacks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-2.5-flash")
    monkeypatch.setenv(
        "GEMINI_MODEL_FALLBACKS",
        "gemini-2.5-flash, gemini-2.5-flash-lite",
    )

    settings = load_settings()
    assert settings.gemini_model_fallbacks == ("gemini-2.5-flash-lite",)


@pytest.mark.parametrize("environment", ["production", "prod", "ci"])
def test_load_settings_requires_explicit_gemini_model_in_hardened_modes(
    monkeypatch: pytest.MonkeyPatch,
    environment: str,
) -> None:
    _set_hardened_env(monkeypatch, environment)
    monkeypatch.delenv("GEMINI_MODEL", raising=False)

    with pytest.raises(ValueError, match="GEMINI_MODEL must be explicitly set"):
        load_settings()


@pytest.mark.parametrize("environment", ["production", "prod", "ci"])
def test_load_settings_rejects_unstable_gemini_model_in_hardened_modes(
    monkeypatch: pytest.MonkeyPatch,
    environment: str,
) -> None:
    _set_hardened_env(monkeypatch, environment)
    monkeypatch.setenv("GEMINI_MODEL", "gemini-3-flash-preview")

    with pytest.raises(ValueError, match="GEMINI_MODEL must use a stable Gemini model"):
        load_settings()


@pytest.mark.parametrize("environment", ["production", "prod", "ci"])
def test_load_settings_rejects_unstable_gemini_fallback_models_in_hardened_modes(
    monkeypatch: pytest.MonkeyPatch,
    environment: str,
) -> None:
    _set_hardened_env(monkeypatch, environment)
    monkeypatch.setenv("GEMINI_MODEL", "gemini-2.5-flash")
    monkeypatch.setenv("GEMINI_MODEL_FALLBACKS", "gemini-3-flash-preview")

    with pytest.raises(
        ValueError,
        match="GEMINI_MODEL_FALLBACKS must use stable Gemini models",
    ):
        load_settings()


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
def test_load_settings_allows_missing_canlii_key_with_official_sources_in_hardened_modes(
    monkeypatch: pytest.MonkeyPatch,
    environment: str,
) -> None:
    _set_hardened_env(monkeypatch, environment)
    monkeypatch.delenv("CANLII_API_KEY", raising=False)
    monkeypatch.delenv("ENABLE_OFFICIAL_CASE_SOURCES", raising=False)

    settings = load_settings()
    assert settings.enable_official_case_sources is True
    assert settings.canlii_api_key is None


def test_load_settings_disables_official_case_sources_by_default_in_development(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.delenv("ENABLE_OFFICIAL_CASE_SOURCES", raising=False)

    settings = load_settings()
    assert settings.enable_official_case_sources is False


def test_load_settings_disables_official_only_case_results_by_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.delenv("CASE_SEARCH_OFFICIAL_ONLY_RESULTS", raising=False)

    settings = load_settings()
    assert settings.case_search_official_only_results is False


def test_load_settings_enables_official_only_case_results_when_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("CASE_SEARCH_OFFICIAL_ONLY_RESULTS", "true")

    settings = load_settings()
    assert settings.case_search_official_only_results is True


@pytest.mark.parametrize("environment", ["production", "prod", "ci"])
def test_load_settings_enables_official_only_case_results_by_default_in_hardened_modes(
    monkeypatch: pytest.MonkeyPatch,
    environment: str,
) -> None:
    _set_hardened_env(monkeypatch, environment)
    monkeypatch.delenv("CASE_SEARCH_OFFICIAL_ONLY_RESULTS", raising=False)

    settings = load_settings()
    assert settings.case_search_official_only_results is True


@pytest.mark.parametrize("environment", ["production", "prod", "ci"])
def test_load_settings_rejects_non_official_only_case_results_in_hardened_modes(
    monkeypatch: pytest.MonkeyPatch,
    environment: str,
) -> None:
    _set_hardened_env(monkeypatch, environment)
    monkeypatch.setenv("CASE_SEARCH_OFFICIAL_ONLY_RESULTS", "false")

    with pytest.raises(ValueError, match="CASE_SEARCH_OFFICIAL_ONLY_RESULTS must be true"):
        load_settings()


def test_load_settings_has_default_official_case_cache_ttls(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.delenv("OFFICIAL_CASE_CACHE_TTL_SECONDS", raising=False)
    monkeypatch.delenv("OFFICIAL_CASE_STALE_CACHE_TTL_SECONDS", raising=False)

    settings = load_settings()

    assert settings.official_case_cache_ttl_seconds == 300.0
    assert settings.official_case_stale_cache_ttl_seconds == 900.0


def test_load_settings_rejects_non_positive_official_case_cache_ttl(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("OFFICIAL_CASE_CACHE_TTL_SECONDS", "0")

    with pytest.raises(ValueError, match="OFFICIAL_CASE_CACHE_TTL_SECONDS must be > 0"):
        load_settings()


def test_load_settings_rejects_stale_ttl_shorter_than_fresh_ttl(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("OFFICIAL_CASE_CACHE_TTL_SECONDS", "120")
    monkeypatch.setenv("OFFICIAL_CASE_STALE_CACHE_TTL_SECONDS", "60")

    with pytest.raises(
        ValueError,
        match="OFFICIAL_CASE_STALE_CACHE_TTL_SECONDS must be >= OFFICIAL_CASE_CACHE_TTL_SECONDS",
    ):
        load_settings()


@pytest.mark.parametrize("environment", ["production", "prod", "ci"])
def test_load_settings_requires_case_search_backend_in_hardened_modes(
    monkeypatch: pytest.MonkeyPatch,
    environment: str,
) -> None:
    _set_hardened_env(monkeypatch, environment)
    monkeypatch.delenv("CANLII_API_KEY", raising=False)
    monkeypatch.setenv("ENABLE_OFFICIAL_CASE_SOURCES", "false")

    with pytest.raises(ValueError, match="Either CANLII_API_KEY or ENABLE_OFFICIAL_CASE_SOURCES=true is required"):
        load_settings()


@pytest.mark.parametrize("environment", ["production", "prod", "ci"])
def test_load_settings_allows_missing_canlii_key_when_case_search_disabled(
    monkeypatch: pytest.MonkeyPatch,
    environment: str,
) -> None:
    _set_hardened_env(monkeypatch, environment)
    monkeypatch.delenv("CANLII_API_KEY", raising=False)
    monkeypatch.setenv("ENABLE_CASE_SEARCH", "false")

    settings = load_settings()
    assert settings.enable_case_search is False


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
