from __future__ import annotations

from fastapi.concurrency import run_in_threadpool
from fastapi import APIRouter, Request, Response

from immcad_api.policy.compliance import SAFE_CONSTRAINED_RESPONSE
from immcad_api.schemas import ChatRequest, ChatResponse
from immcad_api.services import ChatService
from immcad_api.services.chat_service import is_friendly_greeting_answer
from immcad_api.telemetry import RequestMetrics


def build_chat_router(
    chat_service: ChatService,
    *,
    request_metrics: RequestMetrics | None = None,
) -> APIRouter:
    router = APIRouter(prefix="/api", tags=["chat"])

    @router.post("/chat", response_model=ChatResponse)
    async def chat(
        payload: ChatRequest, request: Request, response: Response
    ) -> ChatResponse:
        trace_id = getattr(request.state, "trace_id", "")
        response.headers["x-trace-id"] = trace_id
        try:
            chat_response = await run_in_threadpool(
                chat_service.handle_chat,
                payload,
                trace_id=trace_id,
            )
        except RuntimeError:
            # Python Workers can run in threadless runtimes where threadpool execution
            # is unavailable; fallback to direct invocation for compatibility.
            chat_response = chat_service.handle_chat(
                payload,
                trace_id=trace_id,
            )
        if request_metrics:
            constrained_used = chat_response.answer == SAFE_CONSTRAINED_RESPONSE
            friendly_used = is_friendly_greeting_answer(chat_response.answer)
            request_metrics.record_chat_outcome(
                fallback_used=chat_response.fallback_used.used,
                refusal_used=chat_response.fallback_used.reason == "policy_block",
                friendly_used=friendly_used,
                constrained_used=constrained_used,
            )
        return chat_response

    return router
