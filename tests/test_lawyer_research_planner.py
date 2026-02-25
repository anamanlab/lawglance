from __future__ import annotations

from immcad_api.services.lawyer_research_planner import (
    build_research_queries,
    extract_matter_profile,
)


def test_build_research_queries_expands_matter_into_multiple_queries() -> None:
    queries = build_research_queries(
        "FC appeal on procedural fairness and inadmissibility finding",
        court="fc",
    )

    assert len(queries) >= 3
    assert any("procedural fairness" in query.lower() for query in queries)
    assert any("fc" in query.lower() for query in queries)


def test_extract_matter_profile_detects_issue_tags_and_target_court() -> None:
    profile = extract_matter_profile(
        "Federal Court appeal concerning procedural fairness, inadmissibility, and credibility findings"
    )

    issue_tags = profile.get("issue_tags")
    assert isinstance(issue_tags, list)
    assert "procedural_fairness" in issue_tags
    assert "inadmissibility" in issue_tags
    assert profile.get("target_court") == "fc"

    fact_keywords = profile.get("fact_keywords")
    assert isinstance(fact_keywords, list)
    assert fact_keywords
