from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from immcad_api.api.routes import cases as cases_routes  # noqa: E402
from immcad_api.main import create_app  # noqa: E402


def _set_hardened_export_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production-us-east")
    monkeypatch.setenv("IMMCAD_API_BEARER_TOKEN", "secret-token")
    monkeypatch.setenv("API_BEARER_TOKEN", "secret-token")
    monkeypatch.setenv("ENABLE_SCAFFOLD_PROVIDER", "false")
    monkeypatch.setenv("ALLOW_SCAFFOLD_SYNTHETIC_CITATIONS", "false")
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-2.5-flash-lite")
    monkeypatch.setenv("GEMINI_MODEL_FALLBACKS", "gemini-2.5-flash")
    monkeypatch.setenv(
        "CITATION_TRUSTED_DOMAINS",
        "laws-lois.justice.gc.ca,canlii.org,decisions.scc-csc.ca,decisions.fct-cf.gc.ca,decisions.fca-caf.gc.ca",
    )
    monkeypatch.setenv("EXPORT_POLICY_GATE_ENABLED", "true")


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    download_calls: list[tuple[str, int]] = []

    def fake_download_export_payload(*, request_url: str, max_download_bytes: int):
        download_calls.append((request_url, max_download_bytes))
        return (b"%PDF-1.7\nfake-pdf\n", "application/pdf", request_url)

    monkeypatch.setattr(
        cases_routes, "_download_export_payload", fake_download_export_payload
    )
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.delenv("IMMCAD_API_BEARER_TOKEN", raising=False)
    monkeypatch.delenv("API_BEARER_TOKEN", raising=False)
    monkeypatch.delenv("EXPORT_POLICY_GATE_ENABLED", raising=False)
    test_client = TestClient(create_app())
    test_client._download_calls = download_calls  # type: ignore[attr-defined]
    return test_client


@pytest.fixture
def policy_gate_client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    download_calls: list[tuple[str, int]] = []

    def fake_download_export_payload(*, request_url: str, max_download_bytes: int):
        download_calls.append((request_url, max_download_bytes))
        return (b"%PDF-1.7\nfake-pdf\n", "application/pdf", request_url)

    monkeypatch.setattr(
        cases_routes, "_download_export_payload", fake_download_export_payload
    )
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.delenv("IMMCAD_API_BEARER_TOKEN", raising=False)
    monkeypatch.delenv("API_BEARER_TOKEN", raising=False)
    monkeypatch.setenv("EXPORT_POLICY_GATE_ENABLED", "true")
    test_client = TestClient(create_app())
    test_client._download_calls = download_calls  # type: ignore[attr-defined]
    return test_client


def _issue_export_approval_token(
    client: TestClient,
    *,
    source_id: str,
    case_id: str,
    document_url: str,
    headers: dict[str, str] | None = None,
) -> str:
    response = client.post(
        "/api/export/cases/approval",
        headers=headers or {},
        json={
            "source_id": source_id,
            "case_id": case_id,
            "document_url": document_url,
            "user_approved": True,
        },
    )
    assert response.status_code == 200
    return response.json()["approval_token"]


def test_case_export_hardened_mode_requires_signed_approval_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    download_calls: list[tuple[str, int]] = []

    def fake_download_export_payload(*, request_url: str, max_download_bytes: int):
        download_calls.append((request_url, max_download_bytes))
        return (b"%PDF-1.7\nfake-pdf\n", "application/pdf", request_url)

    monkeypatch.setattr(
        cases_routes, "_download_export_payload", fake_download_export_payload
    )
    _set_hardened_export_env(monkeypatch)
    client = TestClient(create_app())

    response = client.post(
        "/api/export/cases",
        headers={"Authorization": "Bearer secret-token"},
        json={
            "source_id": "SCC_DECISIONS",
            "case_id": "scc-2024-3",
            "document_url": "https://decisions.scc-csc.ca/scc-csc/scc-csc/en/item/123/index.do",
            "format": "pdf",
            "user_approved": True,
        },
    )

    assert response.status_code == 403
    body = response.json()
    assert body["error"]["code"] == "POLICY_BLOCKED"
    assert body["error"]["policy_reason"] == "source_export_user_approval_required"
    assert download_calls == []


def test_case_export_hardened_mode_allows_signed_approval_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    download_calls: list[tuple[str, int]] = []

    def fake_download_export_payload(*, request_url: str, max_download_bytes: int):
        download_calls.append((request_url, max_download_bytes))
        return (b"%PDF-1.7\nfake-pdf\n", "application/pdf", request_url)

    monkeypatch.setattr(
        cases_routes, "_download_export_payload", fake_download_export_payload
    )
    _set_hardened_export_env(monkeypatch)
    client = TestClient(create_app())

    approval_response = client.post(
        "/api/export/cases/approval",
        headers={"Authorization": "Bearer secret-token"},
        json={
            "source_id": "SCC_DECISIONS",
            "case_id": "scc-2024-3",
            "document_url": "https://decisions.scc-csc.ca/scc-csc/scc-csc/en/item/123/index.do",
            "user_approved": True,
        },
    )

    assert approval_response.status_code == 200
    approval_body = approval_response.json()
    assert approval_body["approval_token"]
    assert approval_body["expires_at_epoch"] > 0

    export_response = client.post(
        "/api/export/cases",
        headers={"Authorization": "Bearer secret-token"},
        json={
            "source_id": "SCC_DECISIONS",
            "case_id": "scc-2024-3",
            "document_url": "https://decisions.scc-csc.ca/scc-csc/scc-csc/en/item/123/index.do",
            "format": "pdf",
            "user_approved": True,
            "approval_token": approval_body["approval_token"],
        },
    )

    assert export_response.status_code == 200
    assert export_response.content.startswith(b"%PDF-1.7")
    assert (
        export_response.headers.get("x-export-policy-reason") == "source_export_allowed"
    )
    assert download_calls == [
        (
            "https://decisions.scc-csc.ca/scc-csc/scc-csc/en/item/123/index.do",
            10 * 1024 * 1024,
        )
    ]


def test_case_export_policy_requires_explicit_user_approval(
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

    assert response.status_code == 403
    body = response.json()
    assert body["error"]["code"] == "POLICY_BLOCKED"
    assert body["error"]["policy_reason"] == "source_export_user_approval_required"
    assert getattr(policy_gate_client, "_download_calls") == []


def test_case_export_policy_gate_disabled_downloads_document_even_for_blocked_source(
    client: TestClient,
) -> None:
    approval_token = _issue_export_approval_token(
        client,
        source_id="CANLII_TERMS",
        case_id="terms-reference",
        document_url="https://www.canlii.org/en/ca/scc/doc/2024/2024scc3/2024scc3.html",
    )
    response = client.post(
        "/api/export/cases",
        json={
            "source_id": "CANLII_TERMS",
            "case_id": "terms-reference",
            "document_url": "https://www.canlii.org/en/ca/scc/doc/2024/2024scc3/2024scc3.html",
            "format": "pdf",
            "user_approved": True,
            "approval_token": approval_token,
        },
    )

    assert response.status_code == 200
    assert response.content.startswith(b"%PDF-1.7")
    assert response.headers.get("content-type", "").startswith("application/pdf")
    assert response.headers.get("content-disposition", "").endswith(
        '"CANLII_TERMS-terms-reference.pdf"'
    )
    assert (
        response.headers.get("x-export-policy-reason")
        == "source_export_allowed_gate_disabled"
    )
    assert response.headers.get("x-trace-id", "").strip() != ""
    assert getattr(client, "_download_calls") == [
        (
            "https://www.canlii.org/en/ca/scc/doc/2024/2024scc3/2024scc3.html",
            10 * 1024 * 1024,
        )
    ]


def test_case_export_policy_allows_official_source_and_downloads_when_gate_enabled(
    policy_gate_client: TestClient,
) -> None:
    approval_token = _issue_export_approval_token(
        policy_gate_client,
        source_id="SCC_DECISIONS",
        case_id="scc-2024-3",
        document_url="https://decisions.scc-csc.ca/scc-csc/scc-csc/en/item/123/index.do",
    )
    response = policy_gate_client.post(
        "/api/export/cases",
        json={
            "source_id": "SCC_DECISIONS",
            "case_id": "scc-2024-3",
            "document_url": "https://decisions.scc-csc.ca/scc-csc/scc-csc/en/item/123/index.do",
            "format": "pdf",
            "user_approved": True,
            "approval_token": approval_token,
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
        (
            "https://decisions.scc-csc.ca/scc-csc/scc-csc/en/item/123/index.do",
            10 * 1024 * 1024,
        )
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
            "user_approved": True,
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
            "user_approved": True,
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
            "user_approved": True,
        },
    )

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert body["error"]["policy_reason"] == "export_url_not_allowed_for_source"
    assert getattr(policy_gate_client, "_download_calls") == []


def test_case_export_policy_allows_www_subdomain_host_matching_source_domain(
    policy_gate_client: TestClient,
) -> None:
    approval_token = _issue_export_approval_token(
        policy_gate_client,
        source_id="SCC_DECISIONS",
        case_id="scc-2024-3",
        document_url="https://www.decisions.scc-csc.ca/scc-csc/scc-csc/en/item/123/index.do",
    )
    response = policy_gate_client.post(
        "/api/export/cases",
        json={
            "source_id": "SCC_DECISIONS",
            "case_id": "scc-2024-3",
            "document_url": "https://www.decisions.scc-csc.ca/scc-csc/scc-csc/en/item/123/index.do",
            "format": "pdf",
            "user_approved": True,
            "approval_token": approval_token,
        },
    )

    assert response.status_code == 200
    assert response.content.startswith(b"%PDF-1.7")
    assert response.headers.get("x-export-policy-reason") == "source_export_allowed"
    assert getattr(policy_gate_client, "_download_calls") == [
        (
            "https://decisions.scc-csc.ca/scc-csc/scc-csc/en/item/123/index.do",
            10 * 1024 * 1024,
        )
    ]


def test_case_export_policy_rejects_lookalike_host_outside_source_domain(
    policy_gate_client: TestClient,
) -> None:
    response = policy_gate_client.post(
        "/api/export/cases",
        json={
            "source_id": "SCC_DECISIONS",
            "case_id": "scc-2024-3",
            "document_url": "https://evildecisions.scc-csc.ca/scc-csc/scc-csc/en/item/123/index.do",
            "format": "pdf",
            "user_approved": True,
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
    def fake_download_export_payload(*, request_url: str, max_download_bytes: int):
        del request_url, max_download_bytes
        return (
            b"%PDF-1.7\nfake-pdf\n",
            "application/pdf",
            "https://evil.example/file.pdf",
        )

    monkeypatch.setattr(
        cases_routes, "_download_export_payload", fake_download_export_payload
    )
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.delenv("IMMCAD_API_BEARER_TOKEN", raising=False)
    monkeypatch.delenv("API_BEARER_TOKEN", raising=False)
    monkeypatch.setenv("EXPORT_POLICY_GATE_ENABLED", "true")

    client = TestClient(create_app())
    approval_token = _issue_export_approval_token(
        client,
        source_id="SCC_DECISIONS",
        case_id="scc-2024-3",
        document_url="https://decisions.scc-csc.ca/scc-csc/scc-csc/en/item/123/index.do",
    )
    response = client.post(
        "/api/export/cases",
        json={
            "source_id": "SCC_DECISIONS",
            "case_id": "scc-2024-3",
            "document_url": "https://decisions.scc-csc.ca/scc-csc/scc-csc/en/item/123/index.do",
            "format": "pdf",
            "user_approved": True,
            "approval_token": approval_token,
        },
    )

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert (
        body["error"]["policy_reason"] == "export_redirect_url_not_allowed_for_source"
    )


def test_case_export_policy_allows_redirect_to_source_subdomain_host(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_download_export_payload(*, request_url: str, max_download_bytes: int):
        del request_url, max_download_bytes
        return (
            b"%PDF-1.7\nfake-pdf\n",
            "application/pdf",
            "https://www.decisions.scc-csc.ca/scc-csc/scc-csc/en/item/123/file.pdf",
        )

    monkeypatch.setattr(
        cases_routes, "_download_export_payload", fake_download_export_payload
    )
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.delenv("IMMCAD_API_BEARER_TOKEN", raising=False)
    monkeypatch.delenv("API_BEARER_TOKEN", raising=False)
    monkeypatch.setenv("EXPORT_POLICY_GATE_ENABLED", "true")

    client = TestClient(create_app())
    approval_token = _issue_export_approval_token(
        client,
        source_id="SCC_DECISIONS",
        case_id="scc-2024-3",
        document_url="https://decisions.scc-csc.ca/scc-csc/scc-csc/en/item/123/index.do",
    )
    response = client.post(
        "/api/export/cases",
        json={
            "source_id": "SCC_DECISIONS",
            "case_id": "scc-2024-3",
            "document_url": "https://decisions.scc-csc.ca/scc-csc/scc-csc/en/item/123/index.do",
            "format": "pdf",
            "user_approved": True,
            "approval_token": approval_token,
        },
    )

    assert response.status_code == 200
    assert response.content.startswith(b"%PDF-1.7")
    assert response.headers.get("x-export-policy-reason") == "source_export_allowed"


def test_case_export_policy_rejects_oversized_document_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_download_export_payload(*, request_url: str, max_download_bytes: int):
        del request_url, max_download_bytes
        raise cases_routes.ExportTooLargeError(
            "Case export payload exceeds configured maximum size"
        )

    monkeypatch.setattr(
        cases_routes, "_download_export_payload", fake_download_export_payload
    )
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.delenv("IMMCAD_API_BEARER_TOKEN", raising=False)
    monkeypatch.delenv("API_BEARER_TOKEN", raising=False)
    monkeypatch.setenv("EXPORT_POLICY_GATE_ENABLED", "true")

    client = TestClient(create_app())
    approval_token = _issue_export_approval_token(
        client,
        source_id="SCC_DECISIONS",
        case_id="scc-2024-3",
        document_url="https://decisions.scc-csc.ca/scc-csc/scc-csc/en/item/123/index.do",
    )
    response = client.post(
        "/api/export/cases",
        json={
            "source_id": "SCC_DECISIONS",
            "case_id": "scc-2024-3",
            "document_url": "https://decisions.scc-csc.ca/scc-csc/scc-csc/en/item/123/index.do",
            "format": "pdf",
            "user_approved": True,
            "approval_token": approval_token,
        },
    )

    assert response.status_code == 413
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert body["error"]["policy_reason"] == "source_export_payload_too_large"


def test_case_export_policy_rejects_non_pdf_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_download_export_payload(*, request_url: str, max_download_bytes: int):
        del max_download_bytes
        return (
            b"<html>not a pdf</html>",
            "text/html; charset=utf-8",
            request_url,
        )

    monkeypatch.setattr(
        cases_routes, "_download_export_payload", fake_download_export_payload
    )
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.delenv("IMMCAD_API_BEARER_TOKEN", raising=False)
    monkeypatch.delenv("API_BEARER_TOKEN", raising=False)
    monkeypatch.setenv("EXPORT_POLICY_GATE_ENABLED", "true")

    client = TestClient(create_app())
    approval_token = _issue_export_approval_token(
        client,
        source_id="SCC_DECISIONS",
        case_id="scc-2024-3",
        document_url="https://decisions.scc-csc.ca/scc-csc/scc-csc/en/item/123/index.do",
    )
    response = client.post(
        "/api/export/cases",
        json={
            "source_id": "SCC_DECISIONS",
            "case_id": "scc-2024-3",
            "document_url": "https://decisions.scc-csc.ca/scc-csc/scc-csc/en/item/123/index.do",
            "format": "pdf",
            "user_approved": True,
            "approval_token": approval_token,
        },
    )

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert body["error"]["policy_reason"] == "source_export_non_pdf_payload"


def test_case_export_metrics_include_allowed_and_blocked_outcomes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_download_export_payload(*, request_url: str, max_download_bytes: int):
        del max_download_bytes
        return (b"%PDF-1.7\nfake-pdf\n", "application/pdf", request_url)

    monkeypatch.setattr(
        cases_routes, "_download_export_payload", fake_download_export_payload
    )
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("IMMCAD_API_BEARER_TOKEN", "secret-token")
    monkeypatch.setenv("API_BEARER_TOKEN", "secret-token")
    monkeypatch.setenv("EXPORT_POLICY_GATE_ENABLED", "true")
    secured_client = TestClient(create_app())
    headers = {"Authorization": "Bearer secret-token"}
    approval_token = _issue_export_approval_token(
        secured_client,
        source_id="SCC_DECISIONS",
        case_id="scc-2024-3",
        document_url="https://decisions.scc-csc.ca/scc-csc/scc-csc/en/item/123/index.do",
        headers=headers,
    )

    blocked = secured_client.post(
        "/api/export/cases",
        headers=headers,
        json={
            "source_id": "CANLII_TERMS",
            "case_id": "terms-reference",
            "document_url": "https://www.canlii.org/en/ca/scc/doc/2024/2024scc3/2024scc3.html",
            "format": "pdf",
            "user_approved": True,
        },
    )
    allowed = secured_client.post(
        "/api/export/cases",
        headers=headers,
        json={
            "source_id": "SCC_DECISIONS",
            "case_id": "scc-2024-3",
            "document_url": "https://decisions.scc-csc.ca/scc-csc/scc-csc/en/item/123/index.do",
            "format": "pdf",
            "user_approved": True,
            "approval_token": approval_token,
        },
    )
    metrics = secured_client.get("/ops/metrics", headers=headers)

    assert blocked.status_code == 403
    assert allowed.status_code == 200
    assert metrics.status_code == 200

    export_metrics = metrics.json()["request_metrics"]["export"]
    assert export_metrics["attempts"] == 2
    assert export_metrics["allowed"] == 1
    assert export_metrics["blocked"] == 1
    assert export_metrics["fetch_failures"] == 0
    assert export_metrics["too_large"] == 0
    assert export_metrics["policy_reasons"]["source_export_blocked_by_policy"] == 1
    assert export_metrics["policy_reasons"]["source_export_allowed"] == 1
    assert len(export_metrics["audit_recent"]) == 2
    blocked_event, allowed_event = export_metrics["audit_recent"]
    assert blocked_event["outcome"] == "blocked"
    assert blocked_event["policy_reason"] == "source_export_blocked_by_policy"
    assert blocked_event["user_approved"] is True
    assert blocked_event["source_id"] == "CANLII_TERMS"
    assert blocked_event["trace_id"].strip() != ""
    assert allowed_event["outcome"] == "allowed"
    assert allowed_event["policy_reason"] == "source_export_allowed"
    assert allowed_event["source_id"] == "SCC_DECISIONS"
