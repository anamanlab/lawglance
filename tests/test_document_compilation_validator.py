from __future__ import annotations

from dataclasses import replace

from immcad_api.policy.document_compilation_rules import load_document_compilation_rules
from immcad_api.policy.document_compilation_validator import validate_document_compilation


def test_validator_emits_blocking_violation_for_missing_required_document() -> None:
    catalog = load_document_compilation_rules()
    profile = catalog.require_profile("rpd")

    violations = validate_document_compilation(
        profile=profile,
        provided_document_types={"translation"},
        page_ranges=((1, 2),),
    )

    missing_required = [item for item in violations if item.violation_code == "missing_required_document"]
    assert missing_required
    first = missing_required[0]
    assert first.severity == "blocking"
    assert first.rule_id
    assert first.rule_source_url.startswith("https://")
    assert first.remediation


def test_validator_emits_translation_conditional_violation() -> None:
    catalog = load_document_compilation_rules()
    profile = catalog.require_profile("federal_court_jr_leave")

    violations = validate_document_compilation(
        profile=profile,
        provided_document_types={
            "notice_of_application",
            "decision_under_review",
            "affidavit",
            "memorandum",
            "translation",
        },
        page_ranges=((1, 3), (4, 7), (8, 11), (12, 20), (21, 23)),
    )

    translation_violations = [
        item for item in violations if item.violation_code == "missing_conditional_document"
    ]
    assert len(translation_violations) == 1
    assert translation_violations[0].rule_id.endswith("translation_requires_translator_declaration")


def test_validator_emits_index_violation_when_index_missing() -> None:
    catalog = load_document_compilation_rules()
    base_profile = catalog.require_profile("federal_court_jr_hearing")
    profile = replace(
        base_profile,
        pagination_requirements=replace(
            base_profile.pagination_requirements,
            require_index_document=True,
            index_document_type="index",
        ),
    )

    violations = validate_document_compilation(
        profile=profile,
        provided_document_types={
            "notice_of_application",
            "affidavit",
            "memorandum",
        },
        page_ranges=((1, 20), (21, 35), (36, 60)),
    )

    assert any(item.violation_code == "missing_index_document" for item in violations)


def test_validator_emits_pagination_violation_for_non_monotonic_ranges() -> None:
    catalog = load_document_compilation_rules()
    profile = catalog.require_profile("rad")

    violations = validate_document_compilation(
        profile=profile,
        provided_document_types={
            "appeal_record",
            "decision_under_review",
            "memorandum",
        },
        page_ranges=((1, 5), (7, 12), (13, 22), (23, 27)),
    )

    assert any(item.violation_code == "non_monotonic_pagination" for item in violations)
