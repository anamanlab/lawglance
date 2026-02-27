from __future__ import annotations

from immcad_api.services.record_builders import RecordSection


def _leave_sections() -> tuple[RecordSection, ...]:
    return (
        RecordSection(
            section_id="fc_jr_leave_index",
            title="Index",
            instructions="Provide a package index listing each document and page span.",
            document_types=("index",),
        ),
        RecordSection(
            section_id="fc_jr_leave_core_documents",
            title="Leave Materials",
            instructions=(
                "Include the notice of application, decision under review, affidavit evidence, "
                "and memorandum of argument in filing order."
            ),
            document_types=(
                "notice_of_application",
                "decision_under_review",
                "affidavit",
                "memorandum",
            ),
        ),
        RecordSection(
            section_id="fc_jr_leave_translation_materials",
            title="Translation Materials",
            instructions=(
                "When translated documents are filed, place the translation and translator declaration "
                "after the core leave materials."
            ),
            document_types=("translation", "translator_declaration"),
        ),
    )


def _hearing_sections() -> tuple[RecordSection, ...]:
    return (
        RecordSection(
            section_id="fc_jr_hearing_index",
            title="Index",
            instructions="Provide a package index listing each hearing document and page span.",
            document_types=("index",),
        ),
        RecordSection(
            section_id="fc_jr_hearing_core_documents",
            title="Hearing Record Materials",
            instructions=(
                "Include the notice of application, affidavit evidence, and memorandum of argument "
                "in filing order."
            ),
            document_types=(
                "notice_of_application",
                "affidavit",
                "memorandum",
            ),
        ),
        RecordSection(
            section_id="fc_jr_hearing_translation_materials",
            title="Translation Materials",
            instructions=(
                "When translated documents are filed, place the translation and translator declaration "
                "after the hearing materials."
            ),
            document_types=("translation", "translator_declaration"),
        ),
    )


def build_federal_court_jr_record_sections(profile_id: str) -> tuple[RecordSection, ...]:
    normalized_profile_id = str(profile_id).strip().lower()
    if normalized_profile_id == "federal_court_jr_leave":
        return _leave_sections()
    if normalized_profile_id == "federal_court_jr_hearing":
        return _hearing_sections()
    raise KeyError(f"Unsupported Federal Court JR profile: {profile_id}")


__all__ = ["build_federal_court_jr_record_sections"]
