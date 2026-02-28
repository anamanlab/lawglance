from __future__ import annotations

from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse

from immcad_api.policy import SourcePolicy
from immcad_api.schemas import ErrorEnvelope, SourceTransparencyResponse
from immcad_api.services.source_transparency_service import (
    build_source_transparency_payload,
)
from immcad_api.sources import SourceRegistry


def build_source_transparency_router(
    *,
    source_registry: SourceRegistry | None,
    source_policy: SourcePolicy | None,
    checkpoint_state_path: str,
) -> APIRouter:
    router = APIRouter(prefix="/api", tags=["source-transparency"])

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

    @router.get(
        "/sources/transparency",
        response_model=SourceTransparencyResponse,
        responses={
            503: {
                "model": ErrorEnvelope,
                "description": "Source transparency assets unavailable",
            }
        },
    )
    async def source_transparency(
        request: Request,
        response: Response,
    ) -> SourceTransparencyResponse | JSONResponse:
        trace_id = getattr(request.state, "trace_id", "")
        response.headers["x-trace-id"] = trace_id

        if source_registry is None or source_policy is None:
            return _error_response(
                status_code=503,
                trace_id=trace_id,
                code="SOURCE_UNAVAILABLE",
                message=(
                    "Source transparency is unavailable because source registry/policy assets "
                    "could not be loaded."
                ),
                policy_reason="source_transparency_assets_missing",
            )

        return build_source_transparency_payload(
            source_registry=source_registry,
            source_policy=source_policy,
            checkpoint_state_path=checkpoint_state_path,
        )

    return router
