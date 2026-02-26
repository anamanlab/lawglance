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


def test_build_research_queries_adds_compact_citation_anchor_variant() -> None:
    queries = build_research_queries(
        "2024 FC 101 judicial review on procedural fairness",
        court="fc",
    )

    assert any(query.lower() == "2024 fc 101 precedent" for query in queries)


def test_build_research_queries_adds_compact_docket_anchor_variant() -> None:
    queries = build_research_queries(
        "A-1234-23 inadmissibility finding",
        court="fc",
    )

    assert any(query.lower() == "a-1234-23 precedent" for query in queries)


def test_build_research_queries_uses_structured_intake_anchors_and_objective() -> None:
    queries = build_research_queries(
        "Need support for inadmissibility judicial review",
        court="fc",
        intake={
            "objective": "distinguish_precedent",
            "issue_tags": ["credibility"],
            "anchor_citations": ["2023 FCA 77"],
            "anchor_dockets": ["A-77-23"],
            "fact_keywords": ["misrepresentation", "overstay"],
            "procedural_posture": "judicial_review",
        },
    )

    normalized_queries = [query.lower() for query in queries]
    assert "2023 fca 77 precedent" in normalized_queries
    assert "a-77-23 precedent" in normalized_queries
    assert any("distinguish precedent" in query for query in normalized_queries)
    assert any("misrepresentation" in query for query in normalized_queries)
