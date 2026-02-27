from __future__ import annotations

from immcad_api.services.record_builders import RecordSection


def build_id_record_sections() -> tuple[RecordSection, ...]:
    return (
        RecordSection(
            section_id="id_index",
            title="Index",
            instructions="Provide a package index listing each ID filing document and page span.",
            document_types=("index",),
        ),
        RecordSection(
            section_id="id_core_record",
            title="ID Core Record",
            instructions=(
                "Assemble disclosure package documents and witness list materials for ID proceedings."
            ),
            document_types=("disclosure_package", "witness_list"),
        ),
        RecordSection(
            section_id="id_translation_materials",
            title="Translation Materials",
            instructions=(
                "When translated evidence is included, append translation and translator declaration "
                "after the core ID record."
            ),
            document_types=("translation", "translator_declaration"),
        ),
    )


__all__ = ["build_id_record_sections"]
