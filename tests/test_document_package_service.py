from __future__ import annotations

from immcad_api.schemas import DocumentIntakeResult
from immcad_api.services.document_package_service import DocumentPackageService


def test_package_builder_generates_toc_ordered_by_rule_priority() -> None:
    service = DocumentPackageService()
    package = service.build_package(
        matter_id="matter-1",
        forum="federal_court_jr",
        intake_results=[
            DocumentIntakeResult(
                file_id="f02",
                original_filename="affidavit.pdf",
                normalized_filename="affidavit.pdf",
                classification="affidavit",
                quality_status="processed",
                issues=[],
            ),
            DocumentIntakeResult(
                file_id="f01",
                original_filename="notice.pdf",
                normalized_filename="notice.pdf",
                classification="notice_of_application",
                quality_status="processed",
                issues=[],
            ),
        ],
    )

    assert package.table_of_contents[0].document_type == "notice_of_application"


def test_package_builder_generates_cover_letter_draft_with_missing_items_note() -> None:
    service = DocumentPackageService()
    package = service.build_package(
        matter_id="matter-2",
        forum="federal_court_jr",
        intake_results=[
            DocumentIntakeResult(
                file_id="f01",
                original_filename="notice.pdf",
                normalized_filename="notice.pdf",
                classification="notice_of_application",
                quality_status="processed",
                issues=[],
            ),
        ],
    )

    assert "missing" in package.cover_letter_draft.lower()
    assert package.is_ready is False
