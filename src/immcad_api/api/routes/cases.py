from __future__ import annotations

from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse, RedirectResponse

from immcad_api.policy.source_policy import SourcePolicy, is_source_export_allowed
from immcad_api.sources.source_registry import SourceRegistry
from immcad_api.schemas import CaseSearchRequest, CaseSearchResponse, ErrorEnvelope, SourceExportResponse
from immcad_api.services import CaseSearchService


def build_case_router(
    case_search_service: CaseSearchService,
    *,
    source_policy: SourcePolicy,
    source_registry: SourceRegistry,
) -> APIRouter:
    router = APIRouter(prefix="/api", tags=["cases"])

    @router.post("/search/cases", response_model=CaseSearchResponse)
    def search_cases(payload: CaseSearchRequest, request: Request, response: Response) -> CaseSearchResponse:
        trace_id = getattr(request.state, "trace_id", "")
        response.headers["x-trace-id"] = trace_id
        return case_search_service.search(payload)

    @router.get(
        "/sources/{source_id}/export",
        response_model=SourceExportResponse,
        responses={
            307: {"description": "Redirect to the authoritative source URL"},
            403: {"model": ErrorEnvelope},
            404: {"model": ErrorEnvelope},
        },
    )
    def export_source(
        source_id: str,
        request: Request,
        response: Response,
        redirect: bool = False,
    ) -> SourceExportResponse | JSONResponse | RedirectResponse:
        trace_id = getattr(request.state, "trace_id", "")
        response.headers["x-trace-id"] = trace_id
        allowed, policy_reason = is_source_export_allowed(source_id, source_policy=source_policy)
        if not allowed:
            payload = ErrorEnvelope(
                error={
                    "code": "POLICY_BLOCKED",
                    "message": f"Full-text export is not allowed for source '{source_id}'",
                    "trace_id": trace_id,
                }
            )
            return JSONResponse(
                status_code=403,
                content=payload.model_dump(),
                headers={"x-trace-id": trace_id},
            )

        source_entry = source_registry.get_source(source_id)
        if source_entry is None:
            payload = ErrorEnvelope(
                error={
                    "code": "SOURCE_UNAVAILABLE",
                    "message": f"Source registry metadata unavailable for source '{source_id}'",
                    "trace_id": trace_id,
                }
            )
            return JSONResponse(
                status_code=404,
                content=payload.model_dump(),
                headers={"x-trace-id": trace_id},
            )

        if redirect:
            return RedirectResponse(url=str(source_entry.url), status_code=307)

        return SourceExportResponse(
            source_id=source_id,
            export_allowed=True,
            policy_reason=policy_reason,
            source_type=source_entry.source_type,
            instrument=source_entry.instrument,
            download_url=str(source_entry.url),
            registry_version=source_registry.version,
            jurisdiction=source_registry.jurisdiction.lower(),
            status="ready",
            message="Use download_url to retrieve the source-authoritative content.",
        )

    return router
