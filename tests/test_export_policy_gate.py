from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from immcad_api.main import create_app  # noqa: E402


def _build_client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.delenv("API_BEARER_TOKEN", raising=False)
    return TestClient(create_app())


def test_case_export_policy_allows_official_source(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _build_client(monkeypatch)

    response = client.post(
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
    assert "x-trace-id" in response.headers


def test_case_export_policy_blocks_source_when_export_disallowed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = _build_client(monkeypatch)

    response = client.post(
        "/api/export/cases",
        json={
            "source_id": "CANLII_TERMS",
            "case_id": "terms-reference",
            "format": "pdf",
        },
    )

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "POLICY_BLOCKED"
    assert body["error"]["policy_reason"] == "source_export_blocked_by_policy"
    assert body["error"]["trace_id"]
    assert response.headers["x-trace-id"] == body["error"]["trace_id"]


def test_case_export_policy_blocks_unknown_source_with_policy_reason(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = _build_client(monkeypatch)

    response = client.post(
        "/api/export/cases",
        json={
            "source_id": "UNKNOWN_SOURCE",
            "case_id": "doc-123",
            "format": "pdf",
        },
    )

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "POLICY_BLOCKED"
    assert body["error"]["policy_reason"] == "source_not_in_policy_for_export"
    assert body["error"]["trace_id"]
    assert response.headers["x-trace-id"] == body["error"]["trace_id"]
