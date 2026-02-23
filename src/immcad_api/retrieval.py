from __future__ import annotations

from collections.abc import Iterable
from typing import Protocol

from pydantic import BaseModel, Field

from immcad_api.schemas import Citation


FALLBACK_CITATION_URL = "https://www.canada.ca/en/immigration-refugees-citizenship.html"
FALLBACK_CITATION_PIN = "n/a"


class RetrievedDocument(BaseModel):
    text_snippet: str = Field(min_length=1, max_length=6000)
    source_id: str = Field(min_length=1, max_length=128)
    source_type: str | None = Field(default=None, max_length=64)
    title: str | None = Field(default=None, max_length=256)
    url: str | None = Field(default=None, max_length=2048)
    pin: str | None = Field(default=None, max_length=256)


class ChatRetriever(Protocol):
    def retrieve(self, *, query: str, locale: str, top_k: int) -> list[RetrievedDocument]:
        ...


class NullChatRetriever:
    """No-op retriever that preserves legacy ungrounded behavior."""

    def retrieve(self, *, query: str, locale: str, top_k: int) -> list[RetrievedDocument]:
        return []


def map_retrieved_documents_to_citations(
    documents: Iterable[RetrievedDocument],
) -> list[Citation]:
    citations: list[Citation] = []
    for document in documents:
        citations.append(
            Citation(
                source_id=document.source_id,
                title=document.title or f"Source: {document.source_id}",
                url=document.url or FALLBACK_CITATION_URL,
                pin=document.pin or FALLBACK_CITATION_PIN,
                snippet=document.text_snippet,
            )
        )
    return citations
