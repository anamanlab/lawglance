from __future__ import annotations

import re
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse

from immcad_api.policy import SourcePolicy, is_source_export_allowed
from immcad_api.schemas import (
    CaseExportRequest,
    CaseSearchRequest,
    CaseSearchResponse,
    ErrorEnvelope,
)
from immcad_api.services import CaseSearchService
from immcad_api.sources import SourceRegistry


def build_case_router(
    case_search_service: CaseSearchService,
    *,
    source_policy: SourcePolicy,
    source_registry: SourceRegistry,
    export_policy_gate_enabled: bool = False,
) -> APIRouter:
    router = APIRouter(prefix="/api", tags=["cases"])

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

    def _is_url_allowed_for_source(document_url: str, source_url: str) -> bool:
        document_host = (urlparse(document_url).hostname or "").lower()
        source_host = (urlparse(source_url).hostname or "").lower()
        if not document_host or not source_host:
            return False
        return document_host == source_host or document_host.endswith(f".{source_host}")

    def _safe_download_filename(*, source_id: str, case_id: str, fmt: str) -> str:
        safe_source = re.sub(r"[^A-Za-z0-9_.-]+", "-", source_id).strip("-") or "source"
        safe_case = re.sub(r"[^A-Za-z0-9_.-]+", "-", case_id).strip("-") or "case"
        return f"{safe_source}-{safe_case}.{fmt}"

    @router.post("/search/cases", response_model=CaseSearchResponse)
    def search_cases(payload: CaseSearchRequest, request: Request, response: Response) -> CaseSearchResponse:
        trace_id = getattr(request.state, "trace_id", "")
        response.headers["x-trace-id"] = trace_id
        return case_search_service.search(payload)

    @router.post("/export/cases", response_model=None)
    def export_cases(
        payload: CaseExportRequest,
        request: Request,
    ) -> Response:
        trace_id = getattr(request.state, "trace_id", "")
        source_entry = source_registry.get_source(payload.source_id)
        if source_entry is None:
            return _error_response(
                status_code=403,
                trace_id=trace_id,
                code="POLICY_BLOCKED",
                message="Case export blocked by source policy (source_not_in_registry_for_export)",
                policy_reason="source_not_in_registry_for_export",
            )

        policy_reason = "source_export_allowed_gate_disabled"
        if export_policy_gate_enabled:
            export_allowed, policy_reason = is_source_export_allowed(
                payload.source_id,
                source_policy=source_policy,
            )
            if not export_allowed:
                return _error_response(
                    status_code=403,
                    trace_id=trace_id,
                    code="POLICY_BLOCKED",
                    message=f"Case export blocked by source policy ({policy_reason})",
                    policy_reason=policy_reason,
                )

        if not _is_url_allowed_for_source(str(payload.document_url), str(source_entry.url)):
            return _error_response(
                status_code=422,
                trace_id=trace_id,
                code="VALIDATION_ERROR",
                message="Case export URL host does not match the configured source host",
                policy_reason="export_url_not_allowed_for_source",
            )

        try:
            export_response = httpx.get(
                str(payload.document_url),
                timeout=20.0,
                follow_redirects=True,
            )
            export_response.raise_for_status()
        except httpx.HTTPError as exc:
            return _error_response(
                status_code=503,
                trace_id=trace_id,
                code="SOURCE_UNAVAILABLE",
                message=f"Case export download failed: {exc}",
                policy_reason="source_export_fetch_failed",
            )

        if not _is_url_allowed_for_source(str(export_response.url), str(source_entry.url)):
            return _error_response(
                status_code=422,
                trace_id=trace_id,
                code="VALIDATION_ERROR",
                message="Case export redirected to a URL host that does not match the configured source host",
                policy_reason="export_redirect_url_not_allowed_for_source",
            )

        media_type = export_response.headers.get("content-type", "application/octet-stream")
        filename = _safe_download_filename(
            source_id=payload.source_id,
            case_id=payload.case_id,
            fmt=payload.format,
        )
        return Response(
            content=export_response.content,
            media_type=media_type,
            headers={
                "x-trace-id": trace_id,
                "x-export-policy-reason": policy_reason,
                "content-disposition": f'attachment; filename="{filename}"',
            },
        )

    return router
