from __future__ import annotations

import pytest

from immcad_api.settings import load_settings


def test_load_settings_requires_bearer_token_in_production(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
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


def test_load_settings_rejects_synthetic_citations_in_production(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
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
