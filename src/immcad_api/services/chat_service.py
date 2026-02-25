from __future__ import annotations

from datetime import date
import logging
import re
from typing import Protocol

from immcad_api.errors import ApiError, ProviderApiError
from immcad_api.policy.compliance import (
    DEFAULT_TRUSTED_CITATION_DOMAINS,
    DISCLAIMER_TEXT,
    POLICY_REFUSAL_TEXT,
    SAFE_CONSTRAINED_RESPONSE,
    enforce_citation_requirement,
    normalize_trusted_domains,
    should_refuse_for_policy,
)
from immcad_api.providers import ProviderError, ProviderRouter
from immcad_api.schemas import (
    CaseSearchRequest,
    CaseSearchResponse,
    CaseSearchResult,
    ChatRequest,
    ChatResponse,
    Citation,
    FallbackUsed,
)
from immcad_api.services.grounding import GroundingAdapter, StaticGroundingAdapter


AUDIT_LOGGER = logging.getLogger("immcad_api.audit")
_CASE_SEARCH_TOOL_PATTERN = re.compile(
    r"\b(case law|precedent|judg(?:e)?ment|decision|ruling|canlii|"
    r"supreme court|federal court|court of appeal)\b",
    re.IGNORECASE,
)


class CaseSearchTool(Protocol):
    def search(self, request: CaseSearchRequest) -> CaseSearchResponse: ...


def _extract_rejected_citation_urls(citations: list[object]) -> tuple[str, ...]:
    urls: list[str] = []
    for citation in citations:
        raw_url: object | None
        if isinstance(citation, Citation):
            raw_url = citation.url
        elif isinstance(citation, dict):
            raw_url = citation.get("url")
        else:
            raw_url = None
        if isinstance(raw_url, str) and raw_url.strip():
            urls.append(raw_url.strip())
    return tuple(urls)


class ChatService:
    def __init__(
        self,
        provider_router: ProviderRouter,
        *,
        grounding_adapter: GroundingAdapter | None = None,
        trusted_citation_domains: tuple[str, ...] | list[str] | None = None,
        case_search_tool: CaseSearchTool | None = None,
        case_search_tool_limit: int = 3,
    ) -> None:
        if case_search_tool_limit < 1:
            raise ValueError("case_search_tool_limit must be >= 1")
        self.provider_router = provider_router
        self.grounding_adapter = grounding_adapter or StaticGroundingAdapter()
        self.trusted_citation_domains = normalize_trusted_domains(
            trusted_citation_domains if trusted_citation_domains is not None else DEFAULT_TRUSTED_CITATION_DOMAINS
        )
        self.case_search_tool = case_search_tool
        self.case_search_tool_limit = case_search_tool_limit

    def _should_use_case_search_tool(self, message: str) -> bool:
        return _CASE_SEARCH_TOOL_PATTERN.search(message) is not None

    def _case_result_to_citation(self, result: CaseSearchResult) -> Citation | None:
        case_url = result.url.strip()
        if not case_url:
            return None
        source_id = (result.source_id or "CASE_LAW").strip() or "CASE_LAW"
        title = result.title.strip() or "Case law reference"
        pin = result.citation.strip() or result.case_id.strip() or result.decision_date.isoformat()
        snippet_date = (
            result.decision_date.isoformat()
            if isinstance(result.decision_date, date)
            else str(result.decision_date)
        )
        snippet = f"{title} ({snippet_date})"
        return Citation(
            source_id=source_id,
            title=title,
            url=case_url,
            pin=pin,
            snippet=snippet,
        )

    def _fetch_case_search_citations(
        self,
        *,
        request: ChatRequest,
        trace_id: str | None,
    ) -> list[Citation]:
        if self.case_search_tool is None:
            return []
        if not self._should_use_case_search_tool(request.message):
            return []

        try:
            case_response = self.case_search_tool.search(
                CaseSearchRequest(
                    query=request.message,
                    jurisdiction="ca",
                    limit=self.case_search_tool_limit,
                )
            )
        except ApiError as exc:
            self._emit_audit_event(
                trace_id=trace_id,
                event_type="case_search_tool_error",
                locale=request.locale,
                mode=request.mode,
                message_length=len(request.message),
                tool_name="case_search",
                tool_error_code=exc.code,
            )
            return []
        except Exception:
            self._emit_audit_event(
                trace_id=trace_id,
                event_type="case_search_tool_error",
                locale=request.locale,
                mode=request.mode,
                message_length=len(request.message),
                tool_name="case_search",
                tool_error_code="unexpected_error",
            )
            return []

        tool_citations: list[Citation] = []
        seen: set[tuple[str, str, str]] = set()
        for case_result in case_response.results:
            citation = self._case_result_to_citation(case_result)
            if citation is None:
                continue
            key = (
                citation.source_id.lower(),
                citation.url.strip().lower(),
                citation.pin.strip().lower(),
            )
            if key in seen:
                continue
            seen.add(key)
            tool_citations.append(citation)

        if tool_citations:
            self._emit_audit_event(
                trace_id=trace_id,
                event_type="case_search_tool_used",
                locale=request.locale,
                mode=request.mode,
                message_length=len(request.message),
                tool_name="case_search",
                tool_result_count=len(case_response.results),
                candidate_citation_count=len(tool_citations),
            )

        return tool_citations

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
        case_search_citations = self._fetch_case_search_citations(
            request=request,
            trace_id=trace_id,
        )
        if case_search_citations:
            citations = [*citations, *case_search_citations]

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
            normalized_message = exc.message.lower()
            is_transient_provider_failure = (
                exc.code in {"timeout", "rate_limit"}
                or "circuit breaker open" in normalized_message
                or "resource_exhausted" in normalized_message
                or "quota" in normalized_message
                or "429" in normalized_message
            )
            if is_transient_provider_failure:
                return ChatResponse(
                    answer=SAFE_CONSTRAINED_RESPONSE,
                    citations=[],
                    confidence="low",
                    disclaimer=DISCLAIMER_TEXT,
                    fallback_used=FallbackUsed(
                        used=True,
                        provider=exc.provider,
                        reason="provider_error",
                    ),
                )
            raise ProviderApiError(exc.message) from exc

        answer, validated_citations, confidence = enforce_citation_requirement(
            routed.result.answer,
            routed.result.citations,
            grounded_citations=citations,
            trusted_domains=self.trusted_citation_domains,
        )
        if routed.result.citations and not validated_citations:
            self._emit_audit_event(
                trace_id=trace_id,
                event_type="grounding_validation_failed",
                locale=request.locale,
                mode=request.mode,
                message_length=len(request.message),
                provider=routed.result.provider,
                provider_citation_count=len(routed.result.citations),
                candidate_citation_count=len(citations),
                rejected_citation_urls=_extract_rejected_citation_urls(routed.result.citations),
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
        tool_name: str | None = None,
        tool_error_code: str | None = None,
        tool_result_count: int | None = None,
        provider_citation_count: int | None = None,
        candidate_citation_count: int | None = None,
        rejected_citation_urls: tuple[str, ...] | None = None,
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
        if tool_name:
            event["tool_name"] = tool_name
        if tool_error_code:
            event["tool_error_code"] = tool_error_code
        if tool_result_count is not None:
            event["tool_result_count"] = tool_result_count
        if provider_citation_count is not None:
            event["provider_citation_count"] = provider_citation_count
        if candidate_citation_count is not None:
            event["candidate_citation_count"] = candidate_citation_count
        if rejected_citation_urls:
            event["rejected_citation_urls"] = list(rejected_citation_urls)
        AUDIT_LOGGER.info("chat_audit_event", extra={"audit_event": event})
