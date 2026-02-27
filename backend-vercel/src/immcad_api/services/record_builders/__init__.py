from __future__ import annotations

from dataclasses import dataclass

from immcad_api.policy.document_types import require_canonical_document_type


@dataclass(frozen=True)
class RecordSection:
    section_id: str
    title: str
    instructions: str
    document_types: tuple[str, ...]


from immcad_api.services.record_builders.federal_court_jr import (  # noqa: E402
    build_federal_court_jr_record_sections,
)
from immcad_api.services.record_builders.iad import build_iad_record_sections  # noqa: E402
from immcad_api.services.record_builders.id import build_id_record_sections  # noqa: E402
from immcad_api.services.record_builders.ircc_application import (  # noqa: E402
    build_ircc_pr_card_renewal_record_sections,
)
from immcad_api.services.record_builders.rad import build_rad_record_sections  # noqa: E402
from immcad_api.services.record_builders.rpd import build_rpd_record_sections  # noqa: E402


def build_record_sections(profile_id: str) -> tuple[RecordSection, ...]:
    normalized_profile_id = str(profile_id).strip().lower()

    if normalized_profile_id in {"federal_court_jr_leave", "federal_court_jr_hearing"}:
        sections = build_federal_court_jr_record_sections(normalized_profile_id)
        return _validate_section_document_types(
            profile_id=normalized_profile_id,
            sections=sections,
        )

    profile_builders = {
        "rpd": build_rpd_record_sections,
        "rad": build_rad_record_sections,
        "id": build_id_record_sections,
        "iad": build_iad_record_sections,
        "iad_sponsorship": build_iad_record_sections,
        "iad_residency": build_iad_record_sections,
        "iad_admissibility": build_iad_record_sections,
        "ircc_pr_card_renewal": build_ircc_pr_card_renewal_record_sections,
    }
    builder = profile_builders.get(normalized_profile_id)
    if builder is None:
        raise KeyError(f"Unsupported record builder profile: {profile_id}")

    sections = builder()
    return _validate_section_document_types(
        profile_id=normalized_profile_id,
        sections=sections,
    )


def _validate_section_document_types(
    *,
    profile_id: str,
    sections: tuple[RecordSection, ...],
) -> tuple[RecordSection, ...]:
    for section in sections:
        for document_type in section.document_types:
            require_canonical_document_type(
                document_type,
                context=f"record section '{section.section_id}' in profile_id='{profile_id}'",
            )
    return sections


__all__ = ["RecordSection", "build_record_sections"]
