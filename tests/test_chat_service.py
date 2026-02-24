from __future__ import annotations

from dataclasses import dataclass
import json
import logging

import pytest

from immcad_api.errors import ProviderApiError
from immcad_api.policy.compliance import DISCLAIMER_TEXT, POLICY_REFUSAL_TEXT
from immcad_api.providers import ProviderError
from immcad_api.providers.base import ProviderResult
from immcad_api.providers.router import RoutingResult
from immcad_api.schemas import ChatRequest, Citation
from immcad_api.services.chat_service import ChatService
from immcad_api.services.grounding import StaticGroundingAdapter, scaffold_grounded_citations


@dataclass
class _StaticRouter:
    citations: list

    def generate(self, *, message: str, citations, locale: str) -> RoutingResult:
        del message, locale
        return RoutingResult(
            result=ProviderResult(
                provider="scaffold",
                answer="Scaffold response",
                citations=self.citations or citations,
                confidence="low",
            ),
            fallback_used=False,
            fallback_reason=None,
        )


@dataclass
class _FailingRouter:
    code: str = "provider_error"
    message: str = "provider failed"

    def generate(self, *, message: str, citations, locale: str) -> RoutingResult:
        del message, citations, locale
        raise ProviderError("openai", self.code, self.message)


def _audit_events(caplog: pytest.LogCaptureFixture) -> list[dict[str, object]]:
    return [record.audit_event for record in caplog.records if hasattr(record, "audit_event")]


def _assert_non_pii_audit_event(
    *,
    event: dict[str, object],
    raw_message: str,
    expected_event_type: str,
) -> None:
    assert event["event_type"] == expected_event_type
    assert "message" not in event
    assert "raw_message" not in event
    serialized = json.dumps(event, sort_keys=True)
    assert raw_message not in serialized


@pytest.mark.parametrize(
    "message",
    [
        "Please represent me and file my application",
        "Can you promise my citizenship approval?",
    ],
)
def test_chat_service_emits_policy_block_audit_event(
    caplog: pytest.LogCaptureFixture,
    message: str,
) -> None:
    service = ChatService(_StaticRouter(citations=[]))
    payload = ChatRequest(
        session_id="session-123456",
        message=message,
        locale="en-CA",
        mode="standard",
    )

    with caplog.at_level(logging.INFO, logger="immcad_api.audit"):
        response = service.handle_chat(payload, trace_id="trace-policy-001")

    assert response.answer == POLICY_REFUSAL_TEXT
    assert response.confidence == "low"
    assert response.disclaimer == DISCLAIMER_TEXT
    assert response.fallback_used.reason == "policy_block"
    events = _audit_events(caplog)
    assert events
    event = events[-1]
    assert event["trace_id"] == "trace-policy-001"
    assert event["locale"] == "en-CA"
    assert event["mode"] == "standard"
    assert event["message_length"] == len(payload.message)
    _assert_non_pii_audit_event(
        event=event,
        raw_message=payload.message,
        expected_event_type="policy_block",
    )
    for record in caplog.records:
        assert payload.message not in record.getMessage()


def test_chat_service_emits_provider_error_audit_event(caplog: pytest.LogCaptureFixture) -> None:
    service = ChatService(_FailingRouter(code="timeout", message="provider timed out"))
    payload = ChatRequest(
        session_id="session-123456",
        message="Summarize IRPA section 11.",
        locale="en-CA",
        mode="standard",
    )

    with caplog.at_level(logging.INFO, logger="immcad_api.audit"):
        response = service.handle_chat(payload, trace_id="trace-provider-001")

    assert response.answer.startswith("I do not have enough grounded legal context")
    assert response.citations == []
    assert response.confidence == "low"
    assert response.disclaimer == DISCLAIMER_TEXT
    assert response.fallback_used.used is True
    assert response.fallback_used.provider == "openai"
    assert response.fallback_used.reason == "provider_error"
    events = _audit_events(caplog)
    assert events
    event = events[-1]
    assert event["trace_id"] == "trace-provider-001"
    assert event["provider"] == "openai"
    assert event["provider_error_code"] == "timeout"
    assert event["locale"] == "en-CA"
    assert event["mode"] == "standard"
    assert event["message_length"] == len(payload.message)
    _assert_non_pii_audit_event(
        event=event,
        raw_message=payload.message,
        expected_event_type="provider_error",
    )
    for record in caplog.records:
        assert payload.message not in record.getMessage()


def test_chat_service_raises_provider_error_for_non_transient_failures() -> None:
    service = ChatService(
        _FailingRouter(
            code="provider_error",
            message="GEMINI_API_KEY not configured",
        )
    )
    payload = ChatRequest(
        session_id="session-123456",
        message="Summarize IRPA section 11.",
        locale="en-CA",
        mode="standard",
    )

    with pytest.raises(ProviderApiError):
        service.handle_chat(payload, trace_id="trace-provider-002")


def test_chat_service_returns_grounded_response_when_adapter_supplies_citations() -> None:
    service = ChatService(
        _StaticRouter(citations=[]),
        grounding_adapter=StaticGroundingAdapter(scaffold_grounded_citations()),
    )
    payload = ChatRequest(
        session_id="session-123456",
        message="Summarize IRPA section 11.",
        locale="en-CA",
        mode="standard",
    )

    response = service.handle_chat(payload, trace_id="trace-grounded-001")

    assert response.answer == "Scaffold response"
    assert len(response.citations) == 1
    assert response.citations[0].source_id == "IRPA"
    assert response.confidence == "medium"
    assert response.disclaimer == DISCLAIMER_TEXT
    assert response.fallback_used.used is False
    assert payload.message not in response.model_dump_json()


def test_chat_service_returns_safe_constrained_response_when_adapter_has_no_grounding() -> None:
    service = ChatService(_StaticRouter(citations=[]))
    payload = ChatRequest(
        session_id="session-123456",
        message="Summarize IRPA section 11.",
        locale="en-CA",
        mode="standard",
    )

    response = service.handle_chat(payload, trace_id="trace-constrained-001")

    assert response.answer.startswith("I do not have enough grounded legal context")
    assert response.citations == []
    assert response.confidence == "low"
    assert response.disclaimer == DISCLAIMER_TEXT
    assert response.fallback_used.used is False
    assert response.fallback_used.provider is None
    assert response.fallback_used.reason is None
    assert payload.message not in response.model_dump_json()


def test_chat_service_rejects_provider_citations_not_in_grounding_set() -> None:
    ungrounded_citation = Citation(
        source_id="UNTRUSTED",
        title="Untrusted Source",
        url="https://example.com/legal",
        pin="s. 1",
        snippet="Ungrounded snippet",
    )
    service = ChatService(
        _StaticRouter(citations=[ungrounded_citation]),
        grounding_adapter=StaticGroundingAdapter(scaffold_grounded_citations()),
    )
    payload = ChatRequest(
        session_id="session-123456",
        message="Summarize IRPA section 11.",
        locale="en-CA",
        mode="standard",
    )

    response = service.handle_chat(payload, trace_id="trace-grounding-reject-001")

    assert response.answer.startswith("I do not have enough grounded legal context")
    assert response.citations == []
    assert response.confidence == "low"
    assert response.disclaimer == DISCLAIMER_TEXT
    assert response.fallback_used.used is False
    assert payload.message not in response.model_dump_json()


def test_chat_service_logs_grounding_validation_failure_event(
    caplog: pytest.LogCaptureFixture,
) -> None:
    ungrounded_citation = Citation(
        source_id="UNTRUSTED",
        title="Untrusted Source",
        url="https://example.com/legal",
        pin="s. 1",
        snippet="Ungrounded snippet",
    )
    service = ChatService(
        _StaticRouter(citations=[ungrounded_citation]),
        grounding_adapter=StaticGroundingAdapter(scaffold_grounded_citations()),
    )
    payload = ChatRequest(
        session_id="session-123456",
        message="Summarize IRPA section 11.",
        locale="en-CA",
        mode="standard",
    )

    with caplog.at_level(logging.INFO, logger="immcad_api.audit"):
        response = service.handle_chat(payload, trace_id="trace-grounding-event-001")

    assert response.citations == []
    events = _audit_events(caplog)
    assert events
    event = events[-1]
    assert event["event_type"] == "grounding_validation_failed"
    assert event["trace_id"] == "trace-grounding-event-001"
    assert event["provider"] == "scaffold"
    assert event["provider_citation_count"] == 1
    assert event["candidate_citation_count"] == 1
    _assert_non_pii_audit_event(
        event=event,
        raw_message=payload.message,
        expected_event_type="grounding_validation_failed",
    )
    for record in caplog.records:
        assert payload.message not in record.getMessage()


def test_chat_service_rejects_citations_from_untrusted_domains(
    caplog: pytest.LogCaptureFixture,
) -> None:
    untrusted_citation = Citation(
        source_id="CUSTOM",
        title="Custom Source",
        url="https://evil.example/legal",
        pin="s. 11",
        snippet="Untrusted domain citation",
    )
    service = ChatService(
        _StaticRouter(citations=[untrusted_citation]),
        grounding_adapter=StaticGroundingAdapter([untrusted_citation]),
        trusted_citation_domains=("laws-lois.justice.gc.ca", "canlii.org"),
    )
    payload = ChatRequest(
        session_id="session-123456",
        message="Summarize section 11.",
        locale="en-CA",
        mode="standard",
    )

    with caplog.at_level(logging.INFO, logger="immcad_api.audit"):
        response = service.handle_chat(payload, trace_id="trace-untrusted-domain-001")

    assert response.citations == []
    assert response.confidence == "low"
    assert response.answer.startswith("I do not have enough grounded legal context")
    assert response.disclaimer == DISCLAIMER_TEXT
    assert response.fallback_used.used is False
    assert payload.message not in response.model_dump_json()
    events = _audit_events(caplog)
    assert events
    event = events[-1]
    assert event["event_type"] == "grounding_validation_failed"
    assert event["trace_id"] == "trace-untrusted-domain-001"
    assert event["provider"] == "scaffold"
    assert event["candidate_citation_count"] == 1
    assert event["provider_citation_count"] == 1
    assert event["rejected_citation_urls"] == ["https://evil.example/legal"]


def test_chat_service_accepts_citations_from_configured_trusted_domains() -> None:
    trusted_citation = Citation(
        source_id="CUSTOM",
        title="Trusted Source",
        url="https://trusted.example/legal",
        pin="s. 11",
        snippet="Trusted domain citation",
    )
    service = ChatService(
        _StaticRouter(citations=[trusted_citation]),
        grounding_adapter=StaticGroundingAdapter([trusted_citation]),
        trusted_citation_domains=("trusted.example",),
    )
    payload = ChatRequest(
        session_id="session-123456",
        message="Summarize section 11.",
        locale="en-CA",
        mode="standard",
    )

    response = service.handle_chat(payload, trace_id="trace-trusted-domain-001")

    assert response.answer == "Scaffold response"
    assert len(response.citations) == 1
    assert response.citations[0].url == "https://trusted.example/legal"
    assert response.confidence == "medium"
    assert response.disclaimer == DISCLAIMER_TEXT
    assert payload.message not in response.model_dump_json()
