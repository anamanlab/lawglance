from __future__ import annotations

import fitz
from fastapi.testclient import TestClient

from immcad_api.main import create_app


client = TestClient(create_app())


def _pdf_payload(text: str) -> bytes:
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), text)
    payload = document.tobytes()
    document.close()
    return payload


def test_documents_intake_accepts_multipart_upload() -> None:
    matter_id = "matter-route-accept"
    response = client.post(
        "/api/documents/intake",
        data={"forum": "federal_court_jr", "matter_id": matter_id},
        files=[
            ("files", ("notice.pdf", _pdf_payload("Notice of Application"), "application/pdf")),
            ("files", ("affidavit.pdf", _pdf_payload("Affidavit of John Smith"), "application/pdf")),
        ],
    )

    assert response.status_code == 200
    body = response.json()
    assert body["matter_id"] == matter_id
    assert len(body["results"]) == 2
    assert "x-trace-id" in response.headers


def test_documents_package_blocks_when_blocking_or_missing_items_present() -> None:
    matter_id = "matter-route-blocked"
    intake_response = client.post(
        "/api/documents/intake",
        data={"forum": "federal_court_jr", "matter_id": matter_id},
        files=[
            ("files", ("notice.pdf", _pdf_payload("Notice of Application"), "application/pdf")),
        ],
    )
    assert intake_response.status_code == 200

    package_response = client.post(f"/api/documents/matters/{matter_id}/package")

    assert package_response.status_code == 409
    body = package_response.json()
    assert body["error"]["code"] == "POLICY_BLOCKED"
    assert body["error"]["policy_reason"] == "document_package_not_ready"
    assert "x-trace-id" in package_response.headers
