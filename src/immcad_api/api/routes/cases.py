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
from immcad_api.telemetry import RequestMetrics


class ExportTooLargeError(Exception):
    pass


def _download_export_payload(
    *,
    document_url: str,
    max_download_bytes: int,
) -> tuple[bytes, str, str]:
    with httpx.stream(
        "GET",
        document_url,
        timeout=20.0,
        follow_redirects=True,
    ) as export_response:
        export_response.raise_for_status()
        content_length = export_response.headers.get("content-length")
        if content_length:
            try:
                if int(content_length) > max_download_bytes:
                    raise ExportTooLargeError(
                        "Case export payload exceeds configured maximum size"
                    )
            except ValueError:
                pass

        chunks: list[bytes] = []
        total_bytes = 0
        for chunk in export_response.iter_bytes():
            total_bytes += len(chunk)
            if total_bytes > max_download_bytes:
                raise ExportTooLargeError("Case export payload exceeds configured maximum size")
            chunks.append(chunk)

        payload_bytes = b"".join(chunks)
        media_type = export_response.headers.get("content-type", "application/octet-stream")
        final_url = str(export_response.url)
        return payload_bytes, media_type, final_url


def build_case_router(
    case_search_service: CaseSearchService,
    *,
    source_policy: SourcePolicy,
    source_registry: SourceRegistry,
    request_metrics: RequestMetrics | None = None,
    export_policy_gate_enabled: bool = False,
    export_max_download_bytes: int = 10 * 1024 * 1024,
) -> APIRouter:
    router = APIRouter(prefix="/api", tags=["cases"])

    def _record_export_metric(*, outcome: str, policy_reason: str | None = None) -> None:
        if request_metrics is None:
            return
        request_metrics.record_export_outcome(outcome=outcome, policy_reason=policy_reason)

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
            _record_export_metric(
                outcome="blocked",
                policy_reason="source_not_in_registry_for_export",
            )
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
                _record_export_metric(outcome="blocked", policy_reason=policy_reason)
                return _error_response(
                    status_code=403,
                    trace_id=trace_id,
                    code="POLICY_BLOCKED",
                    message=f"Case export blocked by source policy ({policy_reason})",
                    policy_reason=policy_reason,
                )

        if not _is_url_allowed_for_source(str(payload.document_url), str(source_entry.url)):
            _record_export_metric(
                outcome="blocked",
                policy_reason="export_url_not_allowed_for_source",
            )
            return _error_response(
                status_code=422,
                trace_id=trace_id,
                code="VALIDATION_ERROR",
                message="Case export URL host does not match the configured source host",
                policy_reason="export_url_not_allowed_for_source",
            )

        try:
            payload_bytes, media_type, final_url = _download_export_payload(
                document_url=str(payload.document_url),
                max_download_bytes=export_max_download_bytes,
            )
        except ExportTooLargeError as exc:
            _record_export_metric(
                outcome="too_large",
                policy_reason="source_export_payload_too_large",
            )
            return _error_response(
                status_code=413,
                trace_id=trace_id,
                code="VALIDATION_ERROR",
                message=str(exc),
                policy_reason="source_export_payload_too_large",
            )
        except httpx.HTTPError as exc:
            _record_export_metric(
                outcome="fetch_failed",
                policy_reason="source_export_fetch_failed",
            )
            return _error_response(
                status_code=503,
                trace_id=trace_id,
                code="SOURCE_UNAVAILABLE",
                message=f"Case export download failed: {exc}",
                policy_reason="source_export_fetch_failed",
            )

        if not _is_url_allowed_for_source(final_url, str(source_entry.url)):
            _record_export_metric(
                outcome="blocked",
                policy_reason="export_redirect_url_not_allowed_for_source",
            )
            return _error_response(
                status_code=422,
                trace_id=trace_id,
                code="VALIDATION_ERROR",
                message="Case export redirected to an untrusted host for the configured source",
                policy_reason="export_redirect_url_not_allowed_for_source",
            )

        _record_export_metric(outcome="allowed", policy_reason=policy_reason)
        filename = _safe_download_filename(
            source_id=payload.source_id,
            case_id=payload.case_id,
            fmt=payload.format,
        )
        return Response(
            content=payload_bytes,
            media_type=media_type,
            headers={
                "x-trace-id": trace_id,
                "x-export-policy-reason": policy_reason,
                "content-disposition": f'attachment; filename="{filename}"',
            },
        )

    return router
