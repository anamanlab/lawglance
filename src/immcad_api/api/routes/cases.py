from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import re
import time
from urllib.parse import urljoin, urlparse, urlunparse

import httpx
from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

from immcad_api.api.routes._threadpool import (
    is_threadpool_unavailable_runtime_error,
)
from immcad_api.api.routes.case_query_validation import assess_case_query
from immcad_api.errors import ApiError
from immcad_api.policy import SourcePolicy, is_source_export_allowed
from immcad_api.schemas import (
    CaseExportApprovalRequest,
    CaseExportApprovalResponse,
    CaseExportRequest,
    CaseSearchRequest,
    CaseSearchResult,
    CaseSearchResponse,
    ErrorEnvelope,
)
from immcad_api.services import CaseSearchService
from immcad_api.services.case_document_resolver import (
    allowed_hosts_for_source,
    is_url_allowed_for_source,
)
from immcad_api.sources import SourceRegistry
from immcad_api.telemetry import RequestMetrics


class ExportTooLargeError(Exception):
    """Raised when an export payload exceeds configured bounds."""


class ExportRedirectHostError(Exception):
    """Raised when an export redirect points to an untrusted host."""

    def __init__(self, redirect_url: str) -> None:
        super().__init__("Case export redirect URL host does not match source host")
        self.redirect_url = redirect_url


LOGGER = logging.getLogger(__name__)
_APPROVAL_TOKEN_VERSION = 1
_REDIRECT_STATUS_CODES = {301, 302, 303, 307, 308}


def _download_export_payload(
    *,
    request_url: str,
    max_download_bytes: int,
    allowed_hosts: set[str],
    max_redirects: int = 5,
) -> tuple[bytes, str, str]:
    current_url = request_url
    redirect_count = 0
    while True:
        with httpx.stream(
            "GET",
            current_url,
            timeout=20.0,
            follow_redirects=False,
        ) as export_response:
            if export_response.status_code in _REDIRECT_STATUS_CODES:
                redirect_location = export_response.headers.get("location")
                if not redirect_location:
                    raise httpx.HTTPError(
                        "Case export redirect response missing location header"
                    )
                redirected_url = urljoin(str(export_response.url), redirect_location)
                if not is_url_allowed_for_source(redirected_url, allowed_hosts):
                    raise ExportRedirectHostError(redirected_url)
                redirect_count += 1
                if redirect_count > max_redirects:
                    raise httpx.HTTPError("Case export exceeded maximum redirect count")
                current_url = redirected_url
                continue

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


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(f"{value}{padding}")


def _normalize_token_url(raw_url: str) -> str:
    parsed = urlparse(raw_url.strip())
    return urlunparse(
        (
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            parsed.path,
            parsed.params,
            parsed.query,
            "",
        )
    )


def _issue_export_approval_token(
    *,
    secret: str,
    source_id: str,
    case_id: str,
    document_url: str,
    issued_at_epoch: int,
) -> str:
    payload = {
        "v": _APPROVAL_TOKEN_VERSION,
        "sid": source_id,
        "cid": case_id,
        "url": _normalize_token_url(document_url),
        "iat": issued_at_epoch,
    }
    payload_bytes = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    signature = hmac.new(
        secret.encode("utf-8"),
        payload_bytes,
        hashlib.sha256,
    ).digest()
    return f"{_b64url_encode(payload_bytes)}.{_b64url_encode(signature)}"


def _has_valid_export_approval_token(
    *,
    token: str,
    secret: str,
    source_id: str,
    case_id: str,
    document_url: str,
    ttl_seconds: int,
    now_epoch: int,
) -> bool:
    parts = token.split(".", 1)
    if len(parts) != 2:
        return False
    payload_part, signature_part = parts
    try:
        payload_bytes = _b64url_decode(payload_part)
        received_signature = _b64url_decode(signature_part)
    except Exception:
        return False

    expected_signature = hmac.new(
        secret.encode("utf-8"),
        payload_bytes,
        hashlib.sha256,
    ).digest()
    if not hmac.compare_digest(expected_signature, received_signature):
        return False

    try:
        payload = json.loads(payload_bytes.decode("utf-8"))
    except Exception:
        return False
    if not isinstance(payload, dict):
        return False

    version = payload.get("v")
    token_source_id = payload.get("sid")
    token_case_id = payload.get("cid")
    token_url = payload.get("url")
    issued_at = payload.get("iat")
    if (
        version != _APPROVAL_TOKEN_VERSION
        or not isinstance(token_source_id, str)
        or not isinstance(token_case_id, str)
        or not isinstance(token_url, str)
        or not isinstance(issued_at, int)
    ):
        return False

    if token_source_id != source_id or token_case_id != case_id:
        return False
    if token_url != _normalize_token_url(document_url):
        return False
    if issued_at < 0 or now_epoch < issued_at:
        return False
    if now_epoch - issued_at > ttl_seconds:
        return False

    return True


def build_case_router(
    case_search_service: CaseSearchService,
    *,
    source_policy: SourcePolicy,
    source_registry: SourceRegistry,
    request_metrics: RequestMetrics | None = None,
    export_policy_gate_enabled: bool = False,
    export_max_download_bytes: int = 10 * 1024 * 1024,
    case_search_official_only_results: bool = False,
    export_approval_token_secret: str | None = None,
    export_approval_token_ttl_seconds: int = 600,
    require_signed_export_approval: bool = False,
) -> APIRouter:
    if export_approval_token_ttl_seconds < 60:
        raise ValueError("export_approval_token_ttl_seconds must be >= 60")
    if require_signed_export_approval and not (
        export_approval_token_secret and export_approval_token_secret.strip()
    ):
        raise ValueError(
            "export_approval_token_secret must be configured when signed export approval is required"
        )
    approval_token_secret = (
        export_approval_token_secret.strip()
        if export_approval_token_secret and export_approval_token_secret.strip()
        else "dev-export-approval-secret"
    )

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

    def _resolve_case_search_export_status(
        result: CaseSearchResult,
    ) -> tuple[bool, str]:
        if not result.source_id or not result.document_url:
            return False, "source_export_metadata_missing"
        source_entry = source_registry.get_source(result.source_id)
        if source_entry is None:
            return False, "source_not_in_registry_for_export"
        allowed_hosts = allowed_hosts_for_source(str(source_entry.url))
        if not is_url_allowed_for_source(str(result.document_url), allowed_hosts):
            return False, "export_url_not_allowed_for_source"
        return is_source_export_allowed(
            result.source_id,
            source_policy=source_policy,
        )

    def _apply_case_search_export_policy(
        search_response: CaseSearchResponse,
    ) -> CaseSearchResponse:
        filtered_results: list[CaseSearchResult] = []
        for result in search_response.results:
            export_allowed, policy_reason = _resolve_case_search_export_status(result)
            enriched_result = result.model_copy(
                update={
                    "export_allowed": export_allowed,
                    "export_policy_reason": policy_reason,
                }
            )
            if case_search_official_only_results and not export_allowed:
                continue
            filtered_results.append(enriched_result)
        return CaseSearchResponse(results=filtered_results)

    @router.post("/search/cases", response_model=CaseSearchResponse)
    async def search_cases(
        payload: CaseSearchRequest, request: Request, response: Response
    ) -> CaseSearchResponse | JSONResponse:
        trace_id = getattr(request.state, "trace_id", "")
        response.headers["x-trace-id"] = trace_id
        assessment = assess_case_query(payload.query)
        if not assessment.is_specific:
            refinement_hint = f" {' '.join(assessment.hints)}" if assessment.hints else ""
            return _error_response(
                status_code=422,
                trace_id=trace_id,
                code="VALIDATION_ERROR",
                message=(
                    "Case-law query is too broad. Please include specific terms such as "
                    f"program, issue, court, or citation.{refinement_hint}"
                ),
                policy_reason="case_search_query_too_broad",
            )
        try:
            try:
                case_search_response = await run_in_threadpool(
                    case_search_service.search,
                    payload,
                )
            except RuntimeError as exc:
                if not is_threadpool_unavailable_runtime_error(exc):
                    raise
                # Python Workers can run in threadless runtimes where threadpool
                # execution is unavailable; fallback to direct invocation.
                case_search_response = case_search_service.search(payload)
        except ApiError as exc:
            return _error_response(
                status_code=exc.status_code,
                trace_id=trace_id,
                code=exc.code,
                message=exc.message,
            )
        return _apply_case_search_export_policy(case_search_response)

    @router.post(
        "/export/cases/approval", response_model=CaseExportApprovalResponse
    )
    async def approve_case_export(
        payload: CaseExportApprovalRequest,
        request: Request,
        response: Response,
    ) -> CaseExportApprovalResponse | JSONResponse:
        trace_id = getattr(request.state, "trace_id", "")
        response.headers["x-trace-id"] = trace_id
        source_entry = source_registry.get_source(payload.source_id)
        if source_entry is None:
            return _error_response(
                status_code=403,
                trace_id=trace_id,
                code="POLICY_BLOCKED",
                message="Case export blocked by source policy (source_not_in_registry_for_export)",
                policy_reason="source_not_in_registry_for_export",
            )

        if not payload.user_approved:
            return _error_response(
                status_code=403,
                trace_id=trace_id,
                code="POLICY_BLOCKED",
                message="Case export requires explicit user approval before download",
                policy_reason="source_export_user_approval_required",
            )

        allowed_hosts = allowed_hosts_for_source(str(source_entry.url))
        if not is_url_allowed_for_source(str(payload.document_url), allowed_hosts):
            return _error_response(
                status_code=422,
                trace_id=trace_id,
                code="VALIDATION_ERROR",
                message="Case export URL host does not match the configured source host",
                policy_reason="export_url_not_allowed_for_source",
            )

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

        issued_at_epoch = int(time.time())
        approval_token = _issue_export_approval_token(
            secret=approval_token_secret,
            source_id=payload.source_id,
            case_id=payload.case_id,
            document_url=str(payload.document_url),
            issued_at_epoch=issued_at_epoch,
        )
        return CaseExportApprovalResponse(
            approval_token=approval_token,
            expires_at_epoch=issued_at_epoch + export_approval_token_ttl_seconds,
        )

    @router.post("/export/cases", response_model=None)
    async def export_cases(
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

        allowed_hosts = allowed_hosts_for_source(str(source_entry.url))

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

        if not is_url_allowed_for_source(str(payload.document_url), allowed_hosts):
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

        has_valid_approval_token = False
        if payload.approval_token:
            has_valid_approval_token = _has_valid_export_approval_token(
                token=payload.approval_token,
                secret=approval_token_secret,
                source_id=payload.source_id,
                case_id=payload.case_id,
                document_url=str(payload.document_url),
                ttl_seconds=export_approval_token_ttl_seconds,
                now_epoch=int(time.time()),
            )

        approval_satisfied = payload.user_approved or has_valid_approval_token
        if require_signed_export_approval and not has_valid_approval_token:
            approval_satisfied = False

        if not approval_satisfied:
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

        request_url = _build_source_scoped_request_url(
            document_url=str(payload.document_url),
            source_url=str(source_entry.url),
        )
        try:
            try:
                payload_bytes, media_type, final_url = await run_in_threadpool(
                    _download_export_payload,
                    request_url=request_url,
                    max_download_bytes=export_max_download_bytes,
                    allowed_hosts=allowed_hosts,
                )
            except RuntimeError as exc:
                if not is_threadpool_unavailable_runtime_error(exc):
                    raise
                # Python Workers can run in threadless runtimes where threadpool
                # execution is unavailable; fallback to direct invocation.
                payload_bytes, media_type, final_url = _download_export_payload(
                    request_url=request_url,
                    max_download_bytes=export_max_download_bytes,
                    allowed_hosts=allowed_hosts,
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
        except ExportRedirectHostError as exc:
            _record_export_event(
                request=request,
                payload=payload,
                outcome="blocked",
                policy_reason="export_redirect_url_not_allowed_for_source",
                document_url=exc.redirect_url,
            )
            return _error_response(
                status_code=422,
                trace_id=trace_id,
                code="VALIDATION_ERROR",
                message="Case export redirected to a URL host that does not match the configured source host",
                policy_reason="export_redirect_url_not_allowed_for_source",
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

        if not is_url_allowed_for_source(final_url, allowed_hosts):
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
    async def search_cases_disabled(request: Request) -> JSONResponse:
        trace_id = getattr(request.state, "trace_id", "")
        return _error_response(
            status_code=503,
            trace_id=trace_id,
            code="SOURCE_UNAVAILABLE",
            message="Case-law search is disabled in this deployment.",
        )

    @router.post("/export/cases", response_model=None)
    async def export_cases_disabled(request: Request) -> JSONResponse:
        trace_id = getattr(request.state, "trace_id", "")
        return _error_response(
            status_code=503,
            trace_id=trace_id,
            code="SOURCE_UNAVAILABLE",
            message="Case export is disabled in this deployment.",
        )

    @router.post("/export/cases/approval", response_model=None)
    async def export_cases_approval_disabled(request: Request) -> JSONResponse:
        trace_id = getattr(request.state, "trace_id", "")
        return _error_response(
            status_code=503,
            trace_id=trace_id,
            code="SOURCE_UNAVAILABLE",
            message="Case export approval is disabled in this deployment.",
        )

    return router
