from __future__ import annotations

import httpx
import pytest
from fastapi.testclient import TestClient

from immcad_api.main import create_app


class _MockStreamResponse:
    def __init__(
        self,
        *,
        status_code: int,
        url: str,
        headers: dict[str, str] | None = None,
        body: bytes = b"",
    ) -> None:
        self.status_code = status_code
        self.url = httpx.URL(url)
        self.headers = headers or {}
        self._body = body

    def __enter__(self) -> "_MockStreamResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        del exc_type, exc, tb
        return False

    def raise_for_status(self) -> None:
        if self.status_code < 400:
            return
        request = httpx.Request("GET", str(self.url))
        response = httpx.Response(
            self.status_code,
            request=request,
            headers=self.headers,
            content=self._body,
        )
        raise httpx.HTTPStatusError(
            f"{self.status_code} error",
            request=request,
            response=response,
        )

    def iter_bytes(self):
        if self._body:
            yield self._body


def test_case_export_blocks_untrusted_redirect_hosts_before_payload_download(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = TestClient(create_app())
    document_url = "https://decisions.fct-cf.gc.ca/fc-cf/decisions/en/item/123456/index.do"
    approval_response = client.post(
        "/api/export/cases/approval",
        json={
            "source_id": "FC_DECISIONS",
            "case_id": "FC-2026-123456",
            "document_url": document_url,
            "user_approved": True,
        },
    )
    assert approval_response.status_code == 200
    approval_token = approval_response.json()["approval_token"]

    def _mock_stream(method: str, url: str, timeout: float, follow_redirects: bool):
        del method, timeout, follow_redirects
        return _MockStreamResponse(
            status_code=302,
            url=url,
            headers={"location": "https://evil.example/export.pdf"},
        )

    monkeypatch.setattr("immcad_api.api.routes.cases.httpx.stream", _mock_stream)

    export_response = client.post(
        "/api/export/cases",
        json={
            "source_id": "FC_DECISIONS",
            "case_id": "FC-2026-123456",
            "document_url": document_url,
            "format": "pdf",
            "user_approved": True,
            "approval_token": approval_token,
        },
    )

    assert export_response.status_code == 422
    body = export_response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert body["error"]["policy_reason"] == "export_redirect_url_not_allowed_for_source"


def test_case_export_allows_fc_norma_lexum_document_url_alias(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = TestClient(create_app())
    document_url = "https://norma.lexum.com/fc-cf/decisions/en/123456/1/document.do"
    approval_response = client.post(
        "/api/export/cases/approval",
        json={
            "source_id": "FC_DECISIONS",
            "case_id": "FC-2026-123456",
            "document_url": document_url,
            "user_approved": True,
        },
    )
    assert approval_response.status_code == 200
    approval_token = approval_response.json()["approval_token"]

    def _mock_stream(method: str, url: str, timeout: float, follow_redirects: bool):
        del method, timeout, follow_redirects
        return _MockStreamResponse(
            status_code=200,
            url=url,
            headers={"content-type": "application/pdf"},
            body=b"%PDF-1.7\nfake-pdf\n",
        )

    monkeypatch.setattr("immcad_api.api.routes.cases.httpx.stream", _mock_stream)

    export_response = client.post(
        "/api/export/cases",
        json={
            "source_id": "FC_DECISIONS",
            "case_id": "FC-2026-123456",
            "document_url": document_url,
            "format": "pdf",
            "user_approved": True,
            "approval_token": approval_token,
        },
    )

    assert export_response.status_code == 200
    assert export_response.headers["content-type"].startswith("application/pdf")
    assert export_response.content.startswith(b"%PDF-1.7")
