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
    assert citations[0].source_id == "IRPA"
    assert any(citation.pin == "PR card renewal guide" for citation in citations)


def test_keyword_grounding_adapter_always_returns_baseline_citation() -> None:
    adapter = KeywordGroundingAdapter(official_grounding_catalog(), max_citations=3)

    citations = adapter.citation_candidates(
        message="hello",
        locale="en-CA",
        mode="standard",
    )

    assert len(citations) == 1
    assert citations[0].source_id == "IRPA"
    assert citations[0].pin == "s. 11"
