from __future__ import annotations

from immcad_api.services.grounding import KeywordGroundingAdapter, official_grounding_catalog


def test_keyword_grounding_adapter_includes_pr_card_sources_for_pr_card_query() -> None:
    adapter = KeywordGroundingAdapter(official_grounding_catalog(), max_citations=3)

    citations = adapter.citation_candidates(
        message="my pr card expired while I was outside canada, how do I renew?",
        locale="en-CA",
        mode="standard",
    )

    assert citations
    assert any(citation.pin == "PR card renewal guide" for citation in citations)
    assert len(citations) <= 3


def test_keyword_grounding_adapter_returns_no_citations_for_unmatched_query() -> None:
    adapter = KeywordGroundingAdapter(official_grounding_catalog(), max_citations=3)

    citations = adapter.citation_candidates(
        message="hello",
        locale="en-CA",
        mode="standard",
    )

    assert citations == []


def test_keyword_grounding_adapter_surfaces_study_permit_extension_guidance() -> None:
    adapter = KeywordGroundingAdapter(official_grounding_catalog(), max_citations=3)

    citations = adapter.citation_candidates(
        message="How can I extend my study permit while in Canada?",
        locale="en-CA",
        mode="standard",
    )

    assert citations
    assert any(citation.pin == "Study permit extension guide" for citation in citations)


def test_keyword_grounding_adapter_surfaces_spousal_sponsorship_guidance() -> None:
    adapter = KeywordGroundingAdapter(official_grounding_catalog(), max_citations=3)

    citations = adapter.citation_candidates(
        message="What is the process to sponsor my spouse for permanent residence?",
        locale="en-CA",
        mode="standard",
    )

    assert citations
    assert any(citation.pin == "Spousal sponsorship guide" for citation in citations)


def test_keyword_grounding_adapter_surfaces_work_permit_guidance() -> None:
    adapter = KeywordGroundingAdapter(official_grounding_catalog(), max_citations=3)

    citations = adapter.citation_candidates(
        message="How do I apply for a work permit from inside Canada?",
        locale="en-CA",
        mode="standard",
    )

    assert citations
    assert any(citation.pin == "Work permit guide" for citation in citations)


def test_keyword_grounding_adapter_surfaces_visitor_status_extension_guidance() -> None:
    adapter = KeywordGroundingAdapter(official_grounding_catalog(), max_citations=3)

    citations = adapter.citation_candidates(
        message="My visitor status is expiring. How can I extend my stay in Canada?",
        locale="en-CA",
        mode="standard",
    )

    assert citations
    assert any(citation.pin == "Visitor status extension guide" for citation in citations)
