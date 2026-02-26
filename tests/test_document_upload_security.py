from __future__ import annotations

import fitz
import pytest
from fastapi.testclient import TestClient

from immcad_api.main import create_app


def _pdf_payload(text: str) -> bytes:
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), text)
    payload = document.tobytes()
    document.close()
    return payload


def test_upload_rejects_unsupported_content_type() -> None:
    client = TestClient(create_app())
    response = client.post(
        "/api/documents/intake",
        data={"forum": "federal_court_jr", "matter_id": "matter-upload-type"},
        files=[("files", ("payload.exe", b"MZ", "application/octet-stream"))],
    )

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert body["error"]["policy_reason"] == "unsupported_file_type"


def test_upload_rejects_oversized_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DOCUMENT_UPLOAD_MAX_BYTES", "1024")
    oversized_payload = b"%PDF-1.7\\n" + (b"A" * 5000)
    client = TestClient(create_app())
    response = client.post(
        "/api/documents/intake",
        data={"forum": "federal_court_jr", "matter_id": "matter-upload-size"},
        files=[("files", ("big.pdf", oversized_payload, "application/pdf"))],
    )

    assert response.status_code == 413
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert body["error"]["policy_reason"] == "upload_size_exceeded"
