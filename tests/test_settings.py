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


def test_load_settings_enables_scaffold_citations_in_development_by_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.delenv("ALLOW_SCAFFOLD_SYNTHETIC_CITATIONS", raising=False)

    settings = load_settings()
    assert settings.allow_scaffold_synthetic_citations is True


def test_load_settings_rejects_scaffold_citations_in_production(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("API_BEARER_TOKEN", "token")
    monkeypatch.setenv("ALLOW_SCAFFOLD_SYNTHETIC_CITATIONS", "true")

    with pytest.raises(
        ValueError,
        match="ALLOW_SCAFFOLD_SYNTHETIC_CITATIONS must be disabled",
    ):
        load_settings()


def test_load_settings_has_chat_grounding_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.delenv("ENABLE_CHAT_GROUNDING", raising=False)
    monkeypatch.delenv("CHAT_RETRIEVER_BACKEND", raising=False)
    monkeypatch.delenv("CHAT_GROUNDING_TOP_K", raising=False)

    settings = load_settings()

    assert settings.enable_chat_grounding is False
    assert settings.chat_retriever_backend == "none"
    assert settings.chat_grounding_top_k == 3


def test_load_settings_rejects_invalid_chat_grounding_top_k(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("CHAT_GROUNDING_TOP_K", "0")

    with pytest.raises(ValueError, match="CHAT_GROUNDING_TOP_K must be >= 1"):
        load_settings()


def test_load_settings_rejects_unknown_chat_retriever_backend(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("CHAT_RETRIEVER_BACKEND", "elastic")

    with pytest.raises(ValueError, match="CHAT_RETRIEVER_BACKEND must be one of"):
        load_settings()
