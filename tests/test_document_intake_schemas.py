from __future__ import annotations

from immcad_api.schemas import (
    DocumentIntakeResult,
    DocumentPackageResponse,
    DocumentReadinessResponse,
)


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
    )

    assert response.is_ready is False
    assert response.blocking_issues == ["illegible_pages"]
    assert response.requirement_statuses[0].rule_scope == "base"


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
    )

    assert package.table_of_contents[0].document_type == "notice_of_application"
    assert package.disclosure_checklist[0].status == "missing"
    assert package.disclosure_checklist[0].rule_scope == "base"
