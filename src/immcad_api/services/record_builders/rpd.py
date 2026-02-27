from __future__ import annotations

from immcad_api.services.record_builders import RecordSection


def build_rpd_record_sections() -> tuple[RecordSection, ...]:
    return (
        RecordSection(
            section_id="rpd_index",
            title="Index",
            instructions="Provide a package index listing each RPD filing document and page span.",
            document_types=("index",),
        ),
        RecordSection(
            section_id="rpd_core_record",
            title="Core RPD Record",
            instructions=(
                "Assemble the basis of claim form and disclosure package in the sequence required "
                "for RPD filing."
            ),
            document_types=("disclosure_package",),
        ),
        RecordSection(
            section_id="rpd_supporting_materials",
            title="Supporting Materials",
            instructions=(
                "Append witness list material and any translation package items after core RPD records."
            ),
            document_types=("witness_list", "translation", "translator_declaration"),
        ),
    )


__all__ = ["build_rpd_record_sections"]
