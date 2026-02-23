from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import httpx
import pytest

from immcad_api.errors import ProviderApiError
from immcad_api.schemas import CaseSearchRequest
from immcad_api.sources.canlii_client import CanLIIClient


class _FakeResponse:
    def __init__(self, payload: dict[str, Any], status_ok: bool = True) -> None:
        self._payload = payload
        self._status_ok = status_ok

    def raise_for_status(self) -> None:
        if not self._status_ok:
            raise httpx.HTTPStatusError(
                "error",
                request=httpx.Request("GET", "https://api.canlii.org"),
                response=httpx.Response(500),
            )

    def json(self) -> dict[str, Any]:
        return self._payload


class _FakeClient:
    def __init__(self, *args, **kwargs) -> None:
        self.payload = kwargs.pop("payload", None)
        self.raise_error = kwargs.pop("raise_error", False)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def get(self, *args, **kwargs):
        if self.raise_error:
            raise httpx.ConnectError("connection failed")
        return _FakeResponse(self.payload or {})


def test_canlii_fallback_without_api_key(monkeypatch) -> None:
    # API key is absent, so client should return local fallback without hitting HTTP.
    def _should_not_call_http(*args, **kwargs):  # pragma: no cover - defensive guard
        raise AssertionError("httpx.Client should not be called when api_key is None")

    monkeypatch.setattr("immcad_api.sources.canlii_client.httpx.Client", _should_not_call_http)

    client = CanLIIClient(api_key=None)
    request = CaseSearchRequest(query="inadmissibility", jurisdiction="ca", court="fct", limit=2)

    response = client.search_cases(request)
    assert len(response.results) == 2
    assert response.results[0].url.startswith("https://www.canlii.org/")


def test_canlii_parses_success_payload(monkeypatch) -> None:
    payload = {
        "cases": [
            {
                "caseId": "c1",
                "title": "Case One",
                "citation": "2024 FC 1",
                "decisionDate": "2024-01-08",
                "url": "https://www.canlii.org/c1",
            },
            {
                "databaseId": "c2",
                "title": "Case Two",
                "citation": "2024 FC 2",
                "decisionDate": "2024-01-09T00:00:00Z",
                "url": "https://www.canlii.org/c2",
            },
        ]
    }

    monkeypatch.setattr(
        "immcad_api.sources.canlii_client.httpx.Client",
        lambda *args, **kwargs: _FakeClient(payload=payload),
    )

    client = CanLIIClient(api_key="test-key")
    request = CaseSearchRequest(query="express entry", jurisdiction="ca", court="fct", limit=2)
    response = client.search_cases(request)

    assert len(response.results) == 2
    assert response.results[0].case_id == "c1"
    assert response.results[1].case_id == "c2"
    assert response.results[1].decision_date == date(2024, 1, 9)


def test_canlii_handles_invalid_date(monkeypatch) -> None:
    payload = {
        "cases": [
            {
                "caseId": "c1",
                "title": "Case With Bad Date",
                "citation": "2024 FC 3",
                "decisionDate": "not-a-date",
                "url": "https://www.canlii.org/c3",
            }
        ]
    }
    monkeypatch.setattr(
        "immcad_api.sources.canlii_client.httpx.Client",
        lambda *args, **kwargs: _FakeClient(payload=payload),
    )

    client = CanLIIClient(api_key="test-key")
    request = CaseSearchRequest(query="inadmissibility", jurisdiction="ca", court="fct", limit=1)
    response = client.search_cases(request)

    assert len(response.results) == 1
    today = date.today()
    assert response.results[0].decision_date in {today, today - timedelta(days=1)}


def test_canlii_falls_back_on_http_error(monkeypatch) -> None:
    monkeypatch.setattr(
        "immcad_api.sources.canlii_client.httpx.Client",
        lambda *args, **kwargs: _FakeClient(raise_error=True),
    )

    client = CanLIIClient(api_key="test-key")
    request = CaseSearchRequest(query="inadmissibility", jurisdiction="ca", court="fct", limit=2)
    response = client.search_cases(request)

    assert len(response.results) == 2
    assert response.results[0].case_id.startswith("FCT-")


def test_canlii_raises_without_api_key_when_scaffold_fallback_disabled(monkeypatch) -> None:
    def _should_not_call_http(*args, **kwargs):  # pragma: no cover - defensive guard
        raise AssertionError("httpx.Client should not be called when api_key is None")

    monkeypatch.setattr("immcad_api.sources.canlii_client.httpx.Client", _should_not_call_http)

    client = CanLIIClient(api_key=None, allow_scaffold_fallback=False)
    request = CaseSearchRequest(query="inadmissibility", jurisdiction="ca", court="fct", limit=2)

    with pytest.raises(ProviderApiError, match="Case-law search is currently unavailable"):
        client.search_cases(request)


def test_canlii_raises_on_http_error_when_scaffold_fallback_disabled(monkeypatch) -> None:
    monkeypatch.setattr(
        "immcad_api.sources.canlii_client.httpx.Client",
        lambda *args, **kwargs: _FakeClient(raise_error=True),
    )

    client = CanLIIClient(api_key="test-key", allow_scaffold_fallback=False)
    request = CaseSearchRequest(query="inadmissibility", jurisdiction="ca", court="fct", limit=2)

    with pytest.raises(ProviderApiError, match="Case-law search is currently unavailable"):
        client.search_cases(request)
