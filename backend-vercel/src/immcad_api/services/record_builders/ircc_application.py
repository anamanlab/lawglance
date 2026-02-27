from __future__ import annotations

from immcad_api.services.record_builders import RecordSection


def build_ircc_pr_card_renewal_record_sections() -> tuple[RecordSection, ...]:
    return (
        RecordSection(
            section_id="ircc_pr_card_renewal_index",
            title="Application Index",
            instructions=(
                "Provide an index listing each included IRCC PR card renewal document "
                "and supporting page span."
            ),
            document_types=("index",),
        ),
        RecordSection(
            section_id="ircc_pr_card_renewal_core_application",
            title="Core Application Materials",
            instructions=(
                "Include the completed PR card renewal package materials and required "
                "supporting evidence in filing order."
            ),
            document_types=("disclosure_package", "supporting_evidence"),
        ),
        RecordSection(
            section_id="ircc_pr_card_renewal_translation_materials",
            title="Translation Materials",
            instructions=(
                "When non-English/French evidence is provided, include translations "
                "with the translator declaration."
            ),
            document_types=("translation", "translator_declaration"),
        ),
    )


__all__ = ["build_ircc_pr_card_renewal_record_sections"]
