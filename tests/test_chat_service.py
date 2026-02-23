from __future__ import annotations

from dataclasses import dataclass
import logging

import pytest

from immcad_api.errors import ProviderApiError
from immcad_api.providers import ProviderError
from immcad_api.providers.base import ProviderResult
from immcad_api.providers.router import RoutingResult
from immcad_api.schemas import ChatRequest
from immcad_api.services.chat_service import ChatService


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


def test_chat_service_emits_policy_block_audit_event(caplog: pytest.LogCaptureFixture) -> None:
    service = ChatService(_StaticRouter(citations=[]))
    payload = ChatRequest(
        session_id="session-123456",
        message="Please represent me and file my application",
        locale="en-CA",
        mode="standard",
    )

    with caplog.at_level(logging.INFO, logger="immcad_api.audit"):
        response = service.handle_chat(payload, trace_id="trace-policy-001")

    assert response.fallback_used.reason == "policy_block"
    events = _audit_events(caplog)
    assert events
    event = events[-1]
    assert event["trace_id"] == "trace-policy-001"
    assert event["event_type"] == "policy_block"
    assert event["locale"] == "en-CA"
    assert event["mode"] == "standard"
    assert event["message_length"] == len(payload.message)
    assert "message" not in event


def test_chat_service_emits_provider_error_audit_event(caplog: pytest.LogCaptureFixture) -> None:
    service = ChatService(_FailingRouter(code="timeout", message="provider timed out"))
    payload = ChatRequest(
        session_id="session-123456",
        message="Summarize IRPA section 11.",
        locale="en-CA",
        mode="standard",
    )

    with caplog.at_level(logging.INFO, logger="immcad_api.audit"):
        with pytest.raises(ProviderApiError):
            service.handle_chat(payload, trace_id="trace-provider-001")

    events = _audit_events(caplog)
    assert events
    event = events[-1]
    assert event["trace_id"] == "trace-provider-001"
    assert event["event_type"] == "provider_error"
    assert event["provider"] == "openai"
    assert event["provider_error_code"] == "timeout"
    assert event["locale"] == "en-CA"
    assert event["mode"] == "standard"
    assert event["message_length"] == len(payload.message)
    assert "message" not in event
