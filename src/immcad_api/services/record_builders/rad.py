from __future__ import annotations

from immcad_api.services.record_builders import RecordSection


def build_rad_record_sections() -> tuple[RecordSection, ...]:
    return (
        RecordSection(
            section_id="rad_index",
            title="Index",
            instructions="Provide a package index listing each RAD filing document and page span.",
            document_types=("index",),
        ),
        RecordSection(
            section_id="rad_core_appeal_record",
            title="RAD Appeal Materials",
            instructions=(
                "Assemble the appeal record, decision under review, and memorandum of argument "
                "in filing order."
            ),
            document_types=(
                "appeal_record",
                "decision_under_review",
                "memorandum",
            ),
        ),
        RecordSection(
            section_id="rad_translation_materials",
            title="Translation Materials",
            instructions=(
                "When translated evidence is included, append translation and translator declaration "
                "after appeal materials."
            ),
            document_types=("translation", "translator_declaration"),
        ),
    )


__all__ = ["build_rad_record_sections"]
