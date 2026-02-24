from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from immcad_api.main import create_app  # noqa: E402


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.delenv("API_BEARER_TOKEN", raising=False)
    monkeypatch.delenv("EXPORT_POLICY_GATE_ENABLED", raising=False)
    return TestClient(create_app())


@pytest.fixture
def policy_gate_client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.delenv("API_BEARER_TOKEN", raising=False)
    monkeypatch.setenv("EXPORT_POLICY_GATE_ENABLED", "true")
    return TestClient(create_app())


def test_case_export_policy_gate_disabled_uses_legacy_behavior(client: TestClient) -> None:
    response = client.post(
        "/api/export/cases",
        json={
            "source_id": "CANLII_TERMS",
            "case_id": "terms-reference",
            "format": "pdf",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["source_id"] == "CANLII_TERMS"
    assert body["case_id"] == "terms-reference"
    assert body["format"] == "pdf"
    assert body["export_allowed"] is True
    assert body["policy_reason"] is None
    assert response.headers.get("x-trace-id", "").strip() != ""


def test_case_export_policy_allows_official_source_when_gate_enabled(
    policy_gate_client: TestClient,
) -> None:
    response = policy_gate_client.post(
        "/api/export/cases",
        json={
            "source_id": "SCC_DECISIONS",
            "case_id": "scc-2024-3",
            "format": "pdf",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["source_id"] == "SCC_DECISIONS"
    assert body["case_id"] == "scc-2024-3"
    assert body["format"] == "pdf"
    assert body["export_allowed"] is True
    assert body["policy_reason"] == "source_export_allowed"
    assert response.headers.get("x-trace-id", "").strip() != ""


def test_case_export_policy_blocks_source_when_export_disallowed(
    policy_gate_client: TestClient,
) -> None:
    response = policy_gate_client.post(
        "/api/export/cases",
        json={
            "source_id": "CANLII_TERMS",
            "case_id": "terms-reference",
            "format": "pdf",
        },
    )

    assert response.status_code == 403
    body = response.json()
    assert body["error"]["code"] == "POLICY_BLOCKED"
    assert body["error"]["policy_reason"] == "source_export_blocked_by_policy"
    trace_id = body["error"]["trace_id"]
    assert isinstance(trace_id, str)
    assert trace_id.strip() != ""
    response_trace_id = response.headers.get("x-trace-id")
    assert response_trace_id is not None
    assert response_trace_id == trace_id


def test_case_export_policy_blocks_unknown_source_with_policy_reason(
    policy_gate_client: TestClient,
) -> None:
    response = policy_gate_client.post(
        "/api/export/cases",
        json={
            "source_id": "UNKNOWN_SOURCE",
            "case_id": "doc-123",
            "format": "pdf",
        },
    )

    assert response.status_code == 403
    body = response.json()
    assert body["error"]["code"] == "POLICY_BLOCKED"
    assert body["error"]["policy_reason"] == "source_not_in_policy_for_export"
    trace_id = body["error"]["trace_id"]
    assert isinstance(trace_id, str)
    assert trace_id.strip() != ""
    response_trace_id = response.headers.get("x-trace-id")
    assert response_trace_id is not None
    assert response_trace_id == trace_id
