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
from immcad_api.schemas import ChatRequest, ChatResponse, FallbackUsed
from immcad_api.services.grounding import GroundingAdapter, StaticGroundingAdapter


AUDIT_LOGGER = logging.getLogger("immcad_api.audit")


class ChatService:
    def __init__(
        self,
        provider_router: ProviderRouter,
        *,
        grounding_adapter: GroundingAdapter | None = None,
    ) -> None:
        self.provider_router = provider_router
        self.grounding_adapter = grounding_adapter or StaticGroundingAdapter()

    def handle_chat(self, request: ChatRequest, *, trace_id: str | None = None) -> ChatResponse:
        if should_refuse_for_policy(request.message):
            self._emit_audit_event(
                trace_id=trace_id,
                event_type="policy_block",
                locale=request.locale,
                mode=request.mode,
                message_length=len(request.message),
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

        citations = self.grounding_adapter.citation_candidates(
            message=request.message,
            locale=request.locale,
            mode=request.mode,
        )

        try:
            routed = self.provider_router.generate(
                message=request.message,
                citations=citations,
                locale=request.locale,
            )
        except ProviderError as exc:
            self._emit_audit_event(
                trace_id=trace_id,
                event_type="provider_error",
                locale=request.locale,
                mode=request.mode,
                message_length=len(request.message),
                provider=exc.provider,
                provider_error_code=exc.code,
            )
            raise ProviderApiError(exc.message) from exc

        answer, validated_citations, confidence = enforce_citation_requirement(
            routed.result.answer,
            routed.result.citations,
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

    def _emit_audit_event(
        self,
        *,
        trace_id: str | None,
        event_type: str,
        locale: str,
        mode: str,
        message_length: int,
        provider: str | None = None,
        provider_error_code: str | None = None,
    ) -> None:
        event: dict[str, object] = {
            "trace_id": trace_id or "",
            "event_type": event_type,
            "locale": locale,
            "mode": mode,
            "message_length": message_length,
        }
        if provider:
            event["provider"] = provider
        if provider_error_code:
            event["provider_error_code"] = provider_error_code
        AUDIT_LOGGER.info("chat_audit_event", extra={"audit_event": event})
