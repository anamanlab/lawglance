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


class _ValueErrorIntakeService:
    def process_file(
        self,
        *,
        original_filename: str,
        payload_bytes: bytes,
    ) -> DocumentIntakeResult:
        del original_filename, payload_bytes
        raise ValueError("unable to parse upload payload")


class _UnreadableStubIntakeService:
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
            file_id=f"unreadable-file-{self._sequence}",
            original_filename=original_filename,
            normalized_filename=original_filename.lower(),
            classification="unclassified",
            quality_status="failed",
            issues=["file_unreadable"],
        )


class _MappedClassificationIntakeService:
    def __init__(self, mapping: dict[str, str]) -> None:
        self._sequence = 0
        self._mapping = {name.strip().lower(): value for name, value in mapping.items()}

    def process_file(
        self,
        *,
        original_filename: str,
        payload_bytes: bytes,
    ) -> DocumentIntakeResult:
        del payload_bytes
        self._sequence += 1
        normalized_filename = original_filename.strip().lower()
        classification = self._mapping.get(normalized_filename, "unclassified")
        return DocumentIntakeResult(
            file_id=f"mapped-file-{self._sequence}",
            original_filename=original_filename,
            normalized_filename=normalized_filename,
            classification=classification,
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
    assert body["results"][0]["total_pages"] >= 1
    assert body["results"][0]["page_char_counts"]
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


def test_documents_intake_rejects_invalid_compilation_profile_id() -> None:
    response = client.post(
        "/api/documents/intake",
        data={
            "forum": "federal_court_jr",
            "matter_id": "matter-invalid-profile",
            "compilation_profile_id": "not-a-real-profile-id",
        },
        files=[
            ("files", ("notice.pdf", _pdf_payload("Notice of Application"), "application/pdf")),
        ],
    )

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert body["error"]["policy_reason"] == "document_compilation_profile_invalid"
    assert "Supported profiles for forum federal_court_jr" in body["error"]["message"]
    assert "Unsupported profile families:" in body["error"]["message"]


def test_documents_support_matrix_endpoint_returns_supported_and_unsupported_profiles() -> None:
    response = client.get("/api/documents/support-matrix")

    assert response.status_code == 200
    body = response.json()
    assert "supported_profiles_by_forum" in body
    assert "federal_court_jr" in body["supported_profiles_by_forum"]
    assert "ircc_application" in body["supported_profiles_by_forum"]
    assert "ircc_pr_card_renewal" in body["supported_profiles_by_forum"]["ircc_application"]
    assert "unsupported_profile_families" in body
    assert body["unsupported_profile_families"]


def test_documents_intake_normalizes_supported_compilation_profile_id() -> None:
    response = client.post(
        "/api/documents/intake",
        data={
            "forum": "federal_court_jr",
            "matter_id": "matter-normalized-profile",
            "compilation_profile_id": "  FEDERAL_COURT_JR_LEAVE  ",
        },
        files=[
            ("files", ("notice.pdf", _pdf_payload("Notice of Application"), "application/pdf")),
        ],
    )

    assert response.status_code == 200
    assert response.json()["compilation_profile_id"] == "federal_court_jr_leave"


def test_documents_intake_assigns_ircc_application_default_profile() -> None:
    response = client.post(
        "/api/documents/intake",
        data={
            "forum": "ircc_application",
            "matter_id": "matter-ircc-default-profile",
        },
        files=[
            (
                "files",
                ("application.pdf", _pdf_payload("PR card renewal supporting package"), "application/pdf"),
            ),
        ],
    )

    assert response.status_code == 200
    assert response.json()["compilation_profile_id"] == "ircc_pr_card_renewal"


def test_documents_classification_override_updates_readiness_and_records_audit_event() -> None:
    local_client, request_metrics = _documents_test_harness()
    matter_id = "matter-classification-override-success"
    intake_response = local_client.post(
        "/api/documents/intake",
        data={"forum": "rpd", "matter_id": matter_id},
        files=[
            ("files", ("uploaded.pdf", _pdf_payload("Uploaded document"), "application/pdf")),
        ],
    )
    assert intake_response.status_code == 200
    file_id = intake_response.json()["results"][0]["file_id"]

    readiness_before_response = local_client.get(
        f"/api/documents/matters/{matter_id}/readiness"
    )
    assert readiness_before_response.status_code == 200
    assert readiness_before_response.json()["is_ready"] is False

    override_response = local_client.patch(
        f"/api/documents/matters/{matter_id}/classification",
        json={"file_id": file_id, "classification": "disclosure_package"},
    )
    assert override_response.status_code == 200
    readiness_after_body = override_response.json()
    assert readiness_after_body["is_ready"] is True
    assert readiness_after_body["missing_required_items"] == []

    package_response = local_client.post(f"/api/documents/matters/{matter_id}/package")
    assert package_response.status_code == 200

    metrics_snapshot = request_metrics.snapshot()["document_classification_override"]
    assert metrics_snapshot["attempts"] == 1
    assert metrics_snapshot["updated"] == 1
    assert metrics_snapshot["rejected"] == 0
    assert metrics_snapshot["rejected_rate"] == 0.0
    assert metrics_snapshot["policy_reasons"] == {}
    assert len(metrics_snapshot["audit_recent"]) == 1
    event = metrics_snapshot["audit_recent"][0]
    assert event["trace_id"] == "trace-doc-routes"
    assert event["client_id"] == "198.51.100.77"
    assert event["matter_id"] == matter_id
    assert event["forum"] == "rpd"
    assert event["file_id"] == file_id
    assert event["previous_classification"] == "notice_of_application"
    assert event["new_classification"] == "disclosure_package"
    assert event["outcome"] == "updated"


def test_documents_classification_override_rejects_invalid_classification_and_records_audit() -> None:
    local_client, request_metrics = _documents_test_harness()
    matter_id = "matter-classification-override-invalid"
    intake_response = local_client.post(
        "/api/documents/intake",
        data={"forum": "rpd", "matter_id": matter_id},
        files=[
            ("files", ("uploaded.pdf", _pdf_payload("Uploaded document"), "application/pdf")),
        ],
    )
    assert intake_response.status_code == 200
    file_id = intake_response.json()["results"][0]["file_id"]

    override_response = local_client.patch(
        f"/api/documents/matters/{matter_id}/classification",
        json={"file_id": file_id, "classification": "not-a-known-document-type"},
    )
    assert override_response.status_code == 422
    assert (
        override_response.json()["error"]["policy_reason"]
        == "document_classification_invalid"
    )

    metrics_snapshot = request_metrics.snapshot()["document_classification_override"]
    assert metrics_snapshot["attempts"] == 1
    assert metrics_snapshot["updated"] == 0
    assert metrics_snapshot["rejected"] == 1
    assert metrics_snapshot["rejected_rate"] == pytest.approx(1.0)
    assert metrics_snapshot["policy_reasons"]["document_classification_invalid"] == 1
    assert len(metrics_snapshot["audit_recent"]) == 1
    event = metrics_snapshot["audit_recent"][0]
    assert event["outcome"] == "rejected"
    assert event["file_id"] == file_id
    assert event["new_classification"] == "not-a-known-document-type"
    assert event["policy_reason"] == "document_classification_invalid"


def test_documents_classification_override_rejects_missing_file_and_records_audit() -> None:
    local_client, request_metrics = _documents_test_harness()
    matter_id = "matter-classification-override-missing-file"
    intake_response = local_client.post(
        "/api/documents/intake",
        data={"forum": "rpd", "matter_id": matter_id},
        files=[
            ("files", ("uploaded.pdf", _pdf_payload("Uploaded document"), "application/pdf")),
        ],
    )
    assert intake_response.status_code == 200

    override_response = local_client.patch(
        f"/api/documents/matters/{matter_id}/classification",
        json={"file_id": "unknown-file-id", "classification": "disclosure_package"},
    )
    assert override_response.status_code == 404
    assert override_response.json()["error"]["policy_reason"] == "document_file_not_found"

    metrics_snapshot = request_metrics.snapshot()["document_classification_override"]
    assert metrics_snapshot["attempts"] == 1
    assert metrics_snapshot["updated"] == 0
    assert metrics_snapshot["rejected"] == 1
    assert metrics_snapshot["policy_reasons"]["document_file_not_found"] == 1
    event = metrics_snapshot["audit_recent"][0]
    assert event["matter_id"] == matter_id
    assert event["forum"] == "rpd"
    assert event["file_id"] == "unknown-file-id"
    assert event["new_classification"] == "disclosure_package"
    assert event["outcome"] == "rejected"
    assert event["policy_reason"] == "document_file_not_found"


def test_documents_classification_override_rejects_missing_matter_and_records_audit() -> None:
    local_client, request_metrics = _documents_test_harness()
    matter_id = "matter-classification-override-missing-matter"

    override_response = local_client.patch(
        f"/api/documents/matters/{matter_id}/classification",
        json={"file_id": "file-unknown", "classification": "disclosure_package"},
    )
    assert override_response.status_code == 404
    assert (
        override_response.json()["error"]["policy_reason"]
        == "document_matter_not_found"
    )

    metrics_snapshot = request_metrics.snapshot()["document_classification_override"]
    assert metrics_snapshot["attempts"] == 1
    assert metrics_snapshot["updated"] == 0
    assert metrics_snapshot["rejected"] == 1
    assert metrics_snapshot["policy_reasons"]["document_matter_not_found"] == 1
    event = metrics_snapshot["audit_recent"][0]
    assert event["matter_id"] == matter_id
    assert event["outcome"] == "rejected"
    assert event["policy_reason"] == "document_matter_not_found"


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


def test_documents_package_download_returns_pdf_when_compiled_available(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("IMMCAD_ENABLE_COMPILED_PDF", "1")
    matter_id = "matter-route-download-ready"
    intake_response = client.post(
        "/api/documents/intake",
        data={"forum": "rpd", "matter_id": matter_id},
        files=[
            (
                "files",
                (
                    "disclosure.pdf",
                    _pdf_payload("Document disclosure package for tribunal review."),
                    "application/pdf",
                ),
            )
        ],
    )
    assert intake_response.status_code == 200

    package_response = client.post(f"/api/documents/matters/{matter_id}/package")
    assert package_response.status_code == 200

    download_response = client.get(f"/api/documents/matters/{matter_id}/package/download")
    assert download_response.status_code == 200
    assert download_response.headers["content-type"].startswith("application/pdf")
    assert "attachment;" in download_response.headers["content-disposition"]
    assert f"{matter_id}-compiled-binder.pdf" in download_response.headers["content-disposition"]
    assert download_response.content.startswith(b"%PDF")
    assert "x-trace-id" in download_response.headers


def test_documents_package_download_blocks_when_not_ready() -> None:
    matter_id = "matter-route-download-not-ready"
    intake_response = client.post(
        "/api/documents/intake",
        data={"forum": "federal_court_jr", "matter_id": matter_id},
        files=[
            ("files", ("notice.pdf", _pdf_payload("Notice of Application"), "application/pdf")),
        ],
    )
    assert intake_response.status_code == 200

    download_response = client.get(f"/api/documents/matters/{matter_id}/package/download")
    assert download_response.status_code == 409
    body = download_response.json()
    assert body["error"]["code"] == "POLICY_BLOCKED"
    assert body["error"]["policy_reason"] == "document_package_not_ready"
    assert "x-trace-id" in download_response.headers


def test_documents_package_download_blocks_when_compiled_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("IMMCAD_ENABLE_COMPILED_PDF", "0")
    matter_id = "matter-route-download-unavailable"
    intake_response = client.post(
        "/api/documents/intake",
        data={"forum": "rpd", "matter_id": matter_id},
        files=[
            (
                "files",
                (
                    "disclosure.pdf",
                    _pdf_payload("Document disclosure package for tribunal review."),
                    "application/pdf",
                ),
            )
        ],
    )
    assert intake_response.status_code == 200

    download_response = client.get(f"/api/documents/matters/{matter_id}/package/download")
    assert download_response.status_code == 409
    body = download_response.json()
    assert body["error"]["code"] == "POLICY_BLOCKED"
    assert body["error"]["policy_reason"] == "document_compiled_artifact_unavailable"
    assert "x-trace-id" in download_response.headers


def test_documents_package_download_returns_not_found_for_unknown_matter() -> None:
    response = client.get("/api/documents/matters/matter-route-missing/package/download")

    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "SOURCE_UNAVAILABLE"
    assert body["error"]["policy_reason"] == "document_matter_not_found"


def test_documents_package_download_not_found_records_compilation_audit_event() -> None:
    local_client, request_metrics = _documents_test_harness()
    missing_matter_id = "matter-route-download-missing-telemetry"

    response = local_client.get(
        f"/api/documents/matters/{missing_matter_id}/package/download"
    )

    assert response.status_code == 404
    metrics_snapshot = request_metrics.snapshot()["document_compilation"]
    assert metrics_snapshot["attempts"] == 1
    assert metrics_snapshot["compiled"] == 0
    assert metrics_snapshot["blocked"] == 1
    assert metrics_snapshot["policy_reasons"]["document_matter_not_found"] == 1
    assert len(metrics_snapshot["audit_recent"]) == 1
    event = metrics_snapshot["audit_recent"][0]
    assert event["trace_id"] == "trace-doc-routes"
    assert event["client_id"] == "198.51.100.77"
    assert event["matter_id"] == missing_matter_id
    assert event["route"] == "package_download"
    assert event["http_status"] == 404
    assert event["outcome"] == "blocked"
    assert event["policy_reason"] == "document_matter_not_found"
    assert "forum" not in event


def test_documents_package_routes_record_compilation_metrics_and_audit_events() -> None:
    local_client, request_metrics = _documents_test_harness()
    missing_matter_id = "matter-route-compilation-missing"
    blocked_matter_id = "matter-route-compilation-blocked"

    missing_package_response = local_client.post(
        f"/api/documents/matters/{missing_matter_id}/package"
    )
    assert missing_package_response.status_code == 404

    intake_response = local_client.post(
        "/api/documents/intake",
        data={"forum": "federal_court_jr", "matter_id": blocked_matter_id},
        files=[
            ("files", ("notice.pdf", _pdf_payload("Notice of Application"), "application/pdf")),
        ],
    )
    assert intake_response.status_code == 200

    blocked_package_response = local_client.post(
        f"/api/documents/matters/{blocked_matter_id}/package"
    )
    assert blocked_package_response.status_code == 409

    metrics_snapshot = request_metrics.snapshot()["document_compilation"]
    assert metrics_snapshot["attempts"] == 2
    assert metrics_snapshot["compiled"] == 0
    assert metrics_snapshot["blocked"] == 2
    assert metrics_snapshot["policy_reasons"]["document_matter_not_found"] == 1
    assert metrics_snapshot["policy_reasons"]["document_package_not_ready"] == 1
    assert len(metrics_snapshot["audit_recent"]) == 2

    missing_event, blocked_event = metrics_snapshot["audit_recent"]
    assert missing_event["outcome"] == "blocked"
    assert missing_event["trace_id"] == "trace-doc-routes"
    assert missing_event["client_id"] == "198.51.100.77"
    assert missing_event["matter_id"] == missing_matter_id
    assert missing_event["route"] == "package"
    assert missing_event["http_status"] == 404
    assert missing_event["policy_reason"] == "document_matter_not_found"
    assert "forum" not in missing_event

    assert blocked_event["outcome"] == "blocked"
    assert blocked_event["trace_id"] == "trace-doc-routes"
    assert blocked_event["client_id"] == "198.51.100.77"
    assert blocked_event["matter_id"] == blocked_matter_id
    assert blocked_event["forum"] == "federal_court_jr"
    assert blocked_event["route"] == "package"
    assert blocked_event["http_status"] == 409
    assert blocked_event["policy_reason"] == "document_package_not_ready"


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
    assert metrics_snapshot["files_total"] == 2
    assert metrics_snapshot["ocr_warning_files"] == 0
    assert metrics_snapshot["ocr_warning_rate"] == 0.0
    assert metrics_snapshot["parser_failure_files"] == 0
    assert metrics_snapshot["parser_failure_rate"] == 0.0
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
    assert metrics_snapshot["files_total"] == expected_file_count
    assert metrics_snapshot["ocr_warning_files"] == 0
    assert metrics_snapshot["parser_failure_files"] == 0
    assert metrics_snapshot["policy_reasons"][expected_policy_reason] == 1
    assert len(metrics_snapshot["audit_recent"]) == 1
    audit_event = metrics_snapshot["audit_recent"][0]
    assert audit_event["trace_id"] == "trace-doc-routes"
    assert audit_event["client_id"] == "198.51.100.77"
    assert audit_event["file_count"] == expected_file_count
    assert audit_event["outcome"] == "rejected"
    assert audit_event["policy_reason"] == expected_policy_reason


def test_documents_intake_rejects_invalid_submission_channel() -> None:
    local_client, _ = _documents_test_harness()
    response = local_client.post(
        "/api/documents/intake",
        data={
            "forum": "federal_court_jr",
            "matter_id": "matter-invalid-channel",
            "submission_channel": "courier_pigeon",
        },
        files=[
            ("files", ("notice.pdf", _pdf_payload("Notice of Application"), "application/pdf")),
        ],
    )

    assert response.status_code == 422
    assert response.json()["error"]["policy_reason"] == "document_submission_channel_invalid"


def test_documents_intake_rejects_when_submission_channel_file_count_limit_is_exceeded() -> None:
    local_client, _ = _documents_test_harness(upload_max_files=25)
    response = local_client.post(
        "/api/documents/intake",
        data={
            "forum": "federal_court_jr",
            "matter_id": "matter-channel-file-count",
            "submission_channel": "fax",
        },
        files=[
            ("files", ("first.pdf", _pdf_payload("first"), "application/pdf")),
            ("files", ("second.pdf", _pdf_payload("second"), "application/pdf")),
        ],
    )

    assert response.status_code == 422
    assert (
        response.json()["error"]["policy_reason"]
        == "document_submission_channel_file_count_exceeded"
    )


def test_documents_intake_adds_near_limit_warning_for_submission_channel() -> None:
    local_client, _ = _documents_test_harness(upload_max_files=25)
    files = [
        ("files", (f"doc-{index}.pdf", _pdf_payload(f"doc-{index}"), "application/pdf"))
        for index in range(1, 9)
    ]
    response = local_client.post(
        "/api/documents/intake",
        data={
            "forum": "federal_court_jr",
            "matter_id": "matter-channel-near-limit",
            "submission_channel": "email",
        },
        files=files,
    )

    assert response.status_code == 200
    assert "submission_channel_near_file_limit" in response.json()["warnings"]


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
    assert body["results"][1]["issue_details"][0]["code"] == "unsupported_file_type"
    assert body["results"][1]["issue_details"][0]["severity"] == "error"
    assert body["results"][1]["issue_details"][0]["remediation"]
    assert body["results"][2]["issue_details"][0]["code"] == "upload_size_exceeded"
    assert body["results"][2]["issue_details"][0]["severity"] == "error"
    assert body["results"][2]["issue_details"][0]["remediation"]

    metrics_snapshot = request_metrics.snapshot()["document_intake"]
    assert metrics_snapshot["attempts"] == 1
    assert metrics_snapshot["accepted"] == 1
    assert metrics_snapshot["rejected"] == 0
    assert metrics_snapshot["files_total"] == 3
    assert metrics_snapshot["ocr_warning_files"] == 0
    assert metrics_snapshot["ocr_warning_rate"] == 0.0
    assert metrics_snapshot["parser_failure_files"] == 0
    assert metrics_snapshot["parser_failure_rate"] == 0.0
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
    assert metrics_snapshot["files_total"] == 2
    assert metrics_snapshot["ocr_warning_files"] == 0
    assert metrics_snapshot["ocr_warning_rate"] == 0.0
    assert metrics_snapshot["parser_failure_files"] == 0
    assert metrics_snapshot["parser_failure_rate"] == 0.0
    assert metrics_snapshot["policy_reasons"]["document_all_files_failed"] == 1
    assert metrics_snapshot["audit_recent"][0]["outcome"] == "rejected"
    assert (
        metrics_snapshot["audit_recent"][0]["policy_reason"]
        == "document_all_files_failed"
    )


def test_documents_readiness_warnings_are_deduplicated() -> None:
    local_client, request_metrics = _documents_test_harness(
        intake_service=_WarningStubIntakeService()
    )
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
    intake_metrics = request_metrics.snapshot()["document_intake"]
    assert intake_metrics["files_total"] == 2
    assert intake_metrics["ocr_warning_files"] == 2
    assert intake_metrics["ocr_warning_rate"] == pytest.approx(1.0)
    assert intake_metrics["parser_failure_files"] == 0
    assert intake_metrics["parser_failure_rate"] == 0.0


def test_documents_intake_records_parser_failure_metrics() -> None:
    local_client, request_metrics = _documents_test_harness(
        intake_service=_UnreadableStubIntakeService()
    )
    response = local_client.post(
        "/api/documents/intake",
        data={"forum": "federal_court_jr", "matter_id": "matter-parser-failure-telemetry"},
        files=[
            ("files", ("scan.pdf", _pdf_payload("Unreadable scan payload"), "application/pdf")),
        ],
    )

    assert response.status_code == 200
    metrics_snapshot = request_metrics.snapshot()["document_intake"]
    assert metrics_snapshot["attempts"] == 1
    assert metrics_snapshot["accepted"] == 0
    assert metrics_snapshot["rejected"] == 1
    assert metrics_snapshot["files_total"] == 1
    assert metrics_snapshot["ocr_warning_files"] == 0
    assert metrics_snapshot["parser_failure_files"] == 1
    assert metrics_snapshot["parser_failure_rate"] == pytest.approx(1.0)
    assert metrics_snapshot["policy_reasons"]["document_all_files_failed"] == 1
    assert metrics_snapshot["audit_recent"][0]["parser_failure_files"] == 1


def test_documents_intake_includes_remediation_for_unreadable_failures() -> None:
    local_client, _ = _documents_test_harness(
        intake_service=_ValueErrorIntakeService()
    )
    response = local_client.post(
        "/api/documents/intake",
        data={"forum": "federal_court_jr", "matter_id": "matter-unreadable-remediation"},
        files=[
            ("files", ("scan.pdf", _pdf_payload("Unreadable scan payload"), "application/pdf")),
        ],
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body["results"]) == 1
    assert body["results"][0]["quality_status"] == "failed"
    assert body["results"][0]["issues"] == ["file_unreadable"]
    assert body["results"][0]["issue_details"][0]["code"] == "file_unreadable"
    assert body["results"][0]["issue_details"][0]["severity"] == "error"
    assert body["results"][0]["issue_details"][0]["remediation"]


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
    body = readiness_response.json()
    requirement_statuses = body["requirement_statuses"]
    status_by_item = {item["item"]: item for item in requirement_statuses}
    assert status_by_item["disclosure_package"]["status"] == "present"
    assert status_by_item["disclosure_package"]["rule_scope"] == "base"
    assert status_by_item["translator_declaration"]["status"] == "missing"
    assert status_by_item["translator_declaration"]["rule_scope"] == "conditional"
    assert status_by_item["translator_declaration"]["reason"]
    assert body["toc_entries"]
    assert body["pagination_summary"]["total_documents"] >= 1
    assert body["compilation_profile"]["id"]
    assert body["compilation_output_mode"] == "metadata_plan_only"


def test_documents_deadline_miss_blocks_readiness_and_package_generation() -> None:
    local_client, _ = _documents_test_harness(
        intake_service=_MappedClassificationIntakeService(
            {
                "appeal-record.pdf": "appeal_record",
                "decision.pdf": "decision_under_review",
                "memorandum.pdf": "memorandum",
            }
        )
    )
    matter_id = "matter-rad-deadline-blocked"
    intake_response = local_client.post(
        "/api/documents/intake",
        data={
            "forum": "rad",
            "matter_id": matter_id,
            "decision_date": "2026-02-01",
            "filing_date": "2026-02-20",
        },
        files=[
            ("files", ("appeal-record.pdf", _pdf_payload("Appeal record"), "application/pdf")),
            (
                "files",
                ("decision.pdf", _pdf_payload("Decision under review"), "application/pdf"),
            ),
            ("files", ("memorandum.pdf", _pdf_payload("Memorandum"), "application/pdf")),
        ],
    )
    assert intake_response.status_code == 200
    assert "filing_deadline_expired" in intake_response.json()["blocking_issues"]

    readiness_response = local_client.get(f"/api/documents/matters/{matter_id}/readiness")
    assert readiness_response.status_code == 200
    assert "filing_deadline_expired" in readiness_response.json()["blocking_issues"]

    package_response = local_client.post(f"/api/documents/matters/{matter_id}/package")
    assert package_response.status_code == 409
    assert package_response.json()["error"]["policy_reason"] == "document_package_not_ready"


def test_documents_deadline_override_allows_package_generation_with_warning() -> None:
    local_client, _ = _documents_test_harness(
        intake_service=_MappedClassificationIntakeService(
            {
                "appeal-record.pdf": "appeal_record",
                "decision.pdf": "decision_under_review",
                "memorandum.pdf": "memorandum",
            }
        )
    )
    matter_id = "matter-rad-deadline-override"
    intake_response = local_client.post(
        "/api/documents/intake",
        data={
            "forum": "rad",
            "matter_id": matter_id,
            "decision_date": "2026-02-01",
            "filing_date": "2026-02-20",
            "deadline_override_reason": "Extension granted by tribunal registry.",
        },
        files=[
            ("files", ("appeal-record.pdf", _pdf_payload("Appeal record"), "application/pdf")),
            (
                "files",
                ("decision.pdf", _pdf_payload("Decision under review"), "application/pdf"),
            ),
            ("files", ("memorandum.pdf", _pdf_payload("Memorandum"), "application/pdf")),
        ],
    )
    assert intake_response.status_code == 200
    assert "filing_deadline_override_applied" in intake_response.json()["warnings"]
    assert "filing_deadline_expired" not in intake_response.json()["blocking_issues"]

    package_response = local_client.post(f"/api/documents/matters/{matter_id}/package")
    assert package_response.status_code == 200
    assert package_response.json()["is_ready"] is True


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
