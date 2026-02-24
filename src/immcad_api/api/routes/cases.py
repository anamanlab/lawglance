from __future__ import annotations

from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse

from immcad_api.policy import SourcePolicy, is_source_export_allowed
from immcad_api.schemas import (
    CaseExportRequest,
    CaseExportResponse,
    CaseSearchRequest,
    CaseSearchResponse,
    ErrorEnvelope,
)
from immcad_api.services import CaseSearchService


def build_case_router(
    case_search_service: CaseSearchService,
    *,
    source_policy: SourcePolicy,
) -> APIRouter:
    router = APIRouter(prefix="/api", tags=["cases"])

    @router.post("/search/cases", response_model=CaseSearchResponse)
    def search_cases(payload: CaseSearchRequest, request: Request, response: Response) -> CaseSearchResponse:
        trace_id = getattr(request.state, "trace_id", "")
        response.headers["x-trace-id"] = trace_id
        return case_search_service.search(payload)

    @router.post("/export/cases", response_model=CaseExportResponse)
    def export_cases(
        payload: CaseExportRequest,
        request: Request,
        response: Response,
    ) -> CaseExportResponse | JSONResponse:
        trace_id = getattr(request.state, "trace_id", "")
        export_allowed, policy_reason = is_source_export_allowed(
            payload.source_id,
            source_policy=source_policy,
        )
        if not export_allowed:
            error = ErrorEnvelope(
                error={
                    "code": "POLICY_BLOCKED",
                    "message": f"Case export blocked by source policy ({policy_reason})",
                    "trace_id": trace_id,
                    "policy_reason": policy_reason,
                }
            )
            return JSONResponse(
                status_code=422,
                content=error.model_dump(),
                headers={"x-trace-id": trace_id},
            )

        response.headers["x-trace-id"] = trace_id
        return CaseExportResponse(
            source_id=payload.source_id,
            case_id=payload.case_id,
            format=payload.format,
            export_allowed=True,
            policy_reason=policy_reason,
        )

    return router
