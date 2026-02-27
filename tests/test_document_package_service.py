from __future__ import annotations

from immcad_api.schemas import DocumentIntakeResult, DocumentQualityStatus
from immcad_api.services.document_package_service import DocumentPackageService


def _result(
    *,
    file_id: str,
    filename: str,
    classification: str,
    quality_status: DocumentQualityStatus = "processed",
    issues: list[str] | None = None,
) -> DocumentIntakeResult:
    return DocumentIntakeResult(
        file_id=file_id,
        original_filename=filename,
        normalized_filename=filename,
        classification=classification,
        quality_status=quality_status,
        issues=issues or [],
    )


def test_package_builder_generates_toc_ordered_by_rule_priority() -> None:
    service = DocumentPackageService()
    package = service.build_package(
        matter_id="matter-1",
        forum="federal_court_jr",
        intake_results=[
            _result(file_id="f02", filename="affidavit.pdf", classification="affidavit"),
            _result(
                file_id="f01",
                filename="notice.pdf",
                classification="notice_of_application",
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
            _result(
                file_id="f01",
                filename="notice.pdf",
                classification="notice_of_application",
            ),
        ],
    )

    assert "missing" in package.cover_letter_draft.lower()
    assert package.is_ready is False


def test_package_checklist_includes_translation_declaration_requirement_for_fc_jr() -> None:
    service = DocumentPackageService()
    package = service.build_package(
        matter_id="matter-translation-fc",
        forum="federal_court_jr",
        intake_results=[
            _result(
                file_id="f10",
                filename="notice.pdf",
                classification="notice_of_application",
            ),
            _result(
                file_id="f11",
                filename="decision.pdf",
                classification="decision_under_review",
            ),
            _result(
                file_id="f12",
                filename="affidavit.pdf",
                classification="affidavit",
            ),
            _result(
                file_id="f13",
                filename="memorandum.pdf",
                classification="memorandum",
            ),
            _result(
                file_id="f14",
                filename="translation.pdf",
                classification="translation",
            ),
        ],
    )

    checklist_by_item = {entry.item: entry.status for entry in package.disclosure_checklist}
    assert checklist_by_item["translator_declaration"] == "missing"
    assert package.is_ready is False
    metadata_by_item = {entry.item: entry for entry in package.disclosure_checklist}
    assert metadata_by_item["translator_declaration"].rule_scope == "conditional"
    assert metadata_by_item["translator_declaration"].reason


def test_package_checklist_reflects_rad_decision_requirement() -> None:
    service = DocumentPackageService()
    package = service.build_package(
        matter_id="matter-rad-appeal",
        forum="rad",
        intake_results=[
            _result(
                file_id="f20",
                filename="appeal-record.pdf",
                classification="appeal_record",
            ),
            _result(
                file_id="f21",
                filename="memorandum.pdf",
                classification="memorandum",
            ),
        ],
    )

    checklist_by_item = {entry.item: entry.status for entry in package.disclosure_checklist}
    assert checklist_by_item["decision_under_review"] == "missing"
    assert package.is_ready is False
    metadata_by_item = {entry.item: entry for entry in package.disclosure_checklist}
    assert metadata_by_item["decision_under_review"].rule_scope == "base"
    assert metadata_by_item["decision_under_review"].reason
