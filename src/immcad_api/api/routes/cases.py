from __future__ import annotations

import logging
import re
from urllib.parse import urlparse, urlunparse

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
    """Raised when an export payload exceeds configured bounds."""


LOGGER = logging.getLogger(__name__)


def _download_export_payload(
    *,
    request_url: str,
    max_download_bytes: int,
) -> tuple[bytes, str, str]:
    with httpx.stream(
        "GET",
        request_url,
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
                raise ExportTooLargeError(
                    "Case export payload exceeds configured maximum size"
                )
            chunks.append(chunk)

        payload_bytes = b"".join(chunks)
        media_type = export_response.headers.get(
            "content-type", "application/octet-stream"
        )
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

    def _record_export_metric(
        *, outcome: str, policy_reason: str | None = None
    ) -> None:
        if request_metrics is None:
            return
        request_metrics.record_export_outcome(
            outcome=outcome, policy_reason=policy_reason
        )

    def _record_export_audit(
        *,
        request: Request,
        payload: CaseExportRequest,
        outcome: str,
        policy_reason: str | None = None,
        document_url: str | None = None,
    ) -> None:
        trace_id = getattr(request.state, "trace_id", "")
        raw_client_id = getattr(request.state, "client_id", None)
        client_id = str(raw_client_id).strip() if raw_client_id else None
        target_url = document_url or str(payload.document_url)
        document_host = (urlparse(target_url).hostname or "").lower() or None
        event_payload = {
            "trace_id": trace_id,
            "client_id": client_id,
            "source_id": payload.source_id,
            "case_id": payload.case_id,
            "document_host": document_host,
            "user_approved": payload.user_approved,
            "outcome": outcome,
            "policy_reason": policy_reason,
        }
        LOGGER.info("case_export_audit_event %s", event_payload)
        if request_metrics is None:
            return
        request_metrics.record_export_audit_event(
            trace_id=trace_id,
            client_id=client_id,
            source_id=payload.source_id,
            case_id=payload.case_id,
            document_host=document_host,
            user_approved=payload.user_approved,
            outcome=outcome,
            policy_reason=policy_reason,
        )

    def _record_export_event(
        *,
        request: Request,
        payload: CaseExportRequest,
        outcome: str,
        policy_reason: str | None = None,
        document_url: str | None = None,
    ) -> None:
        _record_export_metric(outcome=outcome, policy_reason=policy_reason)
        _record_export_audit(
            request=request,
            payload=payload,
            outcome=outcome,
            policy_reason=policy_reason,
            document_url=document_url,
        )

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

    def _allowed_hosts_for_source(source_url: str) -> set[str]:
        source_host = (urlparse(source_url).hostname or "").lower()
        if not source_host:
            return set()
        return {source_host}

    def _is_url_allowed_for_source(document_url: str, allowed_hosts: set[str]) -> bool:
        document_host = (urlparse(document_url).hostname or "").lower()
        if not document_host or not allowed_hosts:
            return False
        return document_host in allowed_hosts

    def _safe_download_filename(*, source_id: str, case_id: str, fmt: str) -> str:
        safe_source = re.sub(r"[^A-Za-z0-9_.-]+", "-", source_id).strip("-") or "source"
        safe_case = re.sub(r"[^A-Za-z0-9_.-]+", "-", case_id).strip("-") or "case"
        return f"{safe_source}-{safe_case}.{fmt}"

    def _build_source_scoped_request_url(*, document_url: str, source_url: str) -> str:
        document_parts = urlparse(document_url)
        source_parts = urlparse(source_url)
        scheme = source_parts.scheme or document_parts.scheme or "https"
        netloc = source_parts.netloc
        return urlunparse(
            (
                scheme,
                netloc,
                document_parts.path,
                document_parts.params,
                document_parts.query,
                document_parts.fragment,
            )
        )

    def _is_pdf_payload(*, payload_bytes: bytes, media_type: str) -> bool:
        normalized_media_type = media_type.split(";", 1)[0].strip().lower()
        if payload_bytes.startswith(b"%PDF-"):
            return True
        return normalized_media_type == "application/pdf"

    @router.post("/search/cases", response_model=CaseSearchResponse)
    def search_cases(
        payload: CaseSearchRequest, request: Request, response: Response
    ) -> CaseSearchResponse:
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
            _record_export_event(
                request=request,
                payload=payload,
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

        allowed_hosts = _allowed_hosts_for_source(str(source_entry.url))
        if not payload.user_approved:
            _record_export_event(
                request=request,
                payload=payload,
                outcome="blocked",
                policy_reason="source_export_user_approval_required",
            )
            return _error_response(
                status_code=403,
                trace_id=trace_id,
                code="POLICY_BLOCKED",
                message="Case export requires explicit user approval before download",
                policy_reason="source_export_user_approval_required",
            )

        policy_reason = "source_export_allowed_gate_disabled"
        if export_policy_gate_enabled:
            export_allowed, policy_reason = is_source_export_allowed(
                payload.source_id,
                source_policy=source_policy,
            )
            if not export_allowed:
                _record_export_event(
                    request=request,
                    payload=payload,
                    outcome="blocked",
                    policy_reason=policy_reason,
                )
                return _error_response(
                    status_code=403,
                    trace_id=trace_id,
                    code="POLICY_BLOCKED",
                    message=f"Case export blocked by source policy ({policy_reason})",
                    policy_reason=policy_reason,
                )

        if not _is_url_allowed_for_source(str(payload.document_url), allowed_hosts):
            _record_export_event(
                request=request,
                payload=payload,
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

        request_url = _build_source_scoped_request_url(
            document_url=str(payload.document_url),
            source_url=str(source_entry.url),
        )
        try:
            payload_bytes, media_type, final_url = _download_export_payload(
                request_url=request_url,
                max_download_bytes=export_max_download_bytes,
            )
        except ExportTooLargeError as exc:
            _record_export_event(
                request=request,
                payload=payload,
                outcome="too_large",
                policy_reason="source_export_payload_too_large",
                document_url=request_url,
            )
            return _error_response(
                status_code=413,
                trace_id=trace_id,
                code="VALIDATION_ERROR",
                message=str(exc),
                policy_reason="source_export_payload_too_large",
            )
        except httpx.HTTPError as exc:
            _record_export_event(
                request=request,
                payload=payload,
                outcome="fetch_failed",
                policy_reason="source_export_fetch_failed",
                document_url=request_url,
            )
            return _error_response(
                status_code=503,
                trace_id=trace_id,
                code="SOURCE_UNAVAILABLE",
                message=f"Case export download failed: {exc}",
                policy_reason="source_export_fetch_failed",
            )

        if not _is_url_allowed_for_source(final_url, allowed_hosts):
            _record_export_event(
                request=request,
                payload=payload,
                outcome="blocked",
                policy_reason="export_redirect_url_not_allowed_for_source",
                document_url=final_url,
            )
            return _error_response(
                status_code=422,
                trace_id=trace_id,
                code="VALIDATION_ERROR",
                message="Case export redirected to a URL host that does not match the configured source host",
                policy_reason="export_redirect_url_not_allowed_for_source",
            )

        if payload.format == "pdf" and not _is_pdf_payload(
            payload_bytes=payload_bytes,
            media_type=media_type,
        ):
            _record_export_event(
                request=request,
                payload=payload,
                outcome="blocked",
                policy_reason="source_export_non_pdf_payload",
                document_url=final_url,
            )
            return _error_response(
                status_code=422,
                trace_id=trace_id,
                code="VALIDATION_ERROR",
                message="Case export response did not contain a valid PDF payload",
                policy_reason="source_export_non_pdf_payload",
            )

        _record_export_event(
            request=request,
            payload=payload,
            outcome="allowed",
            policy_reason=policy_reason,
            document_url=final_url,
        )
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


def build_case_router_disabled(
    *,
    policy_reason: str = "case_search_disabled",
) -> APIRouter:
    router = APIRouter(prefix="/api", tags=["cases"])

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

    @router.post("/search/cases", response_model=None)
    def search_cases_disabled(request: Request) -> JSONResponse:
        trace_id = getattr(request.state, "trace_id", "")
        return _error_response(
            status_code=503,
            trace_id=trace_id,
            code="SOURCE_UNAVAILABLE",
            message="Case-law search is disabled in this deployment.",
        )

    @router.post("/export/cases", response_model=None)
    def export_cases_disabled(request: Request) -> JSONResponse:
        trace_id = getattr(request.state, "trace_id", "")
        return _error_response(
            status_code=503,
            trace_id=trace_id,
            code="SOURCE_UNAVAILABLE",
            message="Case export is disabled in this deployment.",
        )

    return router
