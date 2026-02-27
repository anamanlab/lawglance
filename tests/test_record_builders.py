from __future__ import annotations

import pytest

from immcad_api.policy.document_compilation_rules import load_document_compilation_rules
from immcad_api.policy.document_types import is_canonical_document_type
from immcad_api.services.record_builders import RecordSection, build_record_sections


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
def test_record_builder_returns_sections_for_each_supported_profile(profile_id: str) -> None:
    sections = build_record_sections(profile_id)

    assert sections
    assert all(isinstance(section, RecordSection) for section in sections)
    assert all(section.section_id for section in sections)
    assert all(section.title for section in sections)
    assert all(section.document_types for section in sections)


def test_federal_court_leave_and_hearing_sections_are_distinct() -> None:
    leave_sections = build_record_sections("federal_court_jr_leave")
    hearing_sections = build_record_sections("federal_court_jr_hearing")

    assert leave_sections != hearing_sections


@pytest.mark.parametrize(
    ("profile_id", "expected_titles"),
    [
        (
            "federal_court_jr_leave",
            ["Index", "Leave Materials", "Translation Materials"],
        ),
        (
            "federal_court_jr_hearing",
            ["Index", "Hearing Record Materials", "Translation Materials"],
        ),
        (
            "rad",
            ["Index", "RAD Appeal Materials", "Translation Materials"],
        ),
    ],
)
def test_record_builder_uses_expected_section_titles_for_key_profiles(
    profile_id: str,
    expected_titles: list[str],
) -> None:
    sections = build_record_sections(profile_id)

    assert [section.title for section in sections] == expected_titles


def test_record_builder_content_is_procedural_only() -> None:
    sections = build_record_sections("rpd")
    combined = " ".join(section.instructions.lower() for section in sections)

    assert "legal advice" not in combined
    assert "recommend legal strategy" not in combined


def test_record_builder_uses_canonical_document_types() -> None:
    sections = build_record_sections("iad")

    all_document_types = [
        document_type
        for section in sections
        for document_type in section.document_types
    ]
    assert all_document_types
    assert all(is_canonical_document_type(document_type) for document_type in all_document_types)


def test_record_builder_maps_rule_documents_to_single_section_slots() -> None:
    catalog = load_document_compilation_rules()

    for profile in catalog.profiles:
        sections = build_record_sections(profile.profile_id)
        for document_type in [*(
            rule.document_type for rule in profile.required_documents
        ), *(
            rule.requires_document_type for rule in profile.conditional_rules
        )]:
            matching_sections = [
                section.section_id for section in sections if document_type in section.document_types
            ]
            assert len(matching_sections) == 1


def test_record_builder_rejects_unknown_profile() -> None:
    with pytest.raises(KeyError):
        build_record_sections("unknown-profile")
