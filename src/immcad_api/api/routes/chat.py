from __future__ import annotations

from fastapi import APIRouter, Request, Response

from immcad_api.schemas import ChatRequest, ChatResponse
from immcad_api.services import ChatService
from immcad_api.telemetry import RequestMetrics


def build_chat_router(
    chat_service: ChatService,
    *,
    request_metrics: RequestMetrics | None = None,
) -> APIRouter:
    router = APIRouter(prefix="/api", tags=["chat"])

    @router.post("/chat", response_model=ChatResponse)
    def chat(payload: ChatRequest, request: Request, response: Response) -> ChatResponse:
        trace_id = getattr(request.state, "trace_id", "")
        response.headers["x-trace-id"] = trace_id
        chat_response = chat_service.handle_chat(payload, trace_id=trace_id)
        if request_metrics:
            request_metrics.record_chat_outcome(
                fallback_used=chat_response.fallback_used.used,
                refusal_used=chat_response.fallback_used.reason == "policy_block",
            )
        return chat_response

    return router
