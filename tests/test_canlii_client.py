from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import httpx
import pytest

from immcad_api.errors import ProviderApiError, RateLimitError
from immcad_api.schemas import CaseSearchRequest
from immcad_api.sources.canlii_client import CanLIIClient
from immcad_api.sources.canlii_usage_limiter import CanLIIUsageLimitExceeded


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
    created_clients: list["_FakeClient"] = []

    def __init__(self, *args, **kwargs) -> None:
        self.payload = kwargs.pop("payload", None)
        self.raise_error = kwargs.pop("raise_error", False)
        self.init_kwargs = kwargs
        self.last_get_args = ()
        self.last_get_kwargs: dict[str, Any] = {}
        _FakeClient.created_clients.append(self)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def get(self, *args, **kwargs):
        self.last_get_args = args
        self.last_get_kwargs = kwargs
        if self.raise_error:
            raise httpx.ConnectError("connection failed")
        return _FakeResponse(self.payload or {})

    @classmethod
    def reset(cls) -> None:
        cls.created_clients = []


class _AlwaysLimitedLimiter:
    def __init__(self, reason: str) -> None:
        self.reason = reason

    def acquire(self):
        raise CanLIIUsageLimitExceeded(self.reason)


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
    assert response.results[0].source_id == "CANLII_CASE_BROWSE"
    assert response.results[0].document_url == response.results[0].url


def test_canlii_parses_success_payload(monkeypatch) -> None:
    _FakeClient.reset()
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
                "databaseId": "onca",
                "caseId": {"en": "c2"},
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
    request = CaseSearchRequest(query="case", jurisdiction="ca", court="fct", limit=2)
    response = client.search_cases(request)

    assert len(response.results) == 2
    assert response.results[0].case_id == "c1"
    assert response.results[1].case_id == "c2"
    assert response.results[1].decision_date == date(2024, 1, 9)
    assert response.results[0].source_id == "CANLII_CASE_BROWSE"
    assert response.results[0].document_url == "https://www.canlii.org/c1"


def test_canlii_handles_invalid_date(monkeypatch) -> None:
    _FakeClient.reset()
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
    request = CaseSearchRequest(query="case", jurisdiction="ca", court="fct", limit=1)
    response = client.search_cases(request)

    assert len(response.results) == 1
    today = date.today()
    assert response.results[0].decision_date in {today, today - timedelta(days=1)}


def test_canlii_falls_back_on_http_error(monkeypatch) -> None:
    _FakeClient.reset()
    monkeypatch.setattr(
        "immcad_api.sources.canlii_client.httpx.Client",
        lambda *args, **kwargs: _FakeClient(raise_error=True),
    )

    client = CanLIIClient(api_key="test-key")
    request = CaseSearchRequest(query="inadmissibility", jurisdiction="ca", court="fct", limit=2)
    response = client.search_cases(request)

    assert len(response.results) == 2
    assert response.results[0].case_id.startswith("FCT-")


def test_canlii_uses_api_key_query_parameter(monkeypatch) -> None:
    _FakeClient.reset()
    payload = {
        "cases": [
            {
                "databaseId": "fct",
                "caseId": {"en": "fct-1"},
                "title": "Case One",
                "citation": "2024 FC 1",
                "decisionDate": "2024-01-08",
            }
        ]
    }
    monkeypatch.setattr(
        "immcad_api.sources.canlii_client.httpx.Client",
        lambda *args, **kwargs: _FakeClient(payload=payload),
    )

    client = CanLIIClient(api_key="test-key")
    request = CaseSearchRequest(query="case", jurisdiction="ca", court="fct", limit=1)
    response = client.search_cases(request)

    assert len(response.results) == 1
    assert _FakeClient.created_clients, "Expected a CanLII HTTP client to be created."
    used_client = _FakeClient.created_clients[-1]
    assert used_client.last_get_kwargs.get("params", {}).get("api_key") == "test-key"
    assert "Authorization" not in (used_client.init_kwargs.get("headers") or {})


@pytest.mark.parametrize(
    ("court_alias", "expected_database"),
    [
        ("fc", "fct"),
        ("fca-caf", "fca"),
        ("supreme court of canada", "scc"),
    ],
)
def test_canlii_maps_official_court_aliases_to_database_ids(
    monkeypatch, court_alias: str, expected_database: str
) -> None:
    _FakeClient.reset()
    monkeypatch.setattr(
        "immcad_api.sources.canlii_client.httpx.Client",
        lambda *args, **kwargs: _FakeClient(payload={"cases": []}),
    )

    client = CanLIIClient(api_key="test-key")
    request = CaseSearchRequest(query="immigration", jurisdiction="ca", court=court_alias, limit=1)
    _ = client.search_cases(request)

    used_client = _FakeClient.created_clients[-1]
    endpoint = used_client.last_get_args[0]
    assert endpoint.endswith(f"/caseBrowse/en/{expected_database}/")


def test_canlii_returns_empty_results_when_query_tokens_do_not_match(monkeypatch) -> None:
    _FakeClient.reset()
    payload = {
        "cases": [
            {
                "caseId": "c1",
                "title": "Cadogan v Canada (Citizenship and Immigration)",
                "citation": "2025 FC 1125",
                "decisionDate": "2025-06-23",
                "url": "https://www.canlii.org/c1",
            }
        ]
    }
    monkeypatch.setattr(
        "immcad_api.sources.canlii_client.httpx.Client",
        lambda *args, **kwargs: _FakeClient(payload=payload),
    )

    client = CanLIIClient(api_key="test-key")
    request = CaseSearchRequest(query="oi", jurisdiction="ca", court="fct", limit=5)
    response = client.search_cases(request)

    assert response.results == []


def test_canlii_returns_empty_results_for_long_unmatched_query(monkeypatch) -> None:
    _FakeClient.reset()
    payload = {
        "cases": [
            {
                "caseId": "c1",
                "title": "Cadogan v Canada (Citizenship and Immigration)",
                "citation": "2025 FC 1125",
                "decisionDate": "2025-06-23",
                "url": "https://www.canlii.org/c1",
            }
        ]
    }
    monkeypatch.setattr(
        "immcad_api.sources.canlii_client.httpx.Client",
        lambda *args, **kwargs: _FakeClient(payload=payload),
    )

    client = CanLIIClient(api_key="test-key")
    request = CaseSearchRequest(
        query="completely unrelated maritime insurance dispute",
        jurisdiction="ca",
        court="fct",
        limit=5,
    )
    response = client.search_cases(request)

    assert response.results == []


def test_canlii_filters_results_by_decision_date_range(monkeypatch) -> None:
    _FakeClient.reset()
    payload = {
        "cases": [
            {
                "caseId": "c-old",
                "title": "Older Decision",
                "citation": "2023 FC 7",
                "decisionDate": "2023-02-01",
                "url": "https://www.canlii.org/c-old",
            },
            {
                "caseId": "c-new",
                "title": "Newer Decision",
                "citation": "2025 FC 17",
                "decisionDate": "2025-06-01",
                "url": "https://www.canlii.org/c-new",
            },
        ]
    }
    monkeypatch.setattr(
        "immcad_api.sources.canlii_client.httpx.Client",
        lambda *args, **kwargs: _FakeClient(payload=payload),
    )

    client = CanLIIClient(api_key="test-key")
    request = CaseSearchRequest(
        query="decision",
        jurisdiction="ca",
        court="fct",
        limit=5,
        decision_date_from=date(2024, 1, 1),
        decision_date_to=date(2025, 12, 31),
    )
    response = client.search_cases(request)

    assert len(response.results) == 1
    assert response.results[0].case_id == "c-new"


def test_canlii_returns_rate_limited_when_daily_limit_hit() -> None:
    client = CanLIIClient(
        api_key="test-key",
        usage_limiter=_AlwaysLimitedLimiter("daily_limit"),
    )
    request = CaseSearchRequest(query="inadmissibility", jurisdiction="ca", court="fct", limit=2)

    with pytest.raises(RateLimitError) as exc_info:
        client.search_cases(request)

    assert exc_info.value.code == "RATE_LIMITED"
    assert exc_info.value.status_code == 429
    assert "daily quota" in exc_info.value.message.lower()


def test_canlii_raises_without_api_key_when_scaffold_fallback_disabled(monkeypatch) -> None:
    def _should_not_call_http(*args, **kwargs):  # pragma: no cover - defensive guard
        raise AssertionError("httpx.Client should not be called when api_key is None")

    monkeypatch.setattr("immcad_api.sources.canlii_client.httpx.Client", _should_not_call_http)

    client = CanLIIClient(api_key=None, allow_scaffold_fallback=False)
    request = CaseSearchRequest(query="inadmissibility", jurisdiction="ca", court="fct", limit=2)

    with pytest.raises(ProviderApiError, match="Case-law source is currently unavailable") as exc_info:
        client.search_cases(request)

    assert exc_info.value.code == "SOURCE_UNAVAILABLE"
    assert exc_info.value.status_code == 503


def test_canlii_raises_on_http_error_when_scaffold_fallback_disabled(monkeypatch) -> None:
    monkeypatch.setattr(
        "immcad_api.sources.canlii_client.httpx.Client",
        lambda *args, **kwargs: _FakeClient(raise_error=True),
    )

    client = CanLIIClient(api_key="test-key", allow_scaffold_fallback=False)
    request = CaseSearchRequest(query="inadmissibility", jurisdiction="ca", court="fct", limit=2)

    with pytest.raises(ProviderApiError, match="Case-law source is currently unavailable") as exc_info:
        client.search_cases(request)

    assert exc_info.value.code == "SOURCE_UNAVAILABLE"
    assert exc_info.value.status_code == 503
