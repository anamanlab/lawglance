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
    assert any("translator declaration" in item.lower() for item in readiness.missing_required_items)


def test_id_forum_is_ready_when_required_documents_present() -> None:
    readiness = evaluate_readiness(
        forum=FilingForum.ID,
        classified_doc_types={"disclosure_package", "witness_list"},
    )

    assert readiness.is_ready is True
    assert readiness.missing_required_items == ()
