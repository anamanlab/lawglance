from __future__ import annotations

from immcad_api.retrieval import (
    FALLBACK_CITATION_PIN,
    FALLBACK_CITATION_URL,
    RetrievedDocument,
    map_retrieved_documents_to_citations,
)


def test_map_retrieved_documents_to_citations_uses_source_metadata() -> None:
    documents = [
        RetrievedDocument(
            text_snippet="IRPA s.11 governs visa requirements.",
            source_id="IRPA",
            source_type="statute",
            title="Immigration and Refugee Protection Act",
            url="https://laws-lois.justice.gc.ca/eng/acts/I-2.5/",
            pin="s.11",
        )
    ]

    citations = map_retrieved_documents_to_citations(documents)

    assert len(citations) == 1
    assert citations[0].source_id == "IRPA"
    assert citations[0].title == "Immigration and Refugee Protection Act"
    assert citations[0].url == "https://laws-lois.justice.gc.ca/eng/acts/I-2.5/"
    assert citations[0].pin == "s.11"
    assert citations[0].snippet == "IRPA s.11 governs visa requirements."


def test_map_retrieved_documents_to_citations_handles_missing_optional_metadata() -> None:
    documents = [
        RetrievedDocument(
            text_snippet="Program delivery instructions mention filing pathways.",
            source_id="PDI",
        )
    ]

    citations = map_retrieved_documents_to_citations(documents)

    assert len(citations) == 1
    assert citations[0].source_id == "PDI"
    assert citations[0].title == "Source: PDI"
    assert citations[0].url == FALLBACK_CITATION_URL
    assert citations[0].pin == FALLBACK_CITATION_PIN
    assert citations[0].snippet == "Program delivery instructions mention filing pathways."


def test_map_retrieved_documents_to_citations_handles_empty_input() -> None:
    assert map_retrieved_documents_to_citations([]) == []
