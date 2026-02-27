from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from immcad_api.api.routes.documents import build_documents_router
from immcad_api.schemas import DocumentIntakeResult, DocumentPackageResponse


class _CompilationIntakeService:
    _CLASSIFICATION_BY_FILENAME = {
        "notice.pdf": ("notice_of_application", 2),
        "decision.pdf": ("decision_under_review", 3),
        "affidavit.pdf": ("affidavit", 2),
        "memorandum.pdf": ("memorandum", 4),
    }

    def process_file(
        self,
        *,
        original_filename: str,
        payload_bytes: bytes,
    ) -> DocumentIntakeResult:
        del payload_bytes
        classification, total_pages = self._CLASSIFICATION_BY_FILENAME.get(
            original_filename,
            ("unclassified", 1),
        )
        return DocumentIntakeResult(
            file_id=f"file-{original_filename}",
            original_filename=original_filename,
            normalized_filename=original_filename,
            classification=classification,
            quality_status="processed",
            issues=[],
            total_pages=total_pages,
            page_char_counts=[
                {"page_number": page_number, "extracted_char_count": 100}
                for page_number in range(1, total_pages + 1)
            ],
            file_hash=f"hash-{original_filename}",
            ocr_confidence_class="high",
            ocr_capability="tesseract_available",
        )


class _BlockingViolationPackageService:
    def build_package(
        self,
        *,
        matter_id: str,
        forum: str,
        intake_results: list[DocumentIntakeResult],
    ) -> DocumentPackageResponse:
        del forum, intake_results
        return DocumentPackageResponse(
            matter_id=matter_id,
            forum="federal_court_jr",
            is_ready=True,
            table_of_contents=[
                {
                    "position": 1,
                    "document_type": "notice_of_application",
                    "filename": "notice.pdf",
                }
            ],
            disclosure_checklist=[],
            cover_letter_draft="draft",
            toc_entries=[
                {
                    "position": 1,
                    "document_type": "notice_of_application",
                    "filename": "notice.pdf",
                    "start_page": 1,
                    "end_page": 2,
                }
            ],
            pagination_summary={
                "total_documents": 1,
                "total_pages": 2,
                "last_assigned_page": 2,
            },
            rule_violations=[
                {
                    "violation_code": "blocking_rule",
                    "severity": "blocking",
                    "rule_source_url": "https://example.test/rules/blocking",
                }
            ],
            compilation_profile={"id": "ca-imm-mvp", "version": "2026.02"},
        )


class _LegacySignaturePackageService:
    def build_package(
        self,
        *,
        matter_id: str,
        forum: str,
        intake_results: list[DocumentIntakeResult],
    ) -> DocumentPackageResponse:
        del forum, intake_results
        return DocumentPackageResponse(
            matter_id=matter_id,
            forum="federal_court_jr",
            is_ready=True,
            table_of_contents=[
                {
                    "position": 1,
                    "document_type": "notice_of_application",
                    "filename": "notice.pdf",
                }
            ],
            disclosure_checklist=[],
            cover_letter_draft="legacy-draft",
            toc_entries=[
                {
                    "position": 1,
                    "document_type": "notice_of_application",
                    "filename": "notice.pdf",
                    "start_page": 1,
                    "end_page": 1,
                }
            ],
            pagination_summary={
                "total_documents": 1,
                "total_pages": 1,
                "last_assigned_page": 1,
            },
            rule_violations=[],
            compilation_profile={"id": "legacy-signature-stub", "version": "2026.02"},
        )


def _client_with_services(
    *,
    intake_service: object | None = None,
    package_service: object | None = None,
) -> TestClient:
    app = FastAPI()

    @app.middleware("http")
    async def _request_context_middleware(request: Request, call_next):
        request.state.trace_id = "trace-compilation-routes"
        request.state.client_id = "198.51.100.88"
        return await call_next(request)

    app.include_router(
        build_documents_router(
            intake_service=intake_service or _CompilationIntakeService(),
            package_service=package_service,
        )
    )
    return TestClient(app)


def test_readiness_route_exposes_compilation_contract_fields() -> None:
    client = _client_with_services()
    matter_id = "matter-compilation-readiness"

    intake_response = client.post(
        "/api/documents/intake",
        data={"forum": "federal_court_jr", "matter_id": matter_id},
        files=[
            ("files", ("notice.pdf", b"%PDF-1.7", "application/pdf")),
            ("files", ("decision.pdf", b"%PDF-1.7", "application/pdf")),
        ],
    )
    assert intake_response.status_code == 200

    readiness_response = client.get(f"/api/documents/matters/{matter_id}/readiness")

    assert readiness_response.status_code == 200
    body = readiness_response.json()
    assert body["toc_entries"]
    assert body["toc_entries"][0]["start_page"] >= 1
    assert body["toc_entries"][0]["end_page"] >= body["toc_entries"][0]["start_page"]
    assert body["pagination_summary"]["total_pages"] >= 1
    assert body["rule_violations"]
    assert body["rule_violations"][0]["rule_source_url"]
    assert body["compilation_profile"]["id"]
    assert body["compilation_profile"]["version"]
    assert body["compilation_output_mode"] == "metadata_plan_only"
    assert body["record_sections"]
    assert body["record_sections"][0]["section_id"]
    assert body["record_sections"][0]["document_types"]
    assert body["record_sections"][0]["section_status"]
    assert "slot_statuses" in body["record_sections"][0]
    assert "missing_document_types" in body["record_sections"][0]
    assert "missing_reasons" in body["record_sections"][0]


def test_package_route_returns_compilation_contract_when_ready() -> None:
    client = _client_with_services()
    matter_id = "matter-compilation-package"

    intake_response = client.post(
        "/api/documents/intake",
        data={"forum": "federal_court_jr", "matter_id": matter_id},
        files=[
            ("files", ("notice.pdf", b"%PDF-1.7", "application/pdf")),
            ("files", ("decision.pdf", b"%PDF-1.7", "application/pdf")),
            ("files", ("affidavit.pdf", b"%PDF-1.7", "application/pdf")),
            ("files", ("memorandum.pdf", b"%PDF-1.7", "application/pdf")),
        ],
    )
    assert intake_response.status_code == 200

    package_response = client.post(f"/api/documents/matters/{matter_id}/package")

    assert package_response.status_code == 200
    body = package_response.json()
    assert body["table_of_contents"]
    assert body["toc_entries"]
    assert body["toc_entries"][0]["start_page"] == 1
    assert body["pagination_summary"]["total_documents"] == 4
    assert body["compilation_profile"]["id"]
    assert body["compilation_output_mode"] == "metadata_plan_only"
    assert body["record_sections"]
    assert body["record_sections"][0]["section_id"]
    assert body["record_sections"][0]["document_types"]
    assert body["record_sections"][0]["section_status"]
    assert "slot_statuses" in body["record_sections"][0]
    assert "missing_document_types" in body["record_sections"][0]
    assert "missing_reasons" in body["record_sections"][0]


def test_package_route_blocks_when_package_has_blocking_violation() -> None:
    client = _client_with_services(package_service=_BlockingViolationPackageService())
    matter_id = "matter-compilation-violation"

    intake_response = client.post(
        "/api/documents/intake",
        data={"forum": "federal_court_jr", "matter_id": matter_id},
        files=[
            ("files", ("notice.pdf", b"%PDF-1.7", "application/pdf")),
        ],
    )
    assert intake_response.status_code == 200

    package_response = client.post(f"/api/documents/matters/{matter_id}/package")

    assert package_response.status_code == 409
    assert package_response.json()["error"]["policy_reason"] == "document_package_not_ready"


def test_routes_support_legacy_package_stub_without_profile_methods() -> None:
    client = _client_with_services(package_service=_LegacySignaturePackageService())
    matter_id = "matter-compilation-legacy-signature"

    intake_response = client.post(
        "/api/documents/intake",
        data={
            "forum": "federal_court_jr",
            "matter_id": matter_id,
            "compilation_profile_id": "  LEGACY-PROFILE  ",
        },
        files=[
            ("files", ("notice.pdf", b"%PDF-1.7", "application/pdf")),
        ],
    )
    assert intake_response.status_code == 200
    assert intake_response.json()["compilation_profile_id"] is None

    readiness_response = client.get(f"/api/documents/matters/{matter_id}/readiness")
    assert readiness_response.status_code == 200
    assert readiness_response.json()["toc_entries"][0]["start_page"] == 1
    assert readiness_response.json()["record_sections"] == []

    package_response = client.post(f"/api/documents/matters/{matter_id}/package")
    assert package_response.status_code == 200
    assert package_response.json()["compilation_profile"]["id"] == "legacy-signature-stub"
    assert package_response.json()["record_sections"] == []

    download_response = client.get(
        f"/api/documents/matters/{matter_id}/package/download"
    )
    assert download_response.status_code == 409
    assert (
        download_response.json()["error"]["policy_reason"]
        == "document_compiled_artifact_unavailable"
    )
