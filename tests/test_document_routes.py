from __future__ import annotations

import fitz
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
import pytest

from immcad_api.api.routes.documents import build_documents_router
from immcad_api.main import create_app
from immcad_api.schemas import DocumentIntakeResult
from immcad_api.telemetry.request_metrics import RequestMetrics


client = TestClient(create_app())


class _StubIntakeService:
    def __init__(self) -> None:
        self._sequence = 0

    def process_file(
        self,
        *,
        original_filename: str,
        payload_bytes: bytes,
    ) -> DocumentIntakeResult:
        del payload_bytes
        self._sequence += 1
        return DocumentIntakeResult(
            file_id=f"file-{self._sequence}",
            original_filename=original_filename,
            normalized_filename=original_filename.lower(),
            classification="notice_of_application",
            quality_status="processed",
            issues=[],
        )


def _pdf_payload(text: str) -> bytes:
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), text)
    payload = document.tobytes()
    document.close()
    return payload


def _documents_test_harness(
    *,
    upload_max_bytes: int = 10 * 1024 * 1024,
    upload_max_files: int = 25,
) -> tuple[TestClient, RequestMetrics]:
    request_metrics = RequestMetrics()
    app = FastAPI()

    @app.middleware("http")
    async def _request_context_middleware(request: Request, call_next):
        request.state.trace_id = "trace-doc-routes"
        request.state.client_id = "198.51.100.77"
        return await call_next(request)

    app.include_router(
        build_documents_router(
            request_metrics=request_metrics,
            intake_service=_StubIntakeService(),
            upload_max_bytes=upload_max_bytes,
            upload_max_files=upload_max_files,
        )
    )

    return TestClient(app), request_metrics


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


def test_documents_intake_records_accepted_audit_event_and_metrics() -> None:
    local_client, request_metrics = _documents_test_harness()
    matter_id = "matter-route-telemetry-accept"

    response = local_client.post(
        "/api/documents/intake",
        data={"forum": "federal_court_jr", "matter_id": matter_id},
        files=[
            ("files", ("notice.pdf", _pdf_payload("Notice of Application"), "application/pdf")),
            ("files", ("affidavit.pdf", _pdf_payload("Affidavit of John Smith"), "application/pdf")),
        ],
    )

    assert response.status_code == 200
    metrics_snapshot = request_metrics.snapshot()["document_intake"]
    assert metrics_snapshot["attempts"] == 1
    assert metrics_snapshot["accepted"] == 1
    assert metrics_snapshot["rejected"] == 0
    assert metrics_snapshot["policy_reasons"] == {}
    assert len(metrics_snapshot["audit_recent"]) == 1
    audit_event = metrics_snapshot["audit_recent"][0]
    assert audit_event["trace_id"] == "trace-doc-routes"
    assert audit_event["client_id"] == "198.51.100.77"
    assert audit_event["matter_id"] == matter_id
    assert audit_event["forum"] == "federal_court_jr"
    assert audit_event["file_count"] == 2
    assert audit_event["outcome"] == "accepted"
    assert "policy_reason" not in audit_event


@pytest.mark.parametrize(
    (
        "request_kwargs",
        "upload_max_files",
        "upload_max_bytes",
        "expected_status",
        "expected_policy_reason",
        "expected_file_count",
    ),
    [
        (
            {
                "data": {"forum": "federal_court_jr", "matter_id": "matter-too-many"},
                "files": [
                    ("files", ("first.pdf", _pdf_payload("first"), "application/pdf")),
                    ("files", ("second.pdf", _pdf_payload("second"), "application/pdf")),
                ],
            },
            1,
            10 * 1024 * 1024,
            422,
            "document_file_count_exceeded",
            2,
        ),
        (
            {
                "data": {"forum": "federal_court_jr", "matter_id": "matter-bad-type"},
                "files": [("files", ("payload.exe", b"MZ", "application/octet-stream"))],
            },
            25,
            10 * 1024 * 1024,
            422,
            "unsupported_file_type",
            1,
        ),
        (
            {
                "data": {"forum": "federal_court_jr", "matter_id": "matter-oversize"},
                "files": [
                    (
                        "files",
                        ("big.pdf", b"%PDF-1.7\n" + (b"A" * 4096), "application/pdf"),
                    )
                ],
            },
            25,
            512,
            413,
            "upload_size_exceeded",
            1,
        ),
        (
            {
                "data": {"forum": "unknown", "matter_id": "matter-invalid-forum"},
                "files": [("files", ("doc.pdf", _pdf_payload("doc"), "application/pdf"))],
            },
            25,
            10 * 1024 * 1024,
            422,
            "document_forum_invalid",
            1,
        ),
        (
            {"data": {"forum": "federal_court_jr", "matter_id": "matter-missing-files"}},
            25,
            10 * 1024 * 1024,
            422,
            "document_files_missing",
            0,
        ),
    ],
)
def test_documents_intake_records_rejected_audit_events_and_metrics(
    request_kwargs: dict[str, object],
    upload_max_files: int,
    upload_max_bytes: int,
    expected_status: int,
    expected_policy_reason: str,
    expected_file_count: int,
) -> None:
    local_client, request_metrics = _documents_test_harness(
        upload_max_files=upload_max_files,
        upload_max_bytes=upload_max_bytes,
    )
    response = local_client.post("/api/documents/intake", **request_kwargs)

    assert response.status_code == expected_status
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert body["error"]["policy_reason"] == expected_policy_reason

    metrics_snapshot = request_metrics.snapshot()["document_intake"]
    assert metrics_snapshot["attempts"] == 1
    assert metrics_snapshot["accepted"] == 0
    assert metrics_snapshot["rejected"] == 1
    assert metrics_snapshot["policy_reasons"][expected_policy_reason] == 1
    assert len(metrics_snapshot["audit_recent"]) == 1
    audit_event = metrics_snapshot["audit_recent"][0]
    assert audit_event["trace_id"] == "trace-doc-routes"
    assert audit_event["client_id"] == "198.51.100.77"
    assert audit_event["file_count"] == expected_file_count
    assert audit_event["outcome"] == "rejected"
    assert audit_event["policy_reason"] == expected_policy_reason
