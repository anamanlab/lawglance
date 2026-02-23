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
