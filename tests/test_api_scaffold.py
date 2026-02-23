from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from immcad_api.main import create_app  # noqa: E402


client = TestClient(create_app())


def test_chat_endpoint_contract_shape() -> None:
    response = client.post(
        "/api/chat",
        json={
            "session_id": "session-123456",
            "message": "What are the basic PR eligibility pathways?",
            "locale": "en-CA",
            "mode": "standard",
        },
    )

    assert response.status_code == 200
    body = response.json()

    assert "answer" in body
    assert "citations" in body
    assert "confidence" in body
    assert "disclaimer" in body
    assert "fallback_used" in body
    assert body["citations"]
    assert "x-trace-id" in response.headers


def test_chat_policy_block_response() -> None:
    response = client.post(
        "/api/chat",
        json={
            "session_id": "session-123456",
            "message": "Please represent me and file my application",
            "locale": "en-CA",
            "mode": "standard",
        },
    )

    assert response.status_code == 200
    body = response.json()

    assert body["citations"] == []
    assert body["fallback_used"]["used"] is False
    assert body["fallback_used"]["reason"] == "policy_block"


def test_case_search_contract_shape() -> None:
    response = client.post(
        "/api/search/cases",
        json={
            "query": "express entry inadmissibility",
            "jurisdiction": "ca",
            "court": "fct",
            "limit": 2,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert "results" in body
    assert len(body["results"]) == 2
    assert "case_id" in body["results"][0]
    assert "url" in body["results"][0]


def test_validation_error_uses_error_envelope() -> None:
    response = client.post(
        "/api/chat",
        json={
            "session_id": "short",
            "message": "",
        },
    )

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert body["error"]["trace_id"]
    assert "x-trace-id" in response.headers


def test_optional_bearer_auth_gate(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("API_BEARER_TOKEN", "secret-token")
    secured_client = TestClient(create_app())

    unauthorized = secured_client.post(
        "/api/chat",
        json={
            "session_id": "session-123456",
            "message": "What is IRPA section 11 about?",
            "locale": "en-CA",
            "mode": "standard",
        },
    )
    assert unauthorized.status_code == 401
    assert unauthorized.json()["error"]["code"] == "UNAUTHORIZED"

    authorized = secured_client.post(
        "/api/chat",
        headers={"Authorization": "Bearer secret-token"},
        json={
            "session_id": "session-123456",
            "message": "What is IRPA section 11 about?",
            "locale": "en-CA",
            "mode": "standard",
        },
    )
    assert authorized.status_code == 200


def test_provider_error_envelope_when_scaffold_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENABLE_SCAFFOLD_PROVIDER", "false")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    provider_error_client = TestClient(create_app())

    response = provider_error_client.post(
        "/api/chat",
        json={
            "session_id": "session-123456",
            "message": "Summarize IRPA section 11.",
            "locale": "en-CA",
            "mode": "standard",
        },
    )

    assert response.status_code == 502
    body = response.json()
    assert body["error"]["code"] == "PROVIDER_ERROR"
    assert body["error"]["trace_id"]


def test_rate_limit_envelope(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("API_RATE_LIMIT_PER_MINUTE", "1")
    throttled_client = TestClient(create_app())

    first = throttled_client.post(
        "/api/chat",
        json={
            "session_id": "session-123456",
            "message": "Explain PR pathways in brief.",
            "locale": "en-CA",
            "mode": "standard",
        },
    )
    second = throttled_client.post(
        "/api/chat",
        json={
            "session_id": "session-123456",
            "message": "Explain PR pathways in brief.",
            "locale": "en-CA",
            "mode": "standard",
        },
    )

    assert first.status_code == 200
    assert second.status_code == 429
    assert second.json()["error"]["code"] == "RATE_LIMITED"
