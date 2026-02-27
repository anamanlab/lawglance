from __future__ import annotations

from datetime import date

import pytest

from immcad_api.policy.document_filing_deadlines import (
    FilingDeadlineContext,
    evaluate_filing_deadline,
)


@pytest.mark.parametrize(
    ("profile_id", "context"),
    [
        (
            "federal_court_jr_leave",
            FilingDeadlineContext(
                decision_date=date(2026, 1, 1),
                filing_date=date(2026, 1, 20),
            ),
        ),
        (
            "federal_court_jr_hearing",
            FilingDeadlineContext(
                hearing_date=date(2026, 3, 20),
                filing_date=date(2026, 3, 5),
            ),
        ),
        (
            "rpd",
            FilingDeadlineContext(
                hearing_date=date(2026, 4, 20),
                filing_date=date(2026, 4, 7),
            ),
        ),
        (
            "rad",
            FilingDeadlineContext(
                decision_date=date(2026, 2, 1),
                filing_date=date(2026, 2, 10),
            ),
        ),
        (
            "id",
            FilingDeadlineContext(
                hearing_date=date(2026, 5, 20),
                filing_date=date(2026, 5, 15),
            ),
        ),
        (
            "iad",
            FilingDeadlineContext(
                decision_date=date(2026, 6, 1),
                filing_date=date(2026, 6, 20),
            ),
        ),
        (
            "iad_sponsorship",
            FilingDeadlineContext(
                decision_date=date(2026, 6, 1),
                filing_date=date(2026, 6, 20),
            ),
        ),
        (
            "iad_residency",
            FilingDeadlineContext(
                decision_date=date(2026, 6, 1),
                filing_date=date(2026, 6, 20),
            ),
        ),
        (
            "iad_admissibility",
            FilingDeadlineContext(
                decision_date=date(2026, 6, 1),
                filing_date=date(2026, 6, 20),
            ),
        ),
    ],
)
def test_deadline_evaluator_passes_for_supported_profiles_within_window(
    profile_id: str,
    context: FilingDeadlineContext,
) -> None:
    result = evaluate_filing_deadline(profile_id=profile_id, context=context)

    assert result.blocking_issues == ()


@pytest.mark.parametrize(
    ("profile_id", "context"),
    [
        (
            "federal_court_jr_leave",
            FilingDeadlineContext(
                decision_date=date(2026, 1, 1),
                filing_date=date(2026, 2, 5),
            ),
        ),
        (
            "federal_court_jr_hearing",
            FilingDeadlineContext(
                hearing_date=date(2026, 3, 20),
                filing_date=date(2026, 3, 16),
            ),
        ),
        (
            "rpd",
            FilingDeadlineContext(
                hearing_date=date(2026, 4, 20),
                filing_date=date(2026, 4, 15),
            ),
        ),
        (
            "rad",
            FilingDeadlineContext(
                decision_date=date(2026, 2, 1),
                filing_date=date(2026, 2, 20),
            ),
        ),
        (
            "id",
            FilingDeadlineContext(
                hearing_date=date(2026, 5, 20),
                filing_date=date(2026, 5, 19),
            ),
        ),
        (
            "iad",
            FilingDeadlineContext(
                decision_date=date(2026, 6, 1),
                filing_date=date(2026, 7, 5),
            ),
        ),
        (
            "iad_sponsorship",
            FilingDeadlineContext(
                decision_date=date(2026, 6, 1),
                filing_date=date(2026, 7, 5),
            ),
        ),
        (
            "iad_residency",
            FilingDeadlineContext(
                decision_date=date(2026, 6, 1),
                filing_date=date(2026, 7, 5),
            ),
        ),
        (
            "iad_admissibility",
            FilingDeadlineContext(
                decision_date=date(2026, 6, 1),
                filing_date=date(2026, 7, 5),
            ),
        ),
    ],
)
def test_deadline_evaluator_blocks_when_filing_window_is_missed(
    profile_id: str,
    context: FilingDeadlineContext,
) -> None:
    result = evaluate_filing_deadline(profile_id=profile_id, context=context)

    assert "filing_deadline_expired" in result.blocking_issues


def test_deadline_evaluator_allows_expired_window_with_override_reason() -> None:
    result = evaluate_filing_deadline(
        profile_id="rad",
        context=FilingDeadlineContext(
            decision_date=date(2026, 2, 1),
            filing_date=date(2026, 2, 20),
            deadline_override_reason="Extension granted by registry.",
        ),
    )

    assert result.blocking_issues == ()
    assert "filing_deadline_override_applied" in result.warnings
