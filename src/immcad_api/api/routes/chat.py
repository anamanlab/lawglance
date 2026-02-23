from __future__ import annotations

from fastapi import APIRouter, Request, Response

from immcad_api.schemas import ChatRequest, ChatResponse
from immcad_api.services import ChatService


def build_chat_router(chat_service: ChatService) -> APIRouter:
    router = APIRouter(prefix="/api", tags=["chat"])

    @router.post("/chat", response_model=ChatResponse)
    def chat(payload: ChatRequest, request: Request, response: Response) -> ChatResponse:
        trace_id = getattr(request.state, "trace_id", "")
        response.headers["x-trace-id"] = trace_id
        return chat_service.handle_chat(payload, trace_id=trace_id)

    return router
