from __future__ import annotations

import hashlib
import fitz
import pytest

from immcad_api.schemas import (
    DocumentIntakeResult,
    DocumentQualityStatus,
    DocumentRuleViolation,
)
from immcad_api.services.document_matter_store import StoredSourceFile
from immcad_api.services.document_package_service import DocumentPackageService


def _result(
    *,
    file_id: str,
    filename: str,
    classification: str,
    quality_status: DocumentQualityStatus = "processed",
    issues: list[str] | None = None,
    total_pages: int = 1,
) -> DocumentIntakeResult:
    return DocumentIntakeResult(
        file_id=file_id,
        original_filename=filename,
        normalized_filename=filename,
        classification=classification,
        quality_status=quality_status,
        issues=issues or [],
        total_pages=total_pages,
        page_char_counts=[{"page_number": page_number, "extracted_char_count": 100} for page_number in range(1, total_pages + 1)],
    )


def _pdf_payload(text: str, *, page_count: int = 1) -> bytes:
    document = fitz.open()
    for page_index in range(page_count):
        page = document.new_page()
        page.insert_text((72, 72), f"{text} (page {page_index + 1})")
    payload = document.tobytes()
    document.close()
    return payload


def _png_payload(text: str) -> bytes:
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), text)
    pixmap = page.get_pixmap()
    payload = pixmap.tobytes("png")
    document.close()
    return payload


@pytest.mark.parametrize(
    ("forum", "requested_profile_id", "expected_profile_id"),
    [
        ("federal_court_jr", None, "federal_court_jr_leave"),
        ("federal_court_jr", "", "federal_court_jr_leave"),
        ("federal_court_jr", "   ", "federal_court_jr_leave"),
        ("ircc_application", None, "ircc_pr_card_renewal"),
        ("ircc_application", "", "ircc_pr_card_renewal"),
    ],
)
def test_resolve_compilation_profile_id_returns_forum_default_for_blank_request(
    forum: str,
    requested_profile_id: str | None,
    expected_profile_id: str,
) -> None:
    service = DocumentPackageService()
    resolved_profile_id = service.resolve_compilation_profile_id(
        forum=forum,
        requested_profile_id=requested_profile_id,
    )

    assert resolved_profile_id == expected_profile_id


def test_resolve_compilation_profile_id_returns_normalized_requested_profile_id() -> None:
    service = DocumentPackageService()
    resolved_profile_id = service.resolve_compilation_profile_id(
        forum="federal_court_jr",
        requested_profile_id="  FEDERAL_COURT_JR_LEAVE ",
    )

    assert resolved_profile_id == "federal_court_jr_leave"


def test_resolve_compilation_profile_id_rejects_profile_from_other_forum() -> None:
    service = DocumentPackageService()

    with pytest.raises(ValueError, match="Compilation profile does not match forum"):
        service.resolve_compilation_profile_id(
            forum="rad",
            requested_profile_id="federal_court_jr_leave",
        )


def test_package_builder_uses_selected_profile_requirements_for_readiness() -> None:
    service = DocumentPackageService()
    package = service.build_package(
        matter_id="matter-fc-jr-hearing-readiness",
        forum="federal_court_jr",
        compilation_profile_id="federal_court_jr_hearing",
        intake_results=[
            _result(
                file_id="f901",
                filename="notice.pdf",
                classification="notice_of_application",
            ),
            _result(
                file_id="f902",
                filename="affidavit.pdf",
                classification="affidavit",
            ),
            _result(
                file_id="f903",
                filename="memorandum.pdf",
                classification="memorandum",
            ),
        ],
    )

    assert package.is_ready is True
    assert package.compilation_profile.id == "federal_court_jr_hearing"
    assert "decision_under_review" not in package.cover_letter_draft


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
    assert package.toc_entries[0].document_type == "notice_of_application"
    assert package.toc_entries[0].start_page == 1
    assert package.compilation_output_mode == "metadata_plan_only"


def test_package_builder_returns_metadata_plan_only_when_compiled_pdf_flag_off(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("IMMCAD_ENABLE_COMPILED_PDF", raising=False)
    service = DocumentPackageService()
    package = service.build_package(
        matter_id="matter-compiled-flag-off",
        forum="rpd",
        intake_results=[
            _result(
                file_id="f70",
                filename="disclosure.pdf",
                classification="disclosure_package",
            ),
        ],
        source_files=[
            StoredSourceFile(
                file_id="f70",
                filename="disclosure.pdf",
                payload_bytes=_pdf_payload("Disclosure package source payload."),
            )
        ],
    )

    assert package.compilation_output_mode == "metadata_plan_only"
    assert package.compiled_artifact is None


def test_package_builder_returns_compiled_pdf_when_flag_on_with_source_files(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("IMMCAD_ENABLE_COMPILED_PDF", "1")
    service = DocumentPackageService()
    package = service.build_package(
        matter_id="matter-compiled-flag-on",
        forum="rpd",
        intake_results=[
            _result(
                file_id="f71",
                filename="disclosure.pdf",
                classification="disclosure_package",
            ),
        ],
        source_files=[
            StoredSourceFile(
                file_id="f71",
                filename="disclosure.pdf",
                payload_bytes=_pdf_payload("Disclosure package source payload."),
            )
        ],
    )

    assert package.compilation_output_mode == "compiled_pdf"
    assert package.compiled_artifact is not None
    assert package.compiled_artifact.filename == "matter-compiled-flag-on-compiled-binder.pdf"
    assert package.compiled_artifact.page_count == 1
    assert package.compiled_artifact.byte_size > 0
    assert len(package.compiled_artifact.sha256) == 64


def test_build_compiled_binder_returns_bytes_with_metadata_consistency(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("IMMCAD_ENABLE_COMPILED_PDF", "1")
    service = DocumentPackageService()
    compiled = service.build_compiled_binder(
        matter_id="matter-compiled-download",
        forum="rpd",
        intake_results=[
            _result(
                file_id="f72",
                filename="disclosure.pdf",
                classification="disclosure_package",
            ),
        ],
        source_files=[
            StoredSourceFile(
                file_id="f72",
                filename="disclosure.pdf",
                payload_bytes=_pdf_payload("Disclosure package source payload."),
            )
        ],
    )

    assert compiled is not None
    package, payload_bytes = compiled
    assert package.is_ready is True
    assert package.compilation_output_mode == "compiled_pdf"
    assert package.compiled_artifact is not None
    assert payload_bytes.startswith(b"%PDF")
    assert len(payload_bytes) == package.compiled_artifact.byte_size
    assert hashlib.sha256(payload_bytes).hexdigest() == package.compiled_artifact.sha256


def test_build_compiled_binder_includes_bookmarks_and_page_stamps(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("IMMCAD_ENABLE_COMPILED_PDF", "1")
    service = DocumentPackageService()
    compiled = service.build_compiled_binder(
        matter_id="matter-compiled-ux-markers",
        forum="rpd",
        intake_results=[
            _result(
                file_id="f80",
                filename="disclosure.pdf",
                classification="disclosure_package",
            ),
            _result(
                file_id="f81",
                filename="supporting-evidence.pdf",
                classification="supporting_evidence",
            ),
        ],
        source_files=[
            StoredSourceFile(
                file_id="f80",
                filename="disclosure.pdf",
                payload_bytes=_pdf_payload("Disclosure package source payload."),
            ),
            StoredSourceFile(
                file_id="f81",
                filename="supporting-evidence.pdf",
                payload_bytes=_pdf_payload("Supporting evidence source payload."),
            ),
        ],
    )

    assert compiled is not None
    package, payload_bytes = compiled
    assert package.compiled_artifact is not None

    compiled_pdf = fitz.open(stream=payload_bytes, filetype="pdf")
    try:
        assert compiled_pdf.page_count == 2
        assert compiled_pdf.get_toc(simple=True) == [
            [1, "1. disclosure.pdf (disclosure package)", 1],
            [1, "2. supporting-evidence.pdf (supporting evidence)", 2],
        ]
        assert "IMMCAD page 1 of 2" in compiled_pdf[0].get_text("text")
        assert "IMMCAD page 2 of 2" in compiled_pdf[1].get_text("text")
    finally:
        compiled_pdf.close()


def test_package_builder_returns_metadata_plan_only_when_compiled_payload_integrity_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("IMMCAD_ENABLE_COMPILED_PDF", "1")
    service = DocumentPackageService()
    package = service.build_package(
        matter_id="matter-compiled-integrity-fallback",
        forum="rpd",
        intake_results=[
            _result(
                file_id="f82",
                filename="disclosure.pdf",
                classification="disclosure_package",
                total_pages=2,
            ),
        ],
        source_files=[
            StoredSourceFile(
                file_id="f82",
                filename="disclosure.pdf",
                payload_bytes=_pdf_payload("Disclosure package source payload.", page_count=1),
            )
        ],
    )

    assert package.compilation_output_mode == "metadata_plan_only"
    assert package.compiled_artifact is None
    assert (
        service.build_compiled_binder(
            matter_id="matter-compiled-integrity-fallback",
            forum="rpd",
            intake_results=[
                _result(
                    file_id="f82",
                    filename="disclosure.pdf",
                    classification="disclosure_package",
                    total_pages=2,
                ),
            ],
            source_files=[
                StoredSourceFile(
                    file_id="f82",
                    filename="disclosure.pdf",
                    payload_bytes=_pdf_payload("Disclosure package source payload.", page_count=1),
                )
            ],
        )
        is None
    )


def test_package_builder_returns_compiled_pdf_for_mixed_pdf_and_image_sources(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("IMMCAD_ENABLE_COMPILED_PDF", "1")
    service = DocumentPackageService()
    package = service.build_package(
        matter_id="matter-compiled-mixed-sources",
        forum="rpd",
        intake_results=[
            _result(
                file_id="f83",
                filename="disclosure.pdf",
                classification="disclosure_package",
            ),
            _result(
                file_id="f84",
                filename="supporting-evidence.png",
                classification="supporting_evidence",
            ),
        ],
        source_files=[
            StoredSourceFile(
                file_id="f83",
                filename="disclosure.pdf",
                payload_bytes=_pdf_payload("Disclosure package source payload."),
            ),
            StoredSourceFile(
                file_id="f84",
                filename="supporting-evidence.png",
                payload_bytes=_png_payload("Supporting evidence image payload."),
            ),
        ],
    )

    assert package.compilation_output_mode == "compiled_pdf"
    assert package.compiled_artifact is not None
    assert package.compiled_artifact.page_count == 2


def test_package_builder_returns_metadata_only_when_source_payload_is_malformed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("IMMCAD_ENABLE_COMPILED_PDF", "1")
    service = DocumentPackageService()
    package = service.build_package(
        matter_id="matter-compiled-malformed-source",
        forum="rpd",
        intake_results=[
            _result(
                file_id="f85",
                filename="disclosure.pdf",
                classification="disclosure_package",
            ),
        ],
        source_files=[
            StoredSourceFile(
                file_id="f85",
                filename="disclosure.pdf",
                payload_bytes=b"not-a-valid-pdf-payload",
            ),
        ],
    )

    assert package.compilation_output_mode == "metadata_plan_only"
    assert package.compiled_artifact is None


def test_build_compiled_binder_handles_multipage_ocr_heavy_style_payloads(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("IMMCAD_ENABLE_COMPILED_PDF", "1")
    service = DocumentPackageService()
    compiled = service.build_compiled_binder(
        matter_id="matter-compiled-multipage",
        forum="rpd",
        intake_results=[
            _result(
                file_id="f86",
                filename="disclosure.pdf",
                classification="disclosure_package",
                total_pages=6,
            ),
        ],
        source_files=[
            StoredSourceFile(
                file_id="f86",
                filename="disclosure.pdf",
                payload_bytes=_pdf_payload(
                    "OCR heavy style disclosure payload.",
                    page_count=6,
                ),
            ),
        ],
    )

    assert compiled is not None
    package, payload_bytes = compiled
    assert package.compiled_artifact is not None
    assert package.compiled_artifact.page_count == 6
    compiled_pdf = fitz.open(stream=payload_bytes, filetype="pdf")
    try:
        assert "IMMCAD page 6 of 6" in compiled_pdf[5].get_text("text")
    finally:
        compiled_pdf.close()


def test_build_compiled_binder_returns_none_when_compiled_mode_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("IMMCAD_ENABLE_COMPILED_PDF", raising=False)
    service = DocumentPackageService()
    compiled = service.build_compiled_binder(
        matter_id="matter-compiled-download-disabled",
        forum="rpd",
        intake_results=[
            _result(
                file_id="f73",
                filename="disclosure.pdf",
                classification="disclosure_package",
            ),
        ],
        source_files=[
            StoredSourceFile(
                file_id="f73",
                filename="disclosure.pdf",
                payload_bytes=_pdf_payload("Disclosure package source payload."),
            )
        ],
    )

    assert compiled is None


def test_package_builder_includes_normalized_record_sections_for_fc_jr_leave() -> None:
    service = DocumentPackageService()
    package = service.build_package(
        matter_id="matter-record-sections-fc-jr-leave",
        forum="federal_court_jr",
        compilation_profile_id="federal_court_jr_leave",
        intake_results=[
            _result(
                file_id="f50",
                filename="notice.pdf",
                classification="notice_of_application",
            ),
            _result(
                file_id="f51",
                filename="decision.pdf",
                classification="decision_under_review",
            ),
            _result(
                file_id="f52",
                filename="affidavit.pdf",
                classification="affidavit",
            ),
            _result(
                file_id="f53",
                filename="memorandum.pdf",
                classification="memorandum",
            ),
        ],
    )

    sections_by_id = {section.section_id: section for section in package.record_sections}
    assert sections_by_id["fc_jr_leave_core_documents"].title == "Leave Materials"
    assert list(sections_by_id["fc_jr_leave_core_documents"].document_types) == [
        "notice_of_application",
        "decision_under_review",
        "affidavit",
        "memorandum",
    ]


def test_package_builder_includes_normalized_record_sections_for_rad() -> None:
    service = DocumentPackageService()
    package = service.build_package(
        matter_id="matter-record-sections-rad",
        forum="rad",
        compilation_profile_id="rad",
        intake_results=[
            _result(
                file_id="f60",
                filename="appeal-record.pdf",
                classification="appeal_record",
            ),
            _result(
                file_id="f61",
                filename="decision.pdf",
                classification="decision_under_review",
            ),
            _result(
                file_id="f62",
                filename="memorandum.pdf",
                classification="memorandum",
            ),
        ],
    )

    sections_by_id = {section.section_id: section for section in package.record_sections}
    assert sections_by_id["rad_core_appeal_record"].title == "RAD Appeal Materials"
    assert list(sections_by_id["rad_core_appeal_record"].document_types) == [
        "appeal_record",
        "decision_under_review",
        "memorandum",
    ]


def test_package_builder_includes_section_status_and_missing_rationale_for_conditional_rules() -> None:
    service = DocumentPackageService()
    package = service.build_package(
        matter_id="matter-record-sections-rpd-conditional",
        forum="rpd",
        compilation_profile_id="rpd",
        intake_results=[
            _result(
                file_id="f63",
                filename="disclosure.pdf",
                classification="disclosure_package",
            ),
            _result(
                file_id="f64",
                filename="translation.pdf",
                classification="translation",
            ),
        ],
    )

    sections_by_id = {section.section_id: section for section in package.record_sections}
    supporting_section = sections_by_id["rpd_supporting_materials"]

    assert supporting_section.section_status == "missing"
    assert supporting_section.missing_document_types == ["translator_declaration"]
    assert supporting_section.missing_reasons
    translator_slots = [
        slot
        for slot in supporting_section.slot_statuses
        if slot.document_type == "translator_declaration"
    ]
    assert len(translator_slots) == 1
    assert translator_slots[0].rule_scope == "conditional"
    assert translator_slots[0].status == "missing"
    assert translator_slots[0].reason


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
    assert package.rule_violations
    assert all(violation.rule_source_url for violation in package.rule_violations)
    assert package.compilation_profile.id
    assert package.compilation_profile.version


def test_package_builder_calculates_page_ranges_and_pagination_summary() -> None:
    service = DocumentPackageService()
    package = service.build_package(
        matter_id="matter-page-map",
        forum="federal_court_jr",
        intake_results=[
            _result(
                file_id="f30",
                filename="notice.pdf",
                classification="notice_of_application",
                total_pages=2,
            ),
            _result(
                file_id="f31",
                filename="decision.pdf",
                classification="decision_under_review",
                total_pages=3,
            ),
        ],
    )

    assert package.toc_entries[0].start_page == 1
    assert package.toc_entries[0].end_page == 2
    assert package.toc_entries[1].start_page == 3
    assert package.toc_entries[1].end_page == 5
    assert package.pagination_summary.total_documents == 2
    assert package.pagination_summary.total_pages == 5
    assert package.pagination_summary.last_assigned_page == 5


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


def test_package_builder_blocks_deterministically_on_blocking_rule_violations(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = DocumentPackageService()

    def _stub_rule_violations(
        *,
        forum: str,
        intake_results: list[DocumentIntakeResult],
        assembly_violations,
    ):
        del forum, intake_results, assembly_violations
        return [
            DocumentRuleViolation(
                violation_code="z_warning",
                severity="warning",
                rule_source_url="https://example.test/rules/warn",
            ),
            DocumentRuleViolation(
                violation_code="a_block",
                severity="blocking",
                rule_source_url="https://example.test/rules/block",
            ),
        ]

    monkeypatch.setattr(
        DocumentPackageService,
        "_evaluate_rule_violations",
        staticmethod(_stub_rule_violations),
    )

    package = service.build_package(
        matter_id="matter-deterministic-block",
        forum="federal_court_jr",
        intake_results=[
            _result(
                file_id="f40",
                filename="notice.pdf",
                classification="notice_of_application",
            ),
            _result(
                file_id="f41",
                filename="decision.pdf",
                classification="decision_under_review",
            ),
            _result(
                file_id="f42",
                filename="affidavit.pdf",
                classification="affidavit",
            ),
            _result(
                file_id="f43",
                filename="memorandum.pdf",
                classification="memorandum",
            ),
        ],
    )

    assert package.is_ready is False
    assert [violation.violation_code for violation in package.rule_violations] == [
        "a_block",
        "z_warning",
    ]
