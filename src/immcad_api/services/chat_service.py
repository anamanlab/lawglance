from __future__ import annotations

import logging

from immcad_api.policy.compliance import (
    DISCLAIMER_TEXT,
    POLICY_REFUSAL_TEXT,
    enforce_citation_requirement,
    should_refuse_for_policy,
)
from immcad_api.errors import ProviderApiError
from immcad_api.providers import ProviderError, ProviderRouter
from immcad_api.retrieval import ChatRetriever, RetrievedDocument, map_retrieved_documents_to_citations
from immcad_api.schemas import ChatRequest, ChatResponse, Citation, FallbackUsed


_AUDIT_LOGGER = logging.getLogger("immcad_api.audit")
_LOGGER = logging.getLogger(__name__)


class ChatService:
    def __init__(
        self,
        provider_router: ProviderRouter,
        *,
        allow_scaffold_synthetic_citations: bool = False,
        retriever: ChatRetriever | None = None,
        enable_grounding: bool = False,
        grounding_top_k: int = 3,
    ) -> None:
        self.provider_router = provider_router
        self.allow_scaffold_synthetic_citations = allow_scaffold_synthetic_citations
        self.retriever = retriever
        self.enable_grounding = enable_grounding
        self.grounding_top_k = grounding_top_k

    def _emit_audit_event(
        self,
        *,
        trace_id: str | None,
        event_type: str,
        metadata: dict[str, str | int],
    ) -> None:
        _AUDIT_LOGGER.warning(
            "chat_audit_event",
            extra={
                "trace_id": trace_id or "trace-unavailable",
                "event_type": event_type,
                "metadata": metadata,
            },
        )

    def _grounding_documents(
        self,
        request: ChatRequest,
        *,
        trace_id: str | None,
    ) -> list[RetrievedDocument]:
        if not self.enable_grounding or self.retriever is None:
            return []
        try:
            return self.retriever.retrieve(
                query=request.message,
                locale=request.locale,
                top_k=self.grounding_top_k,
            )
        except Exception:  # pragma: no cover - defensive guard for adapter failures
            _LOGGER.warning(
                "chat_grounding_unavailable",
                extra={
                    "trace_id": trace_id or "trace-unavailable",
                    "locale": request.locale,
                    "top_k": self.grounding_top_k,
                },
                exc_info=True,
            )
            return []

    def handle_chat(self, request: ChatRequest, *, trace_id: str | None = None) -> ChatResponse:
        if should_refuse_for_policy(request.message):
            self._emit_audit_event(
                trace_id=trace_id,
                event_type="policy_block",
                metadata={
                    "locale": request.locale,
                    "mode": request.mode,
                    "message_length": len(request.message),
                },
            )
            return ChatResponse(
                answer=POLICY_REFUSAL_TEXT,
                citations=[],
                confidence="low",
                disclaimer=DISCLAIMER_TEXT,
                fallback_used=FallbackUsed(
                    used=False,
                    provider=None,
                    reason="policy_block",
                ),
            )

        grounding_documents = self._grounding_documents(request, trace_id=trace_id)
        grounding_citations = map_retrieved_documents_to_citations(grounding_documents)
        grounding_context = [
            document.text_snippet.strip()
            for document in grounding_documents
            if document.text_snippet.strip()
        ]
        if not grounding_context:
            grounding_context = None

        try:
            routed = self.provider_router.generate(
                message=request.message,
                citations=grounding_citations,
                locale=request.locale,
                grounding_context=grounding_context,
            )
        except ProviderError as exc:
            self._emit_audit_event(
                trace_id=trace_id,
                event_type="provider_error",
                metadata={
                    "provider": exc.provider,
                    "error_code": exc.code,
                    "locale": request.locale,
                    "mode": request.mode,
                },
            )
            raise ProviderApiError(exc.message) from exc

        citations = routed.result.citations
        if (
            self.allow_scaffold_synthetic_citations
            and routed.result.provider == "scaffold"
            and not citations
        ):
            citations = [
                Citation(
                    source_id="SCAFFOLD_DETERMINISTIC",
                    title="Deterministic scaffold citation (non-authoritative)",
                    url="https://www.canada.ca/en/immigration-refugees-citizenship.html",
                    pin="n/a",
                    snippet=(
                        "Synthetic citation for development scaffolding only. "
                        "Replace with retrieval-grounded citations before production rollout."
                    ),
                )
            ]

        answer, validated_citations, confidence = enforce_citation_requirement(
            routed.result.answer,
            citations,
        )

        fallback_provider = routed.result.provider if routed.fallback_used else None
        fallback_reason = routed.fallback_reason if routed.fallback_used else None

        return ChatResponse(
            answer=answer,
            citations=validated_citations,
            confidence=confidence,
            disclaimer=DISCLAIMER_TEXT,
            fallback_used=FallbackUsed(
                used=routed.fallback_used,
                provider=fallback_provider,
                reason=fallback_reason,
            ),
        )
