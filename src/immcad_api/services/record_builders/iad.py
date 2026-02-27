from __future__ import annotations

from immcad_api.services.record_builders import RecordSection


def build_iad_record_sections() -> tuple[RecordSection, ...]:
    return (
        RecordSection(
            section_id="iad_index",
            title="Index",
            instructions="Provide a package index listing each IAD filing document and page span.",
            document_types=("index",),
        ),
        RecordSection(
            section_id="iad_core_appeal_record",
            title="IAD Appeal Materials",
            instructions=(
                "Assemble the appeal record, decision under review, and disclosure package "
                "for IAD filing."
            ),
            document_types=("appeal_record", "decision_under_review", "disclosure_package"),
        ),
        RecordSection(
            section_id="iad_translation_materials",
            title="Translation Materials",
            instructions=(
                "When translated evidence is included, append translation and translator declaration "
                "after IAD appeal materials."
            ),
            document_types=("translation", "translator_declaration"),
        ),
    )


__all__ = ["build_iad_record_sections"]
