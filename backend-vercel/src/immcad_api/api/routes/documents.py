from __future__ import annotations

from typing import Any
import uuid

import os
from fastapi import APIRouter, File, Form, Request, Response, UploadFile
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

from immcad_api.policy.document_requirements import FilingForum, evaluate_readiness
from immcad_api.schemas import (
    DocumentIntakeResult,
    DocumentIntakeResponse,
    DocumentReadinessResponse,
    ErrorEnvelope,
)
from immcad_api.services import (
    DocumentIntakeService,
    DocumentMatterStore,
    DocumentPackageService,
    InMemoryDocumentMatterStore,
)
from immcad_api.telemetry import RequestMetrics


def build_documents_router(
    *,
    request_metrics: RequestMetrics | None = None,
    intake_service: DocumentIntakeService | None = None,
    package_service: DocumentPackageService | None = None,
    matter_store: DocumentMatterStore | None = None,
    upload_max_bytes: int = 10 * 1024 * 1024,
    upload_max_files: int = 25,
    allowed_content_types: tuple[str, ...] = (
        "application/pdf",
        "image/png",
        "image/jpeg",
        "image/tiff",
    ),
) -> APIRouter:
    router = APIRouter(prefix="/api/documents", tags=["documents"])
    intake_service = intake_service or DocumentIntakeService()
    package_service = package_service or DocumentPackageService()
    matter_store = matter_store or InMemoryDocumentMatterStore()

    def _error_response(
        *,
        status_code: int,
        trace_id: str,
        code: str,
        message: str,
        policy_reason: str | None = None,
    ) -> JSONResponse:
        payload = ErrorEnvelope(
            error={
                "code": code,
                "message": message,
                "trace_id": trace_id,
                "policy_reason": policy_reason,
            }
        )
        return JSONResponse(
            status_code=status_code,
            content=payload.model_dump(mode="json"),
            headers={"x-trace-id": trace_id},
        )

    def _record_document_intake_event(
        *,
        request: Request,
        matter_id: str | None,
        forum: str | None,
        file_count: int,
        outcome: str,
        policy_reason: str | None = None,
    ) -> None:
        if request_metrics is None:
            return
        raw_client_id = getattr(request.state, "client_id", None)
        client_id = str(raw_client_id).strip() if raw_client_id else None
        request_metrics.record_document_intake_event(
            trace_id=getattr(request.state, "trace_id", ""),
            client_id=client_id,
            matter_id=matter_id,
            forum=forum,
            file_count=file_count,
            outcome=outcome,
            policy_reason=policy_reason,
        )

    def _readiness_response_for_matter(
        *,
        matter_id: str,
        forum: FilingForum,
        results: list[DocumentIntakeResult] | tuple[DocumentIntakeResult, ...],
    ) -> DocumentReadinessResponse:
        classified_doc_types = {
            result.classification.strip().lower()
            for result in results
            if result.classification.strip()
        }
        blocking_issues = {
            issue
            for result in results
            if result.quality_status in {"failed", "needs_review"}
            for issue in result.issues
        }
        warnings = sorted(
            {
                issue
                for result in results
                if result.quality_status == "processed"
                for issue in result.issues
            }
        )
        readiness = evaluate_readiness(
            forum=forum,
            classified_doc_types=classified_doc_types,
            blocking_issues=blocking_issues,
        )
        return DocumentReadinessResponse(
            matter_id=matter_id,
            forum=forum.value,
            is_ready=readiness.is_ready,
            missing_required_items=list(readiness.missing_required_items),
            blocking_issues=list(readiness.blocking_issues),
            warnings=warnings,
            requirement_statuses=[
                {
                    "item": requirement.item,
                    "status": requirement.status,
                    "rule_scope": requirement.rule_scope,
                    "reason": requirement.reason,
                }
                for requirement in readiness.requirement_statuses
            ],
        )

    def _resolve_matter_client_id(request: Request) -> str:
        raw_client_id = getattr(request.state, "client_id", None)
        resolved_client_id = str(raw_client_id).strip() if raw_client_id else ""
        return resolved_client_id or "anonymous"

    def _build_failed_result(*, original_filename: str, issue: str) -> DocumentIntakeResult:
        if hasattr(intake_service, "build_failed_result"):
            return intake_service.build_failed_result(
                original_filename=original_filename,
                issue=issue,
            )
        file_id = uuid.uuid4().hex[:10]
        return DocumentIntakeResult(
            file_id=file_id,
            original_filename=original_filename,
            normalized_filename=f"unclassified-{file_id}.pdf",
            classification="unclassified",
            quality_status="failed",
            issues=[issue],
        )

    def _is_allowed_file(
        *, content_type: str, filename: str | None, allowed_types: set[str]
    ) -> bool:
        filename = (filename or "").strip()
        _, ext = os.path.splitext(filename.lower())
        if content_type in allowed_types:
            return True
        if content_type == "application/octet-stream" and ext in {
            ".pdf",
            ".png",
            ".jpg",
            ".jpeg",
            ".tif",
            ".tiff",
        }:
            return True
        return False

    async def _read_upload_with_size_cap(
        upload: UploadFile,
        *,
        max_bytes: int,
    ) -> tuple[bytes | None, str | None]:
        chunk_size = max(min(max_bytes, 1024 * 1024), 64 * 1024)
        chunks: list[bytes] = []
        total_bytes = 0
        try:
            while True:
                chunk = await upload.read(chunk_size)
                if not chunk:
                    break
                total_bytes += len(chunk)
                if total_bytes > max_bytes:
                    return None, "upload_size_exceeded"
                chunks.append(chunk)
        except Exception:
            return None, "file_unreadable"
        return b"".join(chunks), None

    @router.post("/intake", response_model=DocumentIntakeResponse)
    async def intake_documents(
        request: Request,
        response: Response,
        forum: str = Form(...),
        matter_id: str | None = Form(default=None),
        files: list[UploadFile] | None = File(default=None),
    ) -> DocumentIntakeResponse | JSONResponse:
        trace_id = getattr(request.state, "trace_id", "")
        response.headers["x-trace-id"] = trace_id
        normalized_forum = forum.strip().lower()
        submitted_matter_id = (matter_id or "").strip() or None
        submitted_file_count = len(files or [])

        if not files:
            _record_document_intake_event(
                request=request,
                matter_id=submitted_matter_id,
                forum=normalized_forum or None,
                file_count=0,
                outcome="rejected",
                policy_reason="document_files_missing",
            )
            return _error_response(
                status_code=422,
                trace_id=trace_id,
                code="VALIDATION_ERROR",
                message="At least one document upload is required",
                policy_reason="document_files_missing",
            )
        if len(files) > upload_max_files:
            _record_document_intake_event(
                request=request,
                matter_id=submitted_matter_id,
                forum=normalized_forum or None,
                file_count=submitted_file_count,
                outcome="rejected",
                policy_reason="document_file_count_exceeded",
            )
            return _error_response(
                status_code=422,
                trace_id=trace_id,
                code="VALIDATION_ERROR",
                message="Too many files submitted in one request",
                policy_reason="document_file_count_exceeded",
            )

        try:
            parsed_forum = FilingForum(normalized_forum)
        except ValueError:
            _record_document_intake_event(
                request=request,
                matter_id=submitted_matter_id,
                forum=normalized_forum or None,
                file_count=submitted_file_count,
                outcome="rejected",
                policy_reason="document_forum_invalid",
            )
            return _error_response(
                status_code=422,
                trace_id=trace_id,
                code="VALIDATION_ERROR",
                message="Unsupported document forum value",
                policy_reason="document_forum_invalid",
            )

        effective_matter_id = submitted_matter_id or f"matter-{uuid.uuid4().hex[:12]}"

        results: list[DocumentIntakeResult] = []
        allowed_content_type_set = {
            content_type.strip().lower() for content_type in allowed_content_types
        }
        for upload in files:
            try:
                original_filename = upload.filename or "uploaded-file.pdf"
                content_type = (upload.content_type or "").strip().lower()
                if not _is_allowed_file(
                    content_type=content_type,
                    filename=original_filename,
                    allowed_types=allowed_content_type_set,
                ):
                    results.append(
                        _build_failed_result(
                            original_filename=original_filename,
                            issue="unsupported_file_type",
                        )
                    )
                    continue

                payload_bytes, read_error = await _read_upload_with_size_cap(
                    upload,
                    max_bytes=upload_max_bytes,
                )
                if read_error:
                    results.append(
                        _build_failed_result(
                            original_filename=original_filename,
                            issue=read_error,
                        )
                    )
                    continue
                if payload_bytes is None:
                    results.append(
                        _build_failed_result(
                            original_filename=original_filename,
                            issue="file_unreadable",
                        )
                    )
                    continue

                try:
                    processed = await run_in_threadpool(
                        intake_service.process_file,
                        original_filename=original_filename,
                        payload_bytes=payload_bytes,
                    )
                except ValueError:
                    processed = _build_failed_result(
                        original_filename=original_filename, issue="file_unreadable"
                    )
                results.append(processed)
            finally:
                await upload.close()

        client_scope_id = _resolve_matter_client_id(request)
        matter_store.put(
            client_id=client_scope_id,
            matter_id=effective_matter_id,
            forum=parsed_forum,
            results=results,
        )

        readiness = _readiness_response_for_matter(
            matter_id=effective_matter_id,
            forum=parsed_forum,
            results=results,
        )
        all_results_failed = bool(results) and all(
            result.quality_status == "failed" for result in results
        )
        _record_document_intake_event(
            request=request,
            matter_id=effective_matter_id,
            forum=parsed_forum.value,
            file_count=submitted_file_count,
            outcome="rejected" if all_results_failed else "accepted",
            policy_reason="document_all_files_failed" if all_results_failed else None,
        )

        return DocumentIntakeResponse(
            matter_id=effective_matter_id,
            forum=parsed_forum.value,
            results=results,
            blocking_issues=readiness.blocking_issues,
            warnings=readiness.warnings,
        )

    @router.get("/matters/{matter_id}/readiness", response_model=DocumentReadinessResponse)
    async def get_document_matter_readiness(
        matter_id: str,
        request: Request,
        response: Response,
    ) -> DocumentReadinessResponse | JSONResponse:
        trace_id = getattr(request.state, "trace_id", "")
        response.headers["x-trace-id"] = trace_id

        client_scope_id = _resolve_matter_client_id(request)
        matter = matter_store.get(client_id=client_scope_id, matter_id=matter_id)
        if matter is None:
            return _error_response(
                status_code=404,
                trace_id=trace_id,
                code="SOURCE_UNAVAILABLE",
                message="Document matter was not found",
                policy_reason="document_matter_not_found",
            )

        return _readiness_response_for_matter(
            matter_id=matter_id,
            forum=matter.forum,
            results=matter.results,
        )

    @router.post("/matters/{matter_id}/package", response_model=None)
    async def build_document_matter_package(
        matter_id: str,
        request: Request,
        response: Response,
    ) -> Any:
        trace_id = getattr(request.state, "trace_id", "")
        response.headers["x-trace-id"] = trace_id

        client_scope_id = _resolve_matter_client_id(request)
        matter = matter_store.get(client_id=client_scope_id, matter_id=matter_id)
        if matter is None:
            return _error_response(
                status_code=404,
                trace_id=trace_id,
                code="SOURCE_UNAVAILABLE",
                message="Document matter was not found",
                policy_reason="document_matter_not_found",
            )

        package = await run_in_threadpool(
            package_service.build_package,
            matter_id=matter_id,
            forum=matter.forum.value,
            intake_results=matter.results,
        )
        if not package.is_ready:
            return _error_response(
                status_code=409,
                trace_id=trace_id,
                code="POLICY_BLOCKED",
                message="Document package is not ready for generation",
                policy_reason="document_package_not_ready",
            )
        return package

    return router


__all__ = ["build_documents_router"]
