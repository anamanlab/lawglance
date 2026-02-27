from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from immcad_api.policy.document_compilation_rules import DocumentCompilationProfile


ViolationSeverity = Literal["warning", "blocking"]


@dataclass(frozen=True)
class DocumentCompilationViolation:
    violation_code: str
    severity: ViolationSeverity
    rule_id: str
    rule_source_url: str
    remediation: str


def _normalize_document_types(
    provided_document_types: set[str] | list[str] | tuple[str, ...],
) -> set[str]:
    normalized: set[str] = set()
    for item in provided_document_types:
        document_type = str(item).strip().lower()
        if document_type:
            normalized.add(document_type)
    return normalized


def _normalize_page_ranges(
    page_ranges: tuple[tuple[int, int], ...] | list[tuple[int, int]] | None,
) -> tuple[tuple[int, int], ...]:
    if page_ranges is None:
        return ()
    normalized: list[tuple[int, int]] = []
    for start_page, end_page in page_ranges:
        normalized.append((int(start_page), int(end_page)))
    return tuple(normalized)


def _is_monotonic_page_ranges(page_ranges: tuple[tuple[int, int], ...]) -> bool:
    if not page_ranges:
        return True

    expected_start = 1
    for start_page, end_page in page_ranges:
        if start_page != expected_start:
            return False
        if end_page < start_page:
            return False
        expected_start = end_page + 1
    return True


def validate_document_compilation(
    *,
    profile: DocumentCompilationProfile,
    provided_document_types: set[str] | list[str] | tuple[str, ...],
    page_ranges: tuple[tuple[int, int], ...] | list[tuple[int, int]] | None = None,
) -> tuple[DocumentCompilationViolation, ...]:
    normalized_document_types = _normalize_document_types(provided_document_types)
    normalized_page_ranges = _normalize_page_ranges(page_ranges)

    violations: list[DocumentCompilationViolation] = []

    for rule in profile.required_documents:
        if rule.document_type in normalized_document_types:
            continue
        violations.append(
            DocumentCompilationViolation(
                violation_code="missing_required_document",
                severity=rule.severity,
                rule_id=rule.rule_id,
                rule_source_url=rule.source_url,
                remediation=rule.remediation,
            )
        )

    for rule in profile.conditional_rules:
        if rule.when_document_type not in normalized_document_types:
            continue
        if rule.requires_document_type in normalized_document_types:
            continue
        violations.append(
            DocumentCompilationViolation(
                violation_code="missing_conditional_document",
                severity=rule.severity,
                rule_id=rule.rule_id,
                rule_source_url=rule.source_url,
                remediation=rule.remediation,
            )
        )

    pagination_rules = profile.pagination_requirements
    if (
        pagination_rules.require_index_document
        and pagination_rules.index_document_type not in normalized_document_types
    ):
        violations.append(
            DocumentCompilationViolation(
                violation_code="missing_index_document",
                severity="blocking",
                rule_id=pagination_rules.rule_id,
                rule_source_url=pagination_rules.source_url,
                remediation=pagination_rules.remediation,
            )
        )

    if (
        pagination_rules.require_continuous_package_pagination
        and normalized_page_ranges
        and not _is_monotonic_page_ranges(normalized_page_ranges)
    ):
        violations.append(
            DocumentCompilationViolation(
                violation_code="non_monotonic_pagination",
                severity="blocking",
                rule_id=pagination_rules.rule_id,
                rule_source_url=pagination_rules.source_url,
                remediation=pagination_rules.remediation,
            )
        )

    return tuple(violations)


__all__ = [
    "DocumentCompilationViolation",
    "ViolationSeverity",
    "validate_document_compilation",
]
