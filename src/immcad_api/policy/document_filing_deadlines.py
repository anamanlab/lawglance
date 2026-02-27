from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Literal, cast, get_args


DocumentSubmissionChannel = Literal["portal", "email", "fax", "mail", "in_person"]


@dataclass(frozen=True)
class SubmissionChannelLimits:
    channel: DocumentSubmissionChannel
    max_files: int
    max_bytes_per_file: int
    near_file_limit_ratio: float = 0.8


@dataclass(frozen=True)
class FilingDeadlineContext:
    submission_channel: DocumentSubmissionChannel = "portal"
    decision_date: date | None = None
    hearing_date: date | None = None
    service_date: date | None = None
    filing_date: date | None = None
    deadline_override_reason: str | None = None
    preflight_warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class FilingDeadlineEvaluation:
    profile_id: str
    deadline_date: date | None
    blocking_issues: tuple[str, ...]
    warnings: tuple[str, ...]


@dataclass(frozen=True)
class _DeadlineRule:
    reference_field: Literal["decision_date", "hearing_date"]
    days: int
    direction: Literal["after", "before"]


_VALID_SUBMISSION_CHANNELS = frozenset(get_args(DocumentSubmissionChannel))
_CHANNEL_LIMITS: dict[DocumentSubmissionChannel, SubmissionChannelLimits] = {
    "portal": SubmissionChannelLimits(
        channel="portal",
        max_files=25,
        max_bytes_per_file=10 * 1024 * 1024,
    ),
    "email": SubmissionChannelLimits(
        channel="email",
        max_files=10,
        max_bytes_per_file=5 * 1024 * 1024,
    ),
    "fax": SubmissionChannelLimits(
        channel="fax",
        max_files=1,
        max_bytes_per_file=2 * 1024 * 1024,
    ),
    "mail": SubmissionChannelLimits(
        channel="mail",
        max_files=25,
        max_bytes_per_file=10 * 1024 * 1024,
    ),
    "in_person": SubmissionChannelLimits(
        channel="in_person",
        max_files=25,
        max_bytes_per_file=10 * 1024 * 1024,
    ),
}
_DEADLINE_RULES_BY_PROFILE: dict[str, _DeadlineRule] = {
    "federal_court_jr_leave": _DeadlineRule(
        reference_field="decision_date",
        days=30,
        direction="after",
    ),
    "federal_court_jr_hearing": _DeadlineRule(
        reference_field="hearing_date",
        days=10,
        direction="before",
    ),
    "rpd": _DeadlineRule(
        reference_field="hearing_date",
        days=10,
        direction="before",
    ),
    "rad": _DeadlineRule(
        reference_field="decision_date",
        days=15,
        direction="after",
    ),
    "id": _DeadlineRule(
        reference_field="hearing_date",
        days=5,
        direction="before",
    ),
    "iad": _DeadlineRule(
        reference_field="decision_date",
        days=30,
        direction="after",
    ),
    "iad_sponsorship": _DeadlineRule(
        reference_field="decision_date",
        days=30,
        direction="after",
    ),
    "iad_residency": _DeadlineRule(
        reference_field="decision_date",
        days=30,
        direction="after",
    ),
    "iad_admissibility": _DeadlineRule(
        reference_field="decision_date",
        days=30,
        direction="after",
    ),
}


def normalize_submission_channel(value: str | None) -> DocumentSubmissionChannel:
    normalized_channel = str(value or "").strip().lower() or "portal"
    if normalized_channel not in _VALID_SUBMISSION_CHANNELS:
        raise ValueError(f"Unsupported submission channel: {value}")
    return cast(DocumentSubmissionChannel, normalized_channel)


def submission_channel_limits(value: str | None) -> SubmissionChannelLimits:
    channel = normalize_submission_channel(value)
    return _CHANNEL_LIMITS[channel]


def is_near_submission_file_limit(*, file_count: int, limits: SubmissionChannelLimits) -> bool:
    if limits.max_files < 2:
        return False
    threshold = max(1, int(limits.max_files * limits.near_file_limit_ratio))
    return file_count >= threshold


def _deadline_date_for_rule(*, rule: _DeadlineRule, context: FilingDeadlineContext) -> date | None:
    reference_date = getattr(context, rule.reference_field)
    if reference_date is None:
        return None
    if rule.direction == "after":
        return reference_date + timedelta(days=rule.days)
    return reference_date - timedelta(days=rule.days)


def evaluate_filing_deadline(
    *,
    profile_id: str,
    context: FilingDeadlineContext,
) -> FilingDeadlineEvaluation:
    normalized_profile_id = str(profile_id).strip().lower()
    filing_date = context.filing_date or date.today()
    blocking_issues: set[str] = set()
    warnings: set[str] = set(context.preflight_warnings)

    if context.service_date and context.hearing_date and context.service_date > context.hearing_date:
        blocking_issues.add("service_date_after_hearing_date")
    if context.service_date and filing_date < context.service_date:
        blocking_issues.add("filing_date_before_service_date")

    rule = _DEADLINE_RULES_BY_PROFILE.get(normalized_profile_id)
    if rule is None:
        return FilingDeadlineEvaluation(
            profile_id=normalized_profile_id,
            deadline_date=None,
            blocking_issues=tuple(sorted(blocking_issues)),
            warnings=tuple(sorted(warnings)),
        )

    deadline_date = _deadline_date_for_rule(rule=rule, context=context)
    if deadline_date is None:
        if any(
            (
                context.decision_date is not None,
                context.hearing_date is not None,
                context.service_date is not None,
                bool(context.deadline_override_reason),
            )
        ):
            warnings.add("filing_deadline_not_evaluated_missing_dates")
        return FilingDeadlineEvaluation(
            profile_id=normalized_profile_id,
            deadline_date=None,
            blocking_issues=tuple(sorted(blocking_issues)),
            warnings=tuple(sorted(warnings)),
        )

    if filing_date > deadline_date:
        if context.deadline_override_reason:
            warnings.add("filing_deadline_override_applied")
        else:
            blocking_issues.add("filing_deadline_expired")
    elif (deadline_date - filing_date).days <= 3:
        warnings.add("filing_deadline_approaching")

    return FilingDeadlineEvaluation(
        profile_id=normalized_profile_id,
        deadline_date=deadline_date,
        blocking_issues=tuple(sorted(blocking_issues)),
        warnings=tuple(sorted(warnings)),
    )


__all__ = [
    "DocumentSubmissionChannel",
    "FilingDeadlineContext",
    "FilingDeadlineEvaluation",
    "SubmissionChannelLimits",
    "evaluate_filing_deadline",
    "is_near_submission_file_limit",
    "normalize_submission_channel",
    "submission_channel_limits",
]
