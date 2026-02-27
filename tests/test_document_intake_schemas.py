from __future__ import annotations

from datetime import date

import pytest

from immcad_api.schemas import (
    DocumentIntakeInitRequest,
    DocumentIntakeResult,
    DocumentIntakeResponse,
    DocumentPackageResponse,
    DocumentReadinessResponse,
)


def _classification_candidates_field_name() -> str:
    for field_name in ("classification_candidates", "candidates"):
        if field_name in DocumentIntakeResult.model_fields:
            return field_name
    raise AssertionError("expected classification candidates field on DocumentIntakeResult")


def _classification_confidence_field_name() -> str:
    for field_name in (
        "classification_confidence_bucket",
        "confidence_bucket",
        "classification_confidence",
    ):
        if field_name in DocumentIntakeResult.model_fields:
            return field_name
    raise AssertionError("expected classification confidence field on DocumentIntakeResult")


def test_document_intake_result_requires_quality_and_classification() -> None:
    result = DocumentIntakeResult(
        file_id="file-1",
        original_filename="scan.pdf",
        normalized_filename="affidavit-smith-2026-01-01.pdf",
        classification="affidavit",
        quality_status="needs_review",
        issues=["ocr_low_confidence"],
    )

    assert result.classification == "affidavit"
    assert result.quality_status == "needs_review"


def test_document_intake_result_exposes_compilation_metadata_defaults() -> None:
    candidates_field_name = _classification_candidates_field_name()
    confidence_field_name = _classification_confidence_field_name()
    result = DocumentIntakeResult(
        file_id="file-2",
        original_filename="scan.pdf",
        normalized_filename="unclassified-scan-2026-01-01-file-2.pdf",
        classification="unclassified",
        quality_status="failed",
        issues=["file_unreadable"],
    )

    assert result.total_pages == 0
    assert result.page_char_counts == []
    assert result.file_hash is None
    assert result.ocr_confidence_class is None
    assert result.ocr_capability is None
    assert result.issue_details == []
    assert getattr(result, candidates_field_name) == []
    assert (
        getattr(result, confidence_field_name)
        == DocumentIntakeResult.model_fields[confidence_field_name].default
    )


def test_document_intake_result_accepts_explicit_classification_fields() -> None:
    candidates_field_name = _classification_candidates_field_name()
    confidence_field_name = _classification_confidence_field_name()
    result = DocumentIntakeResult(
        file_id="file-2b",
        original_filename="scan.pdf",
        normalized_filename="affidavit-scan-2026-01-01-file-2b.pdf",
        classification="affidavit",
        quality_status="processed",
        issues=[],
        **{
            candidates_field_name: [],
            confidence_field_name: "high",
        },
    )

    assert getattr(result, candidates_field_name) == []
    assert getattr(result, confidence_field_name) == "high"


def test_document_intake_result_accepts_structured_issue_details() -> None:
    result = DocumentIntakeResult(
        file_id="file-2c",
        original_filename="scan.pdf",
        normalized_filename="unclassified-scan-2026-01-01-file-2c.pdf",
        classification="unclassified",
        quality_status="failed",
        issues=["file_unreadable"],
        issue_details=[
            {
                "code": "file_unreadable",
                "message": "Unable to read this file.",
                "severity": "error",
                "remediation": "Re-export the file as a PDF and upload again.",
            }
        ],
    )

    assert result.issue_details
    assert result.issue_details[0].code == "file_unreadable"
    assert result.issue_details[0].severity == "error"
    assert result.issue_details[0].remediation


@pytest.mark.parametrize(
    "profile_id",
    [
        "federal_court_jr_leave",
        "federal_court_jr_hearing",
        "rpd",
        "rad",
        "id",
        "iad",
        "iad_sponsorship",
        "iad_residency",
        "iad_admissibility",
        "ircc_pr_card_renewal",
    ],
)
def test_document_intake_init_request_accepts_compilation_profile_literals(
    profile_id: str,
) -> None:
    request = DocumentIntakeInitRequest(
        forum="federal_court_jr",
        compilation_profile_id=profile_id,
    )

    assert request.compilation_profile_id == profile_id


@pytest.mark.parametrize(
    "profile_id",
    [
        "federal_court_jr_leave",
        "federal_court_jr_hearing",
        "rpd",
        "rad",
        "id",
        "iad",
        "iad_sponsorship",
        "iad_residency",
        "iad_admissibility",
        "ircc_pr_card_renewal",
    ],
)
def test_document_intake_response_accepts_compilation_profile_literals(
    profile_id: str,
) -> None:
    response = DocumentIntakeResponse(
        matter_id="matter-1",
        forum="federal_court_jr",
        compilation_profile_id=profile_id,
        results=[],
    )

    assert response.compilation_profile_id == profile_id


def test_document_intake_schemas_allow_optional_compilation_profile_id() -> None:
    request = DocumentIntakeInitRequest(forum="rpd")
    explicit_none_request = DocumentIntakeInitRequest(
        forum="rpd",
        compilation_profile_id=None,
    )
    response = DocumentIntakeResponse(
        matter_id="matter-1",
        forum="rpd",
        results=[],
    )
    explicit_none_response = DocumentIntakeResponse(
        matter_id="matter-1",
        forum="rpd",
        compilation_profile_id=None,
        results=[],
    )

    assert request.compilation_profile_id is None
    assert explicit_none_request.compilation_profile_id is None
    assert response.compilation_profile_id is None
    assert explicit_none_response.compilation_profile_id is None


def test_document_intake_init_request_accepts_ircc_application_forum() -> None:
    request = DocumentIntakeInitRequest(forum="ircc_application")

    assert request.forum == "ircc_application"


def test_document_intake_init_request_accepts_submission_channel_and_filing_dates() -> None:
    request = DocumentIntakeInitRequest(
        forum="rad",
        submission_channel="email",
        decision_date=date(2026, 2, 1),
        filing_date=date(2026, 2, 12),
    )

    assert request.submission_channel == "email"
    assert request.decision_date == date(2026, 2, 1)
    assert request.filing_date == date(2026, 2, 12)


def test_document_intake_init_request_rejects_service_date_after_hearing_date() -> None:
    with pytest.raises(ValueError, match="service_date must be <= hearing_date"):
        DocumentIntakeInitRequest(
            forum="rpd",
            service_date=date(2026, 3, 20),
            hearing_date=date(2026, 3, 10),
        )


def test_document_intake_init_request_rejects_blank_deadline_override_reason() -> None:
    with pytest.raises(ValueError, match="deadline_override_reason cannot be blank"):
        DocumentIntakeInitRequest(
            forum="rad",
            deadline_override_reason="   ",
        )


def test_readiness_response_exposes_blocking_issues() -> None:
    response = DocumentReadinessResponse(
        matter_id="matter-1",
        forum="federal_court_jr",
        is_ready=False,
        missing_required_items=["memorandum"],
        blocking_issues=["illegible_pages"],
        warnings=["ocr_low_confidence"],
        requirement_statuses=[
            {
                "item": "memorandum",
                "status": "missing",
                "rule_scope": "base",
                "reason": "Memorandum of argument is required.",
            }
        ],
        toc_entries=[
            {
                "position": 1,
                "document_type": "notice_of_application",
                "filename": "notice.pdf",
                "start_page": 1,
                "end_page": 3,
            }
        ],
        pagination_summary={
            "total_documents": 1,
            "total_pages": 3,
            "last_assigned_page": 3,
        },
        rule_violations=[
            {
                "violation_code": "missing_memorandum",
                "severity": "blocking",
                "rule_source_url": "https://example.test/rules/memorandum",
            }
        ],
        compilation_profile={"id": "ca-imm-mvp", "version": "2026.02"},
        record_sections=[
            {
                "section_id": "fc_jr_leave_core_documents",
                "title": "Leave Materials",
                "instructions": "Include leave materials in filing order.",
                "document_types": [
                    "notice_of_application",
                    "decision_under_review",
                    "affidavit",
                    "memorandum",
                ],
            }
        ],
    )

    assert response.is_ready is False
    assert response.blocking_issues == ["illegible_pages"]
    assert response.requirement_statuses[0].rule_scope == "base"
    assert response.toc_entries[0].start_page == 1
    assert response.pagination_summary.total_pages == 3
    assert response.rule_violations[0].rule_source_url
    assert response.compilation_profile.id == "ca-imm-mvp"
    assert response.compilation_output_mode == "metadata_plan_only"
    assert response.compiled_artifact is None
    assert response.record_sections[0].section_id == "fc_jr_leave_core_documents"
    assert response.record_sections[0].section_status == "present"
    assert response.record_sections[0].slot_statuses == []
    assert response.record_sections[0].missing_document_types == []
    assert response.record_sections[0].missing_reasons == []
    assert list(response.record_sections[0].document_types) == [
        "notice_of_application",
        "decision_under_review",
        "affidavit",
        "memorandum",
    ]


def test_readiness_response_defaults_record_sections_to_empty_list() -> None:
    response = DocumentReadinessResponse(
        matter_id="matter-1",
        forum="rpd",
        is_ready=True,
    )

    assert response.record_sections == []


def test_readiness_response_accepts_explicit_compilation_output_mode() -> None:
    response = DocumentReadinessResponse(
        matter_id="matter-1",
        forum="federal_court_jr",
        is_ready=True,
        compilation_output_mode="compiled_pdf",
    )

    assert response.compilation_output_mode == "compiled_pdf"


def test_readiness_response_accepts_explicit_compiled_artifact_metadata() -> None:
    response = DocumentReadinessResponse(
        matter_id="matter-1",
        forum="federal_court_jr",
        is_ready=True,
        compilation_output_mode="compiled_pdf",
        compiled_artifact={
            "filename": "matter-1-compiled-binder.pdf",
            "byte_size": 1024,
            "sha256": "a" * 64,
            "page_count": 5,
        },
    )

    assert response.compilation_output_mode == "compiled_pdf"
    assert response.compiled_artifact is not None
    assert response.compiled_artifact.filename == "matter-1-compiled-binder.pdf"
    assert response.compiled_artifact.byte_size == 1024
    assert response.compiled_artifact.sha256 == "a" * 64
    assert response.compiled_artifact.page_count == 5


def test_document_package_response_contains_toc_and_cover_letter() -> None:
    package = DocumentPackageResponse(
        matter_id="matter-1",
        forum="federal_court_jr",
        is_ready=False,
        table_of_contents=[
            {
                "position": 1,
                "document_type": "notice_of_application",
                "filename": "notice.pdf",
            }
        ],
        disclosure_checklist=[
            {
                "item": "memorandum",
                "status": "missing",
                "rule_scope": "base",
                "reason": "Memorandum of argument is required.",
            },
        ],
        cover_letter_draft="Draft text",
        toc_entries=[
            {
                "position": 1,
                "document_type": "notice_of_application",
                "filename": "notice.pdf",
                "start_page": 1,
                "end_page": 4,
            }
        ],
        pagination_summary={
            "total_documents": 1,
            "total_pages": 4,
            "last_assigned_page": 4,
        },
        rule_violations=[
            {
                "violation_code": "missing_memorandum",
                "severity": "blocking",
                "rule_source_url": "https://example.test/rules/memorandum",
            }
        ],
        compilation_profile={"id": "ca-imm-mvp", "version": "2026.02"},
        record_sections=[
            {
                "section_id": "fc_jr_leave_core_documents",
                "title": "Leave Materials",
                "instructions": "Include leave materials in filing order.",
                "document_types": [
                    "notice_of_application",
                    "decision_under_review",
                    "affidavit",
                    "memorandum",
                ],
            }
        ],
    )

    assert package.table_of_contents[0].document_type == "notice_of_application"
    assert package.disclosure_checklist[0].status == "missing"
    assert package.disclosure_checklist[0].rule_scope == "base"
    assert package.toc_entries[0].end_page == 4
    assert package.pagination_summary.total_documents == 1
    assert package.rule_violations[0].rule_source_url
    assert package.compilation_profile.version == "2026.02"
    assert package.compilation_output_mode == "metadata_plan_only"
    assert package.compiled_artifact is None
    assert package.record_sections[0].section_id == "fc_jr_leave_core_documents"
    assert package.record_sections[0].section_status == "present"
    assert package.record_sections[0].slot_statuses == []
    assert package.record_sections[0].missing_document_types == []
    assert package.record_sections[0].missing_reasons == []
    assert list(package.record_sections[0].document_types) == [
        "notice_of_application",
        "decision_under_review",
        "affidavit",
        "memorandum",
    ]


def test_document_package_response_defaults_record_sections_to_empty_list() -> None:
    package = DocumentPackageResponse(
        matter_id="matter-1",
        forum="rpd",
        is_ready=True,
    )

    assert package.record_sections == []


def test_document_package_response_accepts_explicit_compilation_output_mode() -> None:
    package = DocumentPackageResponse(
        matter_id="matter-1",
        forum="federal_court_jr",
        is_ready=True,
        compilation_output_mode="compiled_pdf",
    )

    assert package.compilation_output_mode == "compiled_pdf"


def test_document_package_response_accepts_explicit_compiled_artifact_metadata() -> None:
    package = DocumentPackageResponse(
        matter_id="matter-1",
        forum="federal_court_jr",
        is_ready=True,
        compilation_output_mode="compiled_pdf",
        compiled_artifact={
            "filename": "matter-1-compiled-binder.pdf",
            "byte_size": 2048,
            "sha256": "b" * 64,
            "page_count": 8,
        },
    )

    assert package.compilation_output_mode == "compiled_pdf"
    assert package.compiled_artifact is not None
    assert package.compiled_artifact.filename == "matter-1-compiled-binder.pdf"
    assert package.compiled_artifact.byte_size == 2048
    assert package.compiled_artifact.sha256 == "b" * 64
    assert package.compiled_artifact.page_count == 8
