from __future__ import annotations

from fastapi import APIRouter, Request, Response

from immcad_api.schemas import CaseSearchRequest, CaseSearchResponse
from immcad_api.services import CaseSearchService


def build_case_router(case_search_service: CaseSearchService) -> APIRouter:
    router = APIRouter(prefix="/api", tags=["cases"])

    @router.post("/search/cases", response_model=CaseSearchResponse)
    def search_cases(payload: CaseSearchRequest, request: Request, response: Response) -> CaseSearchResponse:
        trace_id = getattr(request.state, "trace_id", "")
        response.headers["x-trace-id"] = trace_id
        return case_search_service.search(payload)

    return router
