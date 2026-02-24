from __future__ import annotations

import sys
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from immcad_api.main import create_app  # noqa: E402


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    calls: list[str] = []

    def fake_get(url: str, *, timeout: float, follow_redirects: bool) -> httpx.Response:
        del timeout, follow_redirects
        calls.append(url)
        request = httpx.Request("GET", url)
        return httpx.Response(
            status_code=200,
            content=b"%PDF-1.7\nfake-pdf\n",
            headers={"content-type": "application/pdf"},
            request=request,
        )

    monkeypatch.setattr("immcad_api.api.routes.cases.httpx.get", fake_get)
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.delenv("API_BEARER_TOKEN", raising=False)
    monkeypatch.delenv("EXPORT_POLICY_GATE_ENABLED", raising=False)
    test_client = TestClient(create_app())
    test_client._download_calls = calls  # type: ignore[attr-defined]
    return test_client


@pytest.fixture
def policy_gate_client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    calls: list[str] = []

    def fake_get(url: str, *, timeout: float, follow_redirects: bool) -> httpx.Response:
        del timeout, follow_redirects
        calls.append(url)
        request = httpx.Request("GET", url)
        return httpx.Response(
            status_code=200,
            content=b"%PDF-1.7\nfake-pdf\n",
            headers={"content-type": "application/pdf"},
            request=request,
        )

    monkeypatch.setattr("immcad_api.api.routes.cases.httpx.get", fake_get)
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.delenv("API_BEARER_TOKEN", raising=False)
    monkeypatch.setenv("EXPORT_POLICY_GATE_ENABLED", "true")
    test_client = TestClient(create_app())
    test_client._download_calls = calls  # type: ignore[attr-defined]
    return test_client


def test_case_export_policy_gate_disabled_downloads_document_even_for_blocked_source(
    client: TestClient,
) -> None:
    response = client.post(
        "/api/export/cases",
        json={
            "source_id": "CANLII_TERMS",
            "case_id": "terms-reference",
            "document_url": "https://www.canlii.org/en/ca/scc/doc/2024/2024scc3/2024scc3.html",
            "format": "pdf",
        },
    )

    assert response.status_code == 200
    assert response.content.startswith(b"%PDF-1.7")
    assert response.headers.get("content-type", "").startswith("application/pdf")
    assert response.headers.get("content-disposition", "").endswith(
        '"CANLII_TERMS-terms-reference.pdf"'
    )
    assert response.headers.get("x-export-policy-reason") == "source_export_allowed_gate_disabled"
    assert response.headers.get("x-trace-id", "").strip() != ""
    assert getattr(client, "_download_calls") == [
        "https://www.canlii.org/en/ca/scc/doc/2024/2024scc3/2024scc3.html"
    ]


def test_case_export_policy_allows_official_source_and_downloads_when_gate_enabled(
    policy_gate_client: TestClient,
) -> None:
    response = policy_gate_client.post(
        "/api/export/cases",
        json={
            "source_id": "SCC_DECISIONS",
            "case_id": "scc-2024-3",
            "document_url": "https://decisions.scc-csc.ca/scc-csc/scc-csc/en/item/123/index.do",
            "format": "pdf",
        },
    )

    assert response.status_code == 200
    assert response.content.startswith(b"%PDF-1.7")
    assert response.headers.get("x-export-policy-reason") == "source_export_allowed"
    assert response.headers.get("content-disposition", "").endswith(
        '"SCC_DECISIONS-scc-2024-3.pdf"'
    )
    assert response.headers.get("x-trace-id", "").strip() != ""
    assert getattr(policy_gate_client, "_download_calls") == [
        "https://decisions.scc-csc.ca/scc-csc/scc-csc/en/item/123/index.do"
    ]


def test_case_export_policy_blocks_source_when_export_disallowed(
    policy_gate_client: TestClient,
) -> None:
    response = policy_gate_client.post(
        "/api/export/cases",
        json={
            "source_id": "CANLII_TERMS",
            "case_id": "terms-reference",
            "document_url": "https://www.canlii.org/en/ca/scc/doc/2024/2024scc3/2024scc3.html",
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
    assert getattr(policy_gate_client, "_download_calls") == []


def test_case_export_policy_blocks_unknown_source_with_policy_reason(
    policy_gate_client: TestClient,
) -> None:
    response = policy_gate_client.post(
        "/api/export/cases",
        json={
            "source_id": "UNKNOWN_SOURCE",
            "case_id": "doc-123",
            "document_url": "https://example.com/file.pdf",
            "format": "pdf",
        },
    )

    assert response.status_code == 403
    body = response.json()
    assert body["error"]["code"] == "POLICY_BLOCKED"
    assert body["error"]["policy_reason"] == "source_not_in_registry_for_export"
    trace_id = body["error"]["trace_id"]
    assert isinstance(trace_id, str)
    assert trace_id.strip() != ""
    response_trace_id = response.headers.get("x-trace-id")
    assert response_trace_id is not None
    assert response_trace_id == trace_id
    assert getattr(policy_gate_client, "_download_calls") == []


def test_case_export_policy_rejects_document_url_host_not_matching_source(
    policy_gate_client: TestClient,
) -> None:
    response = policy_gate_client.post(
        "/api/export/cases",
        json={
            "source_id": "SCC_DECISIONS",
            "case_id": "scc-2024-3",
            "document_url": "https://example.com/file.pdf",
            "format": "pdf",
        },
    )

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert body["error"]["policy_reason"] == "export_url_not_allowed_for_source"
    assert getattr(policy_gate_client, "_download_calls") == []


def test_case_export_policy_rejects_redirected_document_host_not_matching_source(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    def fake_get(url: str, *, timeout: float, follow_redirects: bool) -> httpx.Response:
        del timeout, follow_redirects
        calls.append(url)
        # Simulate final redirected URL landing on an untrusted host.
        request = httpx.Request("GET", "https://evil.example/file.pdf")
        return httpx.Response(
            status_code=200,
            content=b"%PDF-1.7\nfake-pdf\n",
            headers={"content-type": "application/pdf"},
            request=request,
        )

    monkeypatch.setattr("immcad_api.api.routes.cases.httpx.get", fake_get)
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.delenv("API_BEARER_TOKEN", raising=False)
    monkeypatch.setenv("EXPORT_POLICY_GATE_ENABLED", "true")

    client = TestClient(create_app())
    response = client.post(
        "/api/export/cases",
        json={
            "source_id": "SCC_DECISIONS",
            "case_id": "scc-2024-3",
            "document_url": "https://decisions.scc-csc.ca/scc-csc/scc-csc/en/item/123/index.do",
            "format": "pdf",
        },
    )

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert body["error"]["policy_reason"] == "export_redirect_url_not_allowed_for_source"
    assert calls == ["https://decisions.scc-csc.ca/scc-csc/scc-csc/en/item/123/index.do"]
