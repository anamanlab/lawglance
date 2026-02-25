from __future__ import annotations

import pytest

from immcad_api.api.routes.case_query_validation import is_specific_case_query


@pytest.mark.parametrize(
    "query",
    [
        "A-1234-23",
        "T-123-24",
        "IMM-1234-24",
        "2026 FC 101",
        "2023 SCC 5",
    ],
)
def test_case_query_validation_accepts_specific_docket_and_citation_patterns(
    query: str,
) -> None:
    assert is_specific_case_query(query) is True


@pytest.mark.parametrize("query", ["to be", "and the or", "123 456"])
def test_case_query_validation_rejects_broad_or_non_specific_queries(query: str) -> None:
    assert is_specific_case_query(query) is False
