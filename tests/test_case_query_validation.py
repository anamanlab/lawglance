from __future__ import annotations

import pytest

from immcad_api.api.routes.case_query_validation import (
    assess_case_query,
    is_specific_case_query,
)


@pytest.mark.parametrize(
    "query",
    [
        "A-1234-23",
        "T-123-24",
        "IMM-1234-24",
        "2026 FC 101",
        "2023 SCC 5",
        "JR on H&C",
        "FC JR on H&C refusal",
    ],
)
def test_case_query_validation_accepts_specific_docket_and_citation_patterns(
    query: str,
) -> None:
    assert is_specific_case_query(query) is True


@pytest.mark.parametrize("query", ["to be", "and the or", "123 456"])
def test_case_query_validation_rejects_broad_or_non_specific_queries(query: str) -> None:
    assert is_specific_case_query(query) is False


def test_case_query_assessment_reports_specific_query_without_hints() -> None:
    assessment = assess_case_query("Federal Court JR on H&C refusal 2024 FC 101")

    assert assessment.is_specific is True
    assert assessment.hints == []


def test_case_query_assessment_reports_broad_query_with_refinement_hints() -> None:
    assessment = assess_case_query("help with immigration")

    assert assessment.is_specific is False
    assert len(assessment.hints) >= 1
    assert any("court" in hint.lower() or "citation" in hint.lower() for hint in assessment.hints)
