from __future__ import annotations

from dataclasses import dataclass
import logging

import pytest

from immcad_api.errors import ProviderApiError
from immcad_api.policy.compliance import DISCLAIMER_TEXT, POLICY_REFUSAL_TEXT
from immcad_api.providers.base import ProviderError, ProviderResult
from immcad_api.providers.router import RoutingResult
from immcad_api.retrieval import RetrievedDocument
from immcad_api.schemas import ChatRequest, Citation
from immcad_api.services.chat_service import ChatService


@dataclass
class _RoutingMock:
    result: ProviderResult
    fallback_used: bool
    fallback_reason: str | None

    def generate(
        self,
        *,
        message: str,
        citations,
        locale: str,
        grounding_context=None,
    ) -> RoutingResult:
        del message, locale, grounding_context
        return RoutingResult(
            result=self.result,
            fallback_used=self.fallback_used,
            fallback_reason=self.fallback_reason,
        )


class _ErrorRouter:
    def generate(
        self,
        *,
        message: str,
        citations,
        locale: str,
        grounding_context=None,
    ) -> RoutingResult:
        del message, citations, locale, grounding_context
        raise ProviderError("openai", "provider_error", "boom")


class _EchoRouter:
    def __init__(self) -> None:
        self.call_count = 0
        self.last_citations: list[Citation] = []
        self.last_grounding_context: list[str] | None = None

    def generate(
        self,
        *,
        message: str,
        citations,
        locale: str,
        grounding_context=None,
    ) -> RoutingResult:
        del message, locale
        self.call_count += 1
        self.last_citations = list(citations)
        self.last_grounding_context = list(grounding_context) if grounding_context else None
        return RoutingResult(
            result=ProviderResult(
                provider="gemini",
                answer="Grounded answer",
                citations=list(citations),
                confidence="medium",
            ),
            fallback_used=False,
            fallback_reason=None,
        )


class _RetrieverStub:
    def __init__(self, documents: list[RetrievedDocument]) -> None:
        self.documents = documents
        self.calls: list[tuple[str, str, int]] = []

    def retrieve(self, *, query: str, locale: str, top_k: int) -> list[RetrievedDocument]:
        self.calls.append((query, locale, top_k))
        return self.documents


def _build_request(message: str = "Tell me about IRPA s.11") -> ChatRequest:
    return ChatRequest(
        session_id="session-12345",
        message=message,
        locale="en-CA",
        mode="standard",
    )


def _provider_result(citations: list[Citation]) -> ProviderResult:
    return ProviderResult(
        provider="gemini",
        answer="Sample answer",
        citations=citations,
        confidence="medium",
    )


def test_handle_chat_policy_refusal_short_circuits(caplog: pytest.LogCaptureFixture) -> None:
    service = ChatService(_RoutingMock(_provider_result([]), False, None))

    with caplog.at_level(logging.WARNING, logger="immcad_api.audit"):
        response = service.handle_chat(
            _build_request("Please represent me in my immigration file"),
            trace_id="trace-policy-1",
        )

    assert response.answer == POLICY_REFUSAL_TEXT
    assert response.disclaimer == DISCLAIMER_TEXT
    assert response.fallback_used.used is False
    assert response.citations == []
    assert response.confidence == "low"

    audit_record = next(
        record for record in caplog.records if getattr(record, "event_type", "") == "policy_block"
    )
    assert audit_record.trace_id == "trace-policy-1"
    assert audit_record.metadata == {
        "locale": "en-CA",
        "mode": "standard",
        "message_length": len("Please represent me in my immigration file"),
    }


def test_handle_chat_uses_provider_result_and_reports_fallback() -> None:
    citation = Citation(
        source_id="IRPA",
        title="Immigration and Refugee Protection Act",
        url="https://example.com",
        pin="s.11(1)",
        snippet="Test snippet",
    )
    result = _provider_result([citation])
    router = _RoutingMock(result, fallback_used=True, fallback_reason="timeout")
    service = ChatService(router)

    response = service.handle_chat(_build_request())

    assert response.answer == result.answer
    assert response.citations == [citation]
    assert response.confidence == "medium"
    assert response.fallback_used.used is True
    assert response.fallback_used.provider == "gemini"
    assert response.fallback_used.reason == "timeout"


def test_handle_chat_translates_provider_errors(caplog: pytest.LogCaptureFixture) -> None:
    service = ChatService(_ErrorRouter())
    with caplog.at_level(logging.WARNING, logger="immcad_api.audit"):
        with pytest.raises(ProviderApiError):
            service.handle_chat(_build_request(), trace_id="trace-provider-1")

    audit_record = next(
        record for record in caplog.records if getattr(record, "event_type", "") == "provider_error"
    )
    assert audit_record.trace_id == "trace-provider-1"
    assert audit_record.metadata == {
        "provider": "openai",
        "error_code": "provider_error",
        "locale": "en-CA",
        "mode": "standard",
    }


def test_handle_chat_adds_scaffold_synthetic_citation_when_enabled() -> None:
    result = _provider_result([])
    result.provider = "scaffold"
    router = _RoutingMock(result, fallback_used=False, fallback_reason=None)
    service = ChatService(router, allow_scaffold_synthetic_citations=True)

    response = service.handle_chat(_build_request())

    assert response.citations
    assert response.citations[0].source_id == "SCAFFOLD_DETERMINISTIC"
    assert response.confidence == "medium"


def test_handle_chat_refuses_when_citations_missing_and_scaffold_mode_disabled() -> None:
    result = _provider_result([])
    result.provider = "scaffold"
    router = _RoutingMock(result, fallback_used=False, fallback_reason=None)
    service = ChatService(router, allow_scaffold_synthetic_citations=False)

    response = service.handle_chat(_build_request())

    assert response.citations == []
    assert response.confidence == "low"
    assert "do not have enough grounded legal context" in response.answer.lower()


def test_handle_chat_uses_grounding_retriever_when_enabled() -> None:
    router = _EchoRouter()
    retriever = _RetrieverStub(
        [
            RetrievedDocument(
                text_snippet="IRPA s.11 governs visa requirements.",
                source_id="IRPA",
                source_type="statute",
                title="Immigration and Refugee Protection Act",
                url="https://laws-lois.justice.gc.ca/eng/acts/I-2.5/",
                pin="s.11",
            )
        ]
    )
    service = ChatService(
        router,
        retriever=retriever,
        enable_grounding=True,
        grounding_top_k=2,
    )

    response = service.handle_chat(_build_request())

    assert retriever.calls == [("Tell me about IRPA s.11", "en-CA", 2)]
    assert router.call_count == 1
    assert len(router.last_citations) == 1
    assert router.last_citations[0].source_id == "IRPA"
    assert router.last_grounding_context == ["IRPA s.11 governs visa requirements."]
    assert response.citations == router.last_citations


def test_handle_chat_returns_insufficient_context_when_grounding_retrieval_is_empty() -> None:
    router = _EchoRouter()
    retriever = _RetrieverStub([])
    service = ChatService(
        router,
        retriever=retriever,
        enable_grounding=True,
        grounding_top_k=3,
    )

    response = service.handle_chat(_build_request())

    assert retriever.calls == [("Tell me about IRPA s.11", "en-CA", 3)]
    assert router.call_count == 0
    assert response.citations == []
    assert response.confidence == "low"
    assert response.fallback_used.used is False
    assert response.fallback_used.reason == "insufficient_context"


def test_handle_chat_returns_insufficient_context_when_grounding_unavailable() -> None:
    router = _EchoRouter()
    service = ChatService(
        router,
        retriever=None,
        enable_grounding=True,
        grounding_top_k=3,
    )

    response = service.handle_chat(_build_request())

    assert router.call_count == 0
    assert router.last_citations == []
    assert router.last_grounding_context is None
    assert response.citations == []
    assert response.confidence == "low"
    assert response.fallback_used.used is False
    assert response.fallback_used.reason == "insufficient_context"
