from __future__ import annotations

import base64

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


def test_upload_reports_unsupported_content_type_as_failed_result() -> None:
    client = TestClient(create_app())
    response = client.post(
        "/api/documents/intake",
        data={"forum": "federal_court_jr", "matter_id": "matter-upload-type"},
        files=[("files", ("payload.exe", b"MZ", "application/octet-stream"))],
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body["results"]) == 1
    assert body["results"][0]["quality_status"] == "failed"
    assert body["results"][0]["issues"] == ["unsupported_file_type"]


def test_upload_reports_oversized_payload_as_failed_result(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DOCUMENT_UPLOAD_MAX_BYTES", "1024")
    oversized_payload = b"%PDF-1.7\\n" + (b"A" * 5000)
    client = TestClient(create_app())
    response = client.post(
        "/api/documents/intake",
        data={"forum": "federal_court_jr", "matter_id": "matter-upload-size"},
        files=[("files", ("big.pdf", oversized_payload, "application/pdf"))],
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body["results"]) == 1
    assert body["results"][0]["quality_status"] == "failed"
    assert body["results"][0]["issues"] == ["upload_size_exceeded"]


def test_upload_malformed_allowed_payload_returns_failed_result() -> None:
    # Small malformed PNG payload that currently surfaces parser edge cases.
    malformed_png_payload = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO2L0QAAAABJRU5ErkJggg=="
    )
    client = TestClient(create_app(), raise_server_exceptions=False)
    response = client.post(
        "/api/documents/intake",
        data={"forum": "rpd", "matter_id": "matter-upload-malformed"},
        files=[("files", ("scan.png", malformed_png_payload, "image/png"))],
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body["results"]) == 1
    assert body["results"][0]["quality_status"] == "failed"
    assert "file_unreadable" in body["results"][0]["issues"]


def test_upload_valid_png_payload_returns_needs_review_result() -> None:
    valid_png_payload = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Wn2V50AAAAASUVORK5CYII="
    )
    client = TestClient(create_app())
    response = client.post(
        "/api/documents/intake",
        data={"forum": "rpd", "matter_id": "matter-upload-valid-png"},
        files=[("files", ("scan.png", valid_png_payload, "image/png"))],
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body["results"]) == 1
    assert body["results"][0]["quality_status"] == "needs_review"
    assert "ocr_required" in body["results"][0]["issues"]
