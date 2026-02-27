from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Literal


class FilingForum(str, Enum):
    FEDERAL_COURT_JR = "federal_court_jr"
    RPD = "rpd"
    RAD = "rad"
    IAD = "iad"
    ID = "id"
    IRCC_APPLICATION = "ircc_application"


RequirementRuleScope = Literal["base", "conditional"]
RequirementStatusValue = Literal["present", "missing"]


@dataclass(frozen=True)
class RequirementRule:
    item: str
    reason: str
    rule_scope: RequirementRuleScope = "base"


@dataclass(frozen=True)
class RequirementStatus:
    item: str
    status: RequirementStatusValue
    rule_scope: RequirementRuleScope = "base"
    reason: str = ""


@dataclass(frozen=True)
class ReadinessResult:
    is_ready: bool
    missing_required_items: tuple[str, ...]
    blocking_issues: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    requirement_statuses: tuple[RequirementStatus, ...] = ()


_BASE_REQUIREMENT_RULES_BY_FORUM: dict[FilingForum, tuple[RequirementRule, ...]] = {
    FilingForum.FEDERAL_COURT_JR: (
        RequirementRule(
            item="notice_of_application",
            reason="Required to initiate the judicial review application record.",
        ),
        RequirementRule(
            item="decision_under_review",
            reason="Required to identify the administrative decision being challenged.",
        ),
        RequirementRule(
            item="affidavit",
            reason="Required to ground factual evidence in the judicial review record.",
        ),
        RequirementRule(
            item="memorandum",
            reason="Required to set out legal argument and requested relief.",
        ),
    ),
    FilingForum.RPD: (
        RequirementRule(
            item="disclosure_package",
            reason="Required to disclose documentary evidence before the hearing.",
        ),
    ),
    FilingForum.RAD: (
        RequirementRule(
            item="appeal_record",
            reason="Required to compile the material relied on for the appeal.",
        ),
        RequirementRule(
            item="decision_under_review",
            reason="Required to anchor the appeal to the underlying RPD decision.",
        ),
        RequirementRule(
            item="memorandum",
            reason="Required to state RAD appeal grounds and submissions.",
        ),
    ),
    FilingForum.IAD: (
        RequirementRule(
            item="appeal_record",
            reason="Required to frame the evidence and procedural history for appeal review.",
        ),
        RequirementRule(
            item="decision_under_review",
            reason="Required to identify the decision being appealed at the IAD.",
        ),
        RequirementRule(
            item="disclosure_package",
            reason="Required to disclose supporting evidence for the appeal hearing.",
        ),
    ),
    FilingForum.ID: (
        RequirementRule(
            item="disclosure_package",
            reason="Required to disclose documentary evidence before admissibility proceedings.",
        ),
        RequirementRule(
            item="witness_list",
            reason="Required to identify witnesses for admissibility proceedings.",
        ),
    ),
    FilingForum.IRCC_APPLICATION: (
        RequirementRule(
            item="disclosure_package",
            reason="Required to provide the core IRCC application package materials.",
        ),
        RequirementRule(
            item="supporting_evidence",
            reason="Required to support eligibility claims for the IRCC application stream.",
        ),
    ),
}


def _normalize_doc_types(classified_doc_types: set[str] | list[str] | tuple[str, ...]) -> set[str]:
    normalized: set[str] = set()
    for raw_doc_type in classified_doc_types:
        doc_type = str(raw_doc_type).strip().lower()
        if doc_type:
            normalized.add(doc_type)
    return normalized


def _conditional_requirement_rules(
    *,
    forum: FilingForum,
    normalized_doc_types: set[str],
) -> tuple[RequirementRule, ...]:
    del forum
    conditional_rules: list[RequirementRule] = []
    if "translation" in normalized_doc_types:
        conditional_rules.append(
            RequirementRule(
                item="translator_declaration",
                reason="A translator declaration is required when translated material is filed.",
                rule_scope="conditional",
            )
        )
    return tuple(conditional_rules)


def requirement_rules_for_forum(
    *,
    forum: FilingForum,
    classified_doc_types: set[str] | list[str] | tuple[str, ...],
) -> tuple[RequirementRule, ...]:
    normalized_doc_types = _normalize_doc_types(classified_doc_types)
    base_rules = _BASE_REQUIREMENT_RULES_BY_FORUM[forum]
    conditional_rules = _conditional_requirement_rules(
        forum=forum,
        normalized_doc_types=normalized_doc_types,
    )
    merged_rules: list[RequirementRule] = []
    seen_items: set[str] = set()
    for rule in (*base_rules, *conditional_rules):
        if rule.item in seen_items:
            continue
        seen_items.add(rule.item)
        merged_rules.append(rule)
    return tuple(merged_rules)


def required_doc_types_for_forum(
    *,
    forum: FilingForum,
    classified_doc_types: set[str] | list[str] | tuple[str, ...],
) -> tuple[str, ...]:
    rules = requirement_rules_for_forum(
        forum=forum,
        classified_doc_types=classified_doc_types,
    )
    return tuple(rule.item for rule in rules)


def evaluate_readiness(
    *,
    forum: FilingForum,
    classified_doc_types: set[str] | list[str] | tuple[str, ...],
    blocking_issues: set[str] | list[str] | tuple[str, ...] | None = None,
) -> ReadinessResult:
    normalized_doc_types = _normalize_doc_types(classified_doc_types)

    requirement_rules = requirement_rules_for_forum(
        forum=forum,
        classified_doc_types=normalized_doc_types,
    )
    requirement_statuses = tuple(
        RequirementStatus(
            item=rule.item,
            status="present" if rule.item in normalized_doc_types else "missing",
            rule_scope=rule.rule_scope,
            reason=rule.reason,
        )
        for rule in requirement_rules
    )
    missing_required_items = tuple(
        status.item for status in requirement_statuses if status.status == "missing"
    )

    normalized_blocking_issues = _normalize_doc_types(blocking_issues or ())
    blocking_issue_list = tuple(sorted(normalized_blocking_issues))
    is_ready = not missing_required_items and not blocking_issue_list

    return ReadinessResult(
        is_ready=is_ready,
        missing_required_items=missing_required_items,
        blocking_issues=blocking_issue_list,
        requirement_statuses=requirement_statuses,
    )


__all__ = [
    "FilingForum",
    "RequirementRule",
    "RequirementRuleScope",
    "RequirementStatus",
    "ReadinessResult",
    "evaluate_readiness",
    "requirement_rules_for_forum",
    "required_doc_types_for_forum",
]
