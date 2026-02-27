from __future__ import annotations

from immcad_api.policy.document_requirements import FilingForum, evaluate_readiness


def test_fc_rule_309_requires_decision_affidavit_memorandum() -> None:
    readiness = evaluate_readiness(
        forum=FilingForum.FEDERAL_COURT_JR,
        classified_doc_types={"notice_of_application", "decision_under_review"},
    )

    assert readiness.is_ready is False
    assert "affidavit" in " ".join(readiness.missing_required_items).lower()
    assert "memorandum" in " ".join(readiness.missing_required_items).lower()


def test_rpd_requires_translation_declaration_when_translation_present() -> None:
    readiness = evaluate_readiness(
        forum=FilingForum.RPD,
        classified_doc_types={"identity_document", "translation"},
    )

    assert readiness.is_ready is False
    assert "translator_declaration" in readiness.missing_required_items


def test_id_forum_is_ready_when_required_documents_present() -> None:
    readiness = evaluate_readiness(
        forum=FilingForum.ID,
        classified_doc_types={"disclosure_package", "witness_list"},
    )

    assert readiness.is_ready is True
    assert readiness.missing_required_items == ()


def test_rad_requires_decision_under_review_for_appeal_package() -> None:
    readiness = evaluate_readiness(
        forum=FilingForum.RAD,
        classified_doc_types={"appeal_record", "memorandum"},
    )

    assert readiness.is_ready is False
    assert "decision_under_review" in readiness.missing_required_items


def test_translation_requires_translator_declaration_for_fc_jr() -> None:
    readiness = evaluate_readiness(
        forum=FilingForum.FEDERAL_COURT_JR,
        classified_doc_types={
            "notice_of_application",
            "decision_under_review",
            "affidavit",
            "memorandum",
            "translation",
        },
    )

    assert readiness.is_ready is False
    assert "translator_declaration" in readiness.missing_required_items


def test_readiness_exposes_requirement_metadata_with_rule_scope_and_reason() -> None:
    readiness = evaluate_readiness(
        forum=FilingForum.RAD,
        classified_doc_types={"appeal_record"},
    )

    status_by_item = {item.item: item for item in readiness.requirement_statuses}
    assert status_by_item["appeal_record"].status == "present"
    assert status_by_item["appeal_record"].rule_scope == "base"
    assert status_by_item["appeal_record"].reason
    assert status_by_item["decision_under_review"].status == "missing"
    assert status_by_item["decision_under_review"].rule_scope == "base"


def test_translation_rule_metadata_is_marked_conditional() -> None:
    readiness = evaluate_readiness(
        forum=FilingForum.RPD,
        classified_doc_types={"disclosure_package", "translation"},
    )

    status_by_item = {item.item: item for item in readiness.requirement_statuses}
    assert status_by_item["translator_declaration"].status == "missing"
    assert status_by_item["translator_declaration"].rule_scope == "conditional"
    assert status_by_item["translator_declaration"].reason
