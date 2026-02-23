from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from immcad_api.retrieval import ChromaChatRetriever


@dataclass
class _FakeDocument:
    page_content: str
    metadata: dict[str, object]


class _FakeVectorStore:
    def __init__(
        self,
        *,
        rows: list[tuple[_FakeDocument, float]] | None = None,
        error: Exception | None = None,
    ) -> None:
        self.rows = rows or []
        self.error = error
        self.calls: list[tuple[str, int]] = []

    def similarity_search_with_relevance_scores(
        self, query: str, *, k: int
    ) -> list[tuple[_FakeDocument, float]]:
        self.calls.append((query, k))
        if self.error:
            raise self.error
        return self.rows


def test_chroma_retriever_maps_results_to_normalized_documents(tmp_path: Path) -> None:
    vector_store = _FakeVectorStore(
        rows=[
            (
                _FakeDocument(
                    page_content="IRPA section 11 applies to permanent residence applications.",
                    metadata={
                        "source_id": "IRPA",
                        "title": "Immigration and Refugee Protection Act",
                        "url": "https://laws-lois.justice.gc.ca/eng/acts/I-2.5/",
                        "pin": "s. 11",
                    },
                ),
                0.91,
            )
        ]
    )
    retriever = ChromaChatRetriever(
        vector_store=vector_store,
        persist_directory=tmp_path,
        score_threshold=0.30,
    )

    retrieved = retriever.retrieve(query="irpa section 11", locale="en-CA", top_k=4)

    assert len(retrieved) == 1
    assert retrieved[0].source_id == "IRPA"
    assert retrieved[0].title == "Immigration and Refugee Protection Act"
    assert retrieved[0].url == "https://laws-lois.justice.gc.ca/eng/acts/I-2.5/"
    assert retrieved[0].pin == "s. 11"
    assert "permanent residence applications" in retrieved[0].text_snippet
    assert vector_store.calls == [("irpa section 11", 4)]
    assert retriever.last_failure is None


def test_chroma_retriever_handles_missing_optional_metadata(tmp_path: Path) -> None:
    vector_store = _FakeVectorStore(
        rows=[(_FakeDocument(page_content="Some content", metadata={}), 0.75)]
    )
    retriever = ChromaChatRetriever(
        vector_store=vector_store,
        persist_directory=tmp_path,
    )

    retrieved = retriever.retrieve(query="query", locale="en-CA", top_k=3)

    assert len(retrieved) == 1
    assert retrieved[0].source_id == "unknown_source"
    assert retrieved[0].title is None
    assert retrieved[0].url is None
    assert retrieved[0].pin is None
    assert retrieved[0].text_snippet == "Some content"


def test_chroma_retriever_reports_missing_index_path(tmp_path: Path) -> None:
    missing_path = tmp_path / "missing-index"
    retriever = ChromaChatRetriever(persist_directory=missing_path)

    assert retriever.last_failure is not None
    assert retriever.last_failure.code == "index_missing"
    assert retriever.retrieve(query="query", locale="en-CA", top_k=3) == []


def test_chroma_retriever_reports_initialization_failure(tmp_path: Path) -> None:
    index_path = tmp_path / "index"
    index_path.mkdir()

    def _factory(_persist_directory: Path):
        raise RuntimeError("failed to initialize vector store")

    retriever = ChromaChatRetriever(
        persist_directory=index_path,
        vector_store_factory=_factory,
    )

    assert retriever.last_failure is not None
    assert retriever.last_failure.code == "initialization_failed"
    assert retriever.retrieve(query="query", locale="en-CA", top_k=3) == []


def test_chroma_retriever_reports_search_failure(tmp_path: Path) -> None:
    vector_store = _FakeVectorStore(error=RuntimeError("query failed"))
    retriever = ChromaChatRetriever(
        vector_store=vector_store,
        persist_directory=tmp_path,
    )

    assert retriever.retrieve(query="query", locale="en-CA", top_k=3) == []
    assert retriever.last_failure is not None
    assert retriever.last_failure.code == "search_failed"
