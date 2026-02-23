from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
import os
from pathlib import Path
from typing import Callable, Literal, Protocol

from pydantic import BaseModel, Field

from immcad_api.schemas import Citation


FALLBACK_CITATION_URL = "https://www.canada.ca/en/immigration-refugees-citizenship.html"
FALLBACK_CITATION_PIN = "n/a"
FailureCode = Literal["index_missing", "initialization_failed", "search_failed"]


class RetrievedDocument(BaseModel):
    text_snippet: str = Field(min_length=1, max_length=6000)
    source_id: str = Field(min_length=1, max_length=128)
    source_type: str | None = Field(default=None, max_length=64)
    title: str | None = Field(default=None, max_length=256)
    url: str | None = Field(default=None, max_length=2048)
    pin: str | None = Field(default=None, max_length=256)


@dataclass(frozen=True)
class RetrieverFailure:
    code: FailureCode
    message: str


class ChatRetriever(Protocol):
    def retrieve(self, *, query: str, locale: str, top_k: int) -> list[RetrievedDocument]:
        ...


class _VectorStoreDocument(Protocol):
    page_content: str
    metadata: dict[str, object]


class _VectorStore(Protocol):
    def similarity_search_with_relevance_scores(
        self, query: str, *, k: int
    ) -> list[tuple[_VectorStoreDocument, float]]:
        ...


VectorStoreFactory = Callable[[Path], _VectorStore]


def _default_vector_store_factory(persist_directory: Path) -> _VectorStore:
    from langchain_chroma import Chroma
    from langchain_openai import OpenAIEmbeddings

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is required to initialize Chroma retriever")

    embeddings = OpenAIEmbeddings(api_key=api_key)
    return Chroma(
        persist_directory=str(persist_directory),
        embedding_function=embeddings,
    )


class NullChatRetriever:
    """No-op retriever that preserves legacy ungrounded behavior."""

    def retrieve(self, *, query: str, locale: str, top_k: int) -> list[RetrievedDocument]:
        return []


class ChromaChatRetriever:
    def __init__(
        self,
        *,
        persist_directory: str | Path = Path("chroma_db_legal_bot_part1"),
        score_threshold: float | None = 0.30,
        vector_store: _VectorStore | None = None,
        vector_store_factory: VectorStoreFactory | None = None,
    ) -> None:
        self.persist_directory = Path(persist_directory)
        self.score_threshold = score_threshold
        self.last_failure: RetrieverFailure | None = None

        if vector_store is not None:
            self._vector_store = vector_store
            return

        factory = vector_store_factory or _default_vector_store_factory
        self._vector_store = self._initialize_vector_store(factory)

    def _initialize_vector_store(self, factory: VectorStoreFactory) -> _VectorStore | None:
        if not self.persist_directory.exists():
            self.last_failure = RetrieverFailure(
                code="index_missing",
                message=f"Chroma index path not found: {self.persist_directory}",
            )
            return None

        try:
            return factory(self.persist_directory)
        except Exception as exc:
            self.last_failure = RetrieverFailure(
                code="initialization_failed",
                message=str(exc),
            )
            return None

    def retrieve(self, *, query: str, locale: str, top_k: int) -> list[RetrievedDocument]:
        del locale
        if not query.strip() or top_k < 1 or self._vector_store is None:
            return []

        try:
            rows = self._vector_store.similarity_search_with_relevance_scores(
                query,
                k=top_k,
            )
        except Exception as exc:
            self.last_failure = RetrieverFailure(
                code="search_failed",
                message=str(exc),
            )
            return []

        self.last_failure = None
        documents: list[RetrievedDocument] = []
        for document, score in rows:
            if self.score_threshold is not None and score < self.score_threshold:
                continue
            documents.append(self._normalize_document(document))
        return documents

    def _normalize_document(self, document: _VectorStoreDocument) -> RetrievedDocument:
        metadata = document.metadata or {}
        source_id = self._metadata_text(metadata, "source_id") or "unknown_source"
        title = self._metadata_text(metadata, "title") or self._metadata_text(
            metadata, "instrument"
        )
        url = self._metadata_text(metadata, "url")
        pin = self._metadata_text(metadata, "pin") or self._metadata_text(metadata, "section")
        text_snippet = (document.page_content or "").strip() or "No excerpt available."

        return RetrievedDocument(
            text_snippet=text_snippet,
            source_id=source_id,
            source_type=self._metadata_text(metadata, "source_type"),
            title=title,
            url=url,
            pin=pin,
        )

    @staticmethod
    def _metadata_text(metadata: dict[str, object], key: str) -> str | None:
        raw = metadata.get(key)
        if raw is None:
            return None
        text = str(raw).strip()
        return text or None


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
