from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class FilingForum(str, Enum):
    FEDERAL_COURT_JR = "federal_court_jr"
    RPD = "rpd"
    RAD = "rad"
    IAD = "iad"
    ID = "id"


@dataclass(frozen=True)
class ReadinessResult:
    is_ready: bool
    missing_required_items: tuple[str, ...]
    blocking_issues: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()


_REQUIRED_DOC_TYPES_BY_FORUM: dict[FilingForum, tuple[str, ...]] = {
    FilingForum.FEDERAL_COURT_JR: (
        "notice_of_application",
        "decision_under_review",
        "affidavit",
        "memorandum",
    ),
    FilingForum.RPD: (
        "disclosure_package",
    ),
    FilingForum.RAD: (
        "appeal_record",
        "memorandum",
    ),
    FilingForum.IAD: (
        "appeal_record",
        "disclosure_package",
    ),
    FilingForum.ID: (
        "disclosure_package",
        "witness_list",
    ),
}


def _normalize_doc_types(classified_doc_types: set[str] | list[str] | tuple[str, ...]) -> set[str]:
    normalized: set[str] = set()
    for raw_doc_type in classified_doc_types:
        doc_type = str(raw_doc_type).strip().lower()
        if doc_type:
            normalized.add(doc_type)
    return normalized


def evaluate_readiness(
    *,
    forum: FilingForum,
    classified_doc_types: set[str] | list[str] | tuple[str, ...],
    blocking_issues: set[str] | list[str] | tuple[str, ...] | None = None,
) -> ReadinessResult:
    normalized_doc_types = _normalize_doc_types(classified_doc_types)

    required_doc_types = _REQUIRED_DOC_TYPES_BY_FORUM[forum]
    missing_required_items = tuple(
        required for required in required_doc_types if required not in normalized_doc_types
    )

    # RPD translations require a translator declaration in package completeness checks.
    if forum == FilingForum.RPD and "translation" in normalized_doc_types:
        if "translator_declaration" not in normalized_doc_types:
            missing_required_items = (*missing_required_items, "translator declaration")

    normalized_blocking_issues = _normalize_doc_types(blocking_issues or ())
    blocking_issue_list = tuple(sorted(normalized_blocking_issues))
    is_ready = not missing_required_items and not blocking_issue_list

    return ReadinessResult(
        is_ready=is_ready,
        missing_required_items=missing_required_items,
        blocking_issues=blocking_issue_list,
    )


__all__ = [
    "FilingForum",
    "ReadinessResult",
    "evaluate_readiness",
]
