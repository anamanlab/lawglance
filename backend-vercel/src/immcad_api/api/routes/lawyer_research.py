from __future__ import annotations

from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse

from immcad_api.api.routes.case_query_validation import is_specific_case_query
from immcad_api.errors import ApiError, SourceUnavailableError
from immcad_api.schemas import (
    ErrorEnvelope,
    LawyerCaseResearchRequest,
    LawyerCaseResearchResponse,
)
from immcad_api.services import LawyerCaseResearchService
from immcad_api.telemetry import RequestMetrics


def build_lawyer_research_router(
    lawyer_case_research_service: LawyerCaseResearchService,
    *,
    request_metrics: RequestMetrics | None = None,
) -> APIRouter:
    router = APIRouter(prefix="/api", tags=["lawyer-research"])

    def _error_response(
        *,
        status_code: int,
        trace_id: str,
        code: str,
        message: str,
        policy_reason: str | None = None,
    ) -> JSONResponse:
        error = ErrorEnvelope(
            error={
                "code": code,
                "message": message,
                "trace_id": trace_id,
                "policy_reason": policy_reason,
            }
        )
        return JSONResponse(
            status_code=status_code,
            content=error.model_dump(mode="json"),
            headers={"x-trace-id": trace_id},
        )

    @router.post(
        "/research/lawyer-cases",
        response_model=LawyerCaseResearchResponse,
    )
    async def research_lawyer_cases(
        payload: LawyerCaseResearchRequest,
        request: Request,
        response: Response,
    ) -> LawyerCaseResearchResponse | JSONResponse:
        trace_id = getattr(request.state, "trace_id", "")
        response.headers["x-trace-id"] = trace_id
        if not is_specific_case_query(payload.matter_summary):
            return _error_response(
                status_code=422,
                trace_id=trace_id,
                code="VALIDATION_ERROR",
                message=(
                    "Case-law query is too broad. Please include specific terms such as "
                    "program, issue, court, or citation."
                ),
                policy_reason="case_search_query_too_broad",
            )
        try:
            research_response = lawyer_case_research_service.research(payload)
            if request_metrics is not None:
                pdf_available_count = sum(
                    1 for case in research_response.cases if case.pdf_status == "available"
                )
                pdf_unavailable_count = len(research_response.cases) - pdf_available_count
                request_metrics.record_lawyer_research_outcome(
                    case_count=len(research_response.cases),
                    pdf_available_count=pdf_available_count,
                    pdf_unavailable_count=pdf_unavailable_count,
                    source_status=research_response.source_status,
                )
            return research_response
        except SourceUnavailableError as exc:
            if request_metrics is not None:
                request_metrics.record_lawyer_research_outcome(
                    case_count=0,
                    pdf_available_count=0,
                    pdf_unavailable_count=0,
                    source_status={"official": "unavailable", "canlii": "unavailable"},
                )
            return _error_response(
                status_code=503,
                trace_id=trace_id,
                code="SOURCE_UNAVAILABLE",
                message=str(exc),
            )
        except ApiError as exc:
            return _error_response(
                status_code=exc.status_code,
                trace_id=trace_id,
                code=exc.code,
                message=exc.message,
            )

    return router


def build_lawyer_research_router_disabled(
    *,
    policy_reason: str = "case_search_disabled",
) -> APIRouter:
    router = APIRouter(prefix="/api", tags=["lawyer-research"])

    def _error_response(
        *,
        status_code: int,
        trace_id: str,
        code: str,
        message: str,
    ) -> JSONResponse:
        error = ErrorEnvelope(
            error={
                "code": code,
                "message": message,
                "trace_id": trace_id,
                "policy_reason": policy_reason,
            }
        )
        return JSONResponse(
            status_code=status_code,
            content=error.model_dump(mode="json"),
            headers={"x-trace-id": trace_id},
        )

    @router.post("/research/lawyer-cases", response_model=None)
    async def lawyer_case_research_disabled(request: Request) -> JSONResponse:
        trace_id = getattr(request.state, "trace_id", "")
        return _error_response(
            status_code=503,
            trace_id=trace_id,
            code="SOURCE_UNAVAILABLE",
            message="Lawyer case research is disabled in this deployment.",
        )

    return router
