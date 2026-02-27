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


class _WarningStubIntakeService:
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
            file_id=f"warning-file-{self._sequence}",
            original_filename=original_filename,
            normalized_filename=original_filename.lower(),
            classification="disclosure_package",
            quality_status="processed",
            issues=["ocr_low_confidence"],
        )


class _ExplodingIntakeService:
    def process_file(
        self,
        *,
        original_filename: str,
        payload_bytes: bytes,
    ) -> DocumentIntakeResult:
        del original_filename, payload_bytes
        raise RuntimeError("unexpected intake failure")


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
    dynamic_client_id_from_header: bool = False,
    intake_service: object | None = None,
    raise_server_exceptions: bool = True,
) -> tuple[TestClient, RequestMetrics]:
    request_metrics = RequestMetrics()
    app = FastAPI()

    @app.middleware("http")
    async def _request_context_middleware(request: Request, call_next):
        request.state.trace_id = "trace-doc-routes"
        if dynamic_client_id_from_header:
            request.state.client_id = request.headers.get("x-test-client-id", "198.51.100.77")
        else:
            request.state.client_id = "198.51.100.77"
        return await call_next(request)

    app.include_router(
        build_documents_router(
            request_metrics=request_metrics,
            intake_service=intake_service or _StubIntakeService(),
            upload_max_bytes=upload_max_bytes,
            upload_max_files=upload_max_files,
        )
    )

    return TestClient(app, raise_server_exceptions=raise_server_exceptions), request_metrics


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


def test_documents_intake_returns_partial_results_for_mixed_validity_files() -> None:
    matter_id = "matter-route-partial"
    response = client.post(
        "/api/documents/intake",
        data={"forum": "federal_court_jr", "matter_id": matter_id},
        files=[
            ("files", ("notice.pdf", _pdf_payload("Notice of Application"), "application/pdf")),
            ("files", ("payload.exe", b"MZ", "application/octet-stream")),
        ],
    )

    assert response.status_code == 200
    body = response.json()
    assert body["matter_id"] == matter_id
    assert len(body["results"]) == 2
    assert body["results"][0]["quality_status"] in {"processed", "needs_review"}
    assert body["results"][1]["quality_status"] == "failed"
    assert "unsupported_file_type" in body["results"][1]["issues"]
    assert "x-trace-id" in response.headers


def test_documents_accepts_octet_stream_scans() -> None:
    matter_id = "matter-octet"
    response = client.post(
        "/api/documents/intake",
        data={"forum": "federal_court_jr", "matter_id": matter_id},
        files=[
            ("files", ("scan.pdf", _pdf_payload("Notice of Application"), "application/octet-stream")),
        ],
    )

    assert response.status_code == 200
    body = response.json()
    assert body["results"][0]["quality_status"] in {"processed", "needs_review"}
    assert body["results"][0]["classification"] == "notice_of_application"


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


def test_documents_intake_partial_request_records_accepted_metrics() -> None:
    local_client, request_metrics = _documents_test_harness(upload_max_bytes=4096)
    response = local_client.post(
        "/api/documents/intake",
        data={"forum": "federal_court_jr", "matter_id": "matter-partial-telemetry"},
        files=[
            ("files", ("notice.pdf", _pdf_payload("Notice of Application"), "application/pdf")),
            ("files", ("payload.exe", b"MZ", "application/octet-stream")),
            ("files", ("big.pdf", b"%PDF-1.7\n" + (b"A" * 5000), "application/pdf")),
        ],
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body["results"]) == 3
    assert body["results"][0]["quality_status"] in {"processed", "needs_review"}
    assert body["results"][1]["issues"] == ["unsupported_file_type"]
    assert body["results"][2]["issues"] == ["upload_size_exceeded"]

    metrics_snapshot = request_metrics.snapshot()["document_intake"]
    assert metrics_snapshot["attempts"] == 1
    assert metrics_snapshot["accepted"] == 1
    assert metrics_snapshot["rejected"] == 0
    assert metrics_snapshot["policy_reasons"] == {}


def test_documents_intake_all_failed_request_records_rejected_metrics() -> None:
    local_client, request_metrics = _documents_test_harness(upload_max_bytes=1024)
    response = local_client.post(
        "/api/documents/intake",
        data={"forum": "federal_court_jr", "matter_id": "matter-all-failed-telemetry"},
        files=[
            ("files", ("payload.exe", b"MZ", "application/octet-stream")),
            ("files", ("big.pdf", b"%PDF-1.7\n" + (b"A" * 5000), "application/pdf")),
        ],
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body["results"]) == 2
    assert body["results"][0]["quality_status"] == "failed"
    assert body["results"][1]["quality_status"] == "failed"

    metrics_snapshot = request_metrics.snapshot()["document_intake"]
    assert metrics_snapshot["attempts"] == 1
    assert metrics_snapshot["accepted"] == 0
    assert metrics_snapshot["rejected"] == 1
    assert metrics_snapshot["policy_reasons"]["document_all_files_failed"] == 1
    assert metrics_snapshot["audit_recent"][0]["outcome"] == "rejected"
    assert (
        metrics_snapshot["audit_recent"][0]["policy_reason"]
        == "document_all_files_failed"
    )


def test_documents_readiness_warnings_are_deduplicated() -> None:
    local_client, _ = _documents_test_harness(intake_service=_WarningStubIntakeService())
    matter_id = "matter-warning-dedupe"
    intake_response = local_client.post(
        "/api/documents/intake",
        data={"forum": "rpd", "matter_id": matter_id},
        files=[
            ("files", ("scan-a.pdf", _pdf_payload("scan-a"), "application/pdf")),
            ("files", ("scan-b.pdf", _pdf_payload("scan-b"), "application/pdf")),
        ],
    )
    assert intake_response.status_code == 200
    assert intake_response.json()["warnings"] == ["ocr_low_confidence"]

    readiness_response = local_client.get(f"/api/documents/matters/{matter_id}/readiness")
    assert readiness_response.status_code == 200
    assert readiness_response.json()["warnings"] == ["ocr_low_confidence"]


def test_documents_readiness_exposes_requirement_status_metadata() -> None:
    matter_id = "matter-rpd-rules"
    intake_response = client.post(
        "/api/documents/intake",
        data={"forum": "rpd", "matter_id": matter_id},
        files=[
            (
                "files",
                (
                    "disclosure.pdf",
                    _pdf_payload("Document disclosure package for tribunal review"),
                    "application/pdf",
                ),
            ),
            (
                "files",
                (
                    "translation.pdf",
                    _pdf_payload("Translation prepared for hearing"),
                    "application/pdf",
                ),
            ),
        ],
    )
    assert intake_response.status_code == 200

    readiness_response = client.get(f"/api/documents/matters/{matter_id}/readiness")
    assert readiness_response.status_code == 200
    requirement_statuses = readiness_response.json()["requirement_statuses"]
    status_by_item = {item["item"]: item for item in requirement_statuses}
    assert status_by_item["disclosure_package"]["status"] == "present"
    assert status_by_item["disclosure_package"]["rule_scope"] == "base"
    assert status_by_item["translator_declaration"]["status"] == "missing"
    assert status_by_item["translator_declaration"]["rule_scope"] == "conditional"
    assert status_by_item["translator_declaration"]["reason"]


def test_documents_matter_access_is_scoped_to_client_id() -> None:
    local_client, _ = _documents_test_harness(dynamic_client_id_from_header=True)
    matter_id = "matter-client-scope"
    intake_response = local_client.post(
        "/api/documents/intake",
        data={"forum": "federal_court_jr", "matter_id": matter_id},
        files=[
            ("files", ("notice.pdf", _pdf_payload("Notice of Application"), "application/pdf")),
        ],
        headers={"x-test-client-id": "198.51.100.10"},
    )
    assert intake_response.status_code == 200

    wrong_client_readiness = local_client.get(
        f"/api/documents/matters/{matter_id}/readiness",
        headers={"x-test-client-id": "198.51.100.99"},
    )
    assert wrong_client_readiness.status_code == 404
    assert wrong_client_readiness.json()["error"]["policy_reason"] == "document_matter_not_found"

    right_client_readiness = local_client.get(
        f"/api/documents/matters/{matter_id}/readiness",
        headers={"x-test-client-id": "198.51.100.10"},
    )
    assert right_client_readiness.status_code == 200


def test_documents_intake_returns_500_for_unexpected_service_errors() -> None:
    local_client, _ = _documents_test_harness(
        intake_service=_ExplodingIntakeService(),
        raise_server_exceptions=False,
    )
    response = local_client.post(
        "/api/documents/intake",
        data={"forum": "federal_court_jr", "matter_id": "matter-exploding-intake"},
        files=[
            ("files", ("notice.pdf", _pdf_payload("Notice of Application"), "application/pdf")),
        ],
    )

    assert response.status_code == 500
