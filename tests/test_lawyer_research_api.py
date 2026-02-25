from __future__ import annotations

from datetime import date

import pytest
from fastapi.testclient import TestClient

from immcad_api.errors import RateLimitError
from immcad_api.main import create_app
from immcad_api.schemas import CaseSearchResponse, CaseSearchResult


def test_lawyer_research_endpoint_returns_structured_cases(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _mock_case_search(self, request):
        del self, request
        return CaseSearchResponse(
            results=[
                CaseSearchResult(
                    case_id="2026-FC-101",
                    title="Example v Canada",
                    citation="2026 FC 101",
                    decision_date=date(2026, 2, 1),
                    url="https://decisions.fct-cf.gc.ca/fc-cf/decisions/en/item/123456/index.do",
                    source_id="FC_DECISIONS",
                    document_url="https://decisions.fct-cf.gc.ca/fc-cf/decisions/en/item/123456/index.do",
                )
            ]
        )

    monkeypatch.setattr(
        "immcad_api.services.case_search_service.CaseSearchService.search",
        _mock_case_search,
    )
    client = TestClient(create_app())

    response = client.post(
        "/api/research/lawyer-cases",
        json={
            "session_id": "session-123456",
            "matter_summary": "Federal Court appeal about procedural fairness and inadmissibility",
            "jurisdiction": "ca",
            "court": "fc",
            "limit": 3,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["cases"]
    assert body["cases"][0]["citation"] == "2026 FC 101"
    assert body["cases"][0]["pdf_status"] == "available"
    assert body["cases"][0]["source_id"] == "FC_DECISIONS"
    assert body["source_status"]["official"] == "ok"
    assert response.headers["x-trace-id"]


def test_lawyer_research_endpoint_returns_disabled_envelope_when_case_search_off(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENABLE_CASE_SEARCH", "false")
    client = TestClient(create_app())

    response = client.post(
        "/api/research/lawyer-cases",
        json={
            "session_id": "session-123456",
            "matter_summary": "Federal Court appeal on procedural fairness",
            "jurisdiction": "ca",
            "limit": 3,
        },
    )

    assert response.status_code == 503
    body = response.json()
    assert body["error"]["code"] == "SOURCE_UNAVAILABLE"
    assert body["error"]["policy_reason"] == "case_search_disabled"
    assert response.headers["x-trace-id"] == body["error"]["trace_id"]


def test_lawyer_research_endpoint_rejects_broad_stopword_query() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/api/research/lawyer-cases",
        json={
            "session_id": "session-123456",
            "matter_summary": "and the or to be",
            "jurisdiction": "ca",
            "limit": 3,
        },
    )

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert body["error"]["policy_reason"] == "case_search_query_too_broad"
    assert response.headers["x-trace-id"] == body["error"]["trace_id"]


def test_lawyer_research_endpoint_handles_long_matter_summary_without_internal_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed_queries: list[str] = []

    def _mock_case_search(self, request):
        del self
        observed_queries.append(request.query)
        return CaseSearchResponse(results=[])

    monkeypatch.setattr(
        "immcad_api.services.case_search_service.CaseSearchService.search",
        _mock_case_search,
    )
    client = TestClient(create_app())
    long_summary = "Federal Court procedural fairness " + ("inadmissibility " * 120)

    response = client.post(
        "/api/research/lawyer-cases",
        json={
            "session_id": "session-123456",
            "matter_summary": long_summary,
            "jurisdiction": "ca",
            "court": "fc",
            "limit": 5,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["source_status"]["official"] == "no_match"
    assert observed_queries
    assert all(len(query) <= 300 for query in observed_queries)


def test_lawyer_research_endpoint_returns_rate_limited_envelope(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _rate_limited_search(self, request):
        del self, request
        raise RateLimitError("CanLII per-second request limit reached. Please retry shortly.")

    monkeypatch.setattr(
        "immcad_api.services.case_search_service.CaseSearchService.search",
        _rate_limited_search,
    )
    client = TestClient(create_app())

    response = client.post(
        "/api/research/lawyer-cases",
        json={
            "session_id": "session-123456",
            "matter_summary": "Federal Court inadmissibility appeal decision",
            "jurisdiction": "ca",
            "court": "fc",
            "limit": 3,
        },
    )

    assert response.status_code == 429
    body = response.json()
    assert body["error"]["code"] == "RATE_LIMITED"
    assert "retry" in body["error"]["message"].lower()
    assert response.headers["x-trace-id"] == body["error"]["trace_id"]
