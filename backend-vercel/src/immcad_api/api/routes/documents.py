from __future__ import annotations

from datetime import date
import hashlib
import inspect
from typing import Any
import uuid

import os
from fastapi import APIRouter, File, Form, Request, Response, UploadFile
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

from immcad_api.policy.document_filing_deadlines import (
    FilingDeadlineContext,
    FilingDeadlineEvaluation,
    evaluate_filing_deadline,
    is_near_submission_file_limit,
    submission_channel_limits,
)
from immcad_api.policy.document_requirements import (
    FilingForum,
    evaluate_readiness as evaluate_policy_readiness,
)
from immcad_api.policy.document_types import require_canonical_document_type
from immcad_api.schemas import (
    DocumentClassificationOverrideRequest,
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
from immcad_api.services.document_matter_store import StoredSourceFile
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
    default_profile_id_by_forum: dict[FilingForum, str] = {
        FilingForum.FEDERAL_COURT_JR: "federal_court_jr_leave",
        FilingForum.RPD: "rpd",
        FilingForum.RAD: "rad",
        FilingForum.ID: "id",
        FilingForum.IAD: "iad",
        FilingForum.IRCC_APPLICATION: "ircc_pr_card_renewal",
    }
    supported_profiles_by_forum: dict[FilingForum, tuple[str, ...]] = {
        FilingForum.FEDERAL_COURT_JR: (
            "federal_court_jr_leave",
            "federal_court_jr_hearing",
        ),
        FilingForum.RPD: ("rpd",),
        FilingForum.RAD: ("rad",),
        FilingForum.ID: ("id",),
        FilingForum.IAD: (
            "iad",
            "iad_sponsorship",
            "iad_residency",
            "iad_admissibility",
        ),
        FilingForum.IRCC_APPLICATION: ("ircc_pr_card_renewal",),
    }
    unsupported_profile_families = (
        "humanitarian_and_compassionate",
        "prra",
        "work_permit",
        "study_permit",
        "citizenship_proof",
    )

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
        ocr_warning_files: int | None = None,
        low_confidence_classification_files: int | None = None,
        parser_failure_files: int | None = None,
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
            ocr_warning_files=ocr_warning_files,
            low_confidence_classification_files=low_confidence_classification_files,
            parser_failure_files=parser_failure_files,
        )

    def _record_document_compilation_event(
        *,
        request: Request,
        matter_id: str | None,
        forum: str | None,
        route: str,
        status_code: int,
        outcome: str,
        policy_reason: str | None = None,
    ) -> None:
        if request_metrics is None:
            return
        raw_client_id = getattr(request.state, "client_id", None)
        client_id = str(raw_client_id).strip() if raw_client_id else None
        request_metrics.record_document_compilation_outcome(
            outcome=outcome,
            policy_reason=policy_reason,
            trace_id=getattr(request.state, "trace_id", ""),
            client_id=client_id,
            matter_id=matter_id,
            forum=forum,
            route=route,
            http_status=status_code,
        )

    def _record_document_classification_override_event(
        *,
        request: Request,
        matter_id: str | None,
        forum: str | None,
        file_id: str | None,
        previous_classification: str | None,
        new_classification: str | None,
        outcome: str,
        policy_reason: str | None = None,
    ) -> None:
        if request_metrics is None:
            return
        raw_client_id = getattr(request.state, "client_id", None)
        client_id = str(raw_client_id).strip() if raw_client_id else None
        request_metrics.record_document_classification_override_event(
            trace_id=getattr(request.state, "trace_id", ""),
            client_id=client_id,
            matter_id=matter_id,
            forum=forum,
            file_id=file_id,
            previous_classification=previous_classification,
            new_classification=new_classification,
            outcome=outcome,
            policy_reason=policy_reason,
        )

    def _blocking_rule_violation_codes(rule_violations: Any) -> tuple[str, ...]:
        if not isinstance(rule_violations, list):
            return ()
        blocking_codes: set[str] = set()
        for violation in rule_violations:
            if isinstance(violation, dict):
                severity = str(violation.get("severity", "")).strip().lower()
                code = str(violation.get("violation_code") or "").strip()
            else:
                severity = str(getattr(violation, "severity", "")).strip().lower()
                code = str(getattr(violation, "violation_code", "")).strip()
            if severity == "blocking" and code:
                blocking_codes.add(code)
        return tuple(sorted(blocking_codes))

    def _legacy_signature_type_error(
        error: TypeError,
        *,
        argument_name: str,
    ) -> bool:
        message = str(error)
        return (
            "unexpected keyword argument" in message
            and f"'{argument_name}'" in message
        )

    def _build_package_accepts_profile_id() -> bool:
        try:
            parameters = inspect.signature(package_service.build_package).parameters.values()
        except (TypeError, ValueError):
            return True
        for parameter in parameters:
            if parameter.kind == inspect.Parameter.VAR_KEYWORD:
                return True
            if parameter.name == "compilation_profile_id":
                return True
        return False

    def _build_package_accepts_source_files() -> bool:
        try:
            parameters = inspect.signature(package_service.build_package).parameters.values()
        except (TypeError, ValueError):
            return True
        for parameter in parameters:
            if parameter.kind == inspect.Parameter.VAR_KEYWORD:
                return True
            if parameter.name == "source_files":
                return True
        return False

    def _build_package_accepts_additional_blocking_issues() -> bool:
        try:
            parameters = inspect.signature(package_service.build_package).parameters.values()
        except (TypeError, ValueError):
            return True
        for parameter in parameters:
            if parameter.kind == inspect.Parameter.VAR_KEYWORD:
                return True
            if parameter.name == "additional_blocking_issues":
                return True
        return False

    def _evaluate_readiness_accepts_profile_id() -> bool:
        evaluator = getattr(package_service, "evaluate_readiness", None)
        if not callable(evaluator):
            return False
        try:
            parameters = inspect.signature(evaluator).parameters.values()
        except (TypeError, ValueError):
            return True
        for parameter in parameters:
            if parameter.kind == inspect.Parameter.VAR_KEYWORD:
                return True
            if parameter.name == "compilation_profile_id":
                return True
        return False

    def _evaluate_readiness_for_matter(
        *,
        forum: FilingForum,
        compilation_profile_id: str | None,
        classified_doc_types: set[str],
        blocking_issues: set[str],
    ) -> Any:
        evaluator = getattr(package_service, "evaluate_readiness", None)
        if not callable(evaluator):
            return evaluate_policy_readiness(
                forum=forum,
                classified_doc_types=classified_doc_types,
                blocking_issues=blocking_issues,
            )
        readiness_kwargs: dict[str, Any] = {
            "forum": forum.value,
            "classified_doc_types": classified_doc_types,
            "blocking_issues": blocking_issues,
        }
        if _evaluate_readiness_accepts_profile_id():
            readiness_kwargs["compilation_profile_id"] = compilation_profile_id
        try:
            return evaluator(**readiness_kwargs)
        except TypeError as error:
            if (
                "compilation_profile_id" in readiness_kwargs
                and _legacy_signature_type_error(
                    error,
                    argument_name="compilation_profile_id",
                )
            ):
                readiness_kwargs.pop("compilation_profile_id", None)
                return evaluator(**readiness_kwargs)
            raise

    def _build_compiled_binder_accepts_profile_id() -> bool:
        builder = getattr(package_service, "build_compiled_binder", None)
        if not callable(builder):
            return False
        try:
            parameters = inspect.signature(builder).parameters.values()
        except (TypeError, ValueError):
            return True
        for parameter in parameters:
            if parameter.kind == inspect.Parameter.VAR_KEYWORD:
                return True
            if parameter.name == "compilation_profile_id":
                return True
        return False

    def _build_compiled_binder_accepts_source_files() -> bool:
        builder = getattr(package_service, "build_compiled_binder", None)
        if not callable(builder):
            return False
        try:
            parameters = inspect.signature(builder).parameters.values()
        except (TypeError, ValueError):
            return True
        for parameter in parameters:
            if parameter.kind == inspect.Parameter.VAR_KEYWORD:
                return True
            if parameter.name == "source_files":
                return True
        return False

    def _build_package_for_matter(
        *,
        matter_id: str,
        forum: str,
        compilation_profile_id: str | None,
        intake_results: list[DocumentIntakeResult] | tuple[DocumentIntakeResult, ...],
        source_files: list[StoredSourceFile] | tuple[StoredSourceFile, ...] | None = None,
        additional_blocking_issues: tuple[str, ...] | list[str] | None = None,
    ) -> Any:
        build_kwargs: dict[str, Any] = {
            "matter_id": matter_id,
            "forum": forum,
            "intake_results": intake_results,
        }
        if _build_package_accepts_profile_id():
            build_kwargs["compilation_profile_id"] = compilation_profile_id
        if source_files is not None and _build_package_accepts_source_files():
            build_kwargs["source_files"] = source_files
        if (
            additional_blocking_issues is not None
            and _build_package_accepts_additional_blocking_issues()
        ):
            build_kwargs["additional_blocking_issues"] = additional_blocking_issues

        try:
            return package_service.build_package(**build_kwargs)
        except TypeError as error:
            retry_kwargs = dict(build_kwargs)
            removed_legacy_argument = False
            if (
                "compilation_profile_id" in retry_kwargs
                and _legacy_signature_type_error(
                    error,
                    argument_name="compilation_profile_id",
                )
            ):
                retry_kwargs.pop("compilation_profile_id", None)
                removed_legacy_argument = True
            if (
                "source_files" in retry_kwargs
                and _legacy_signature_type_error(
                    error,
                    argument_name="source_files",
                )
            ):
                retry_kwargs.pop("source_files", None)
                removed_legacy_argument = True
            if (
                "additional_blocking_issues" in retry_kwargs
                and _legacy_signature_type_error(
                    error,
                    argument_name="additional_blocking_issues",
                )
            ):
                retry_kwargs.pop("additional_blocking_issues", None)
                removed_legacy_argument = True
            if removed_legacy_argument:
                return package_service.build_package(**retry_kwargs)
            raise

    def _build_compiled_binder_for_matter(
        *,
        matter_id: str,
        forum: str,
        compilation_profile_id: str | None,
        intake_results: list[DocumentIntakeResult] | tuple[DocumentIntakeResult, ...],
        source_files: list[StoredSourceFile] | tuple[StoredSourceFile, ...] | None = None,
    ) -> tuple[Any, bytes] | None:
        builder = getattr(package_service, "build_compiled_binder", None)
        if not callable(builder):
            return None
        build_kwargs: dict[str, Any] = {
            "matter_id": matter_id,
            "forum": forum,
            "intake_results": intake_results,
        }
        if _build_compiled_binder_accepts_profile_id():
            build_kwargs["compilation_profile_id"] = compilation_profile_id
        if source_files is not None and _build_compiled_binder_accepts_source_files():
            build_kwargs["source_files"] = source_files

        try:
            result = builder(**build_kwargs)
        except TypeError as error:
            retry_kwargs = dict(build_kwargs)
            removed_legacy_argument = False
            if (
                "compilation_profile_id" in retry_kwargs
                and _legacy_signature_type_error(
                    error,
                    argument_name="compilation_profile_id",
                )
            ):
                retry_kwargs.pop("compilation_profile_id", None)
                removed_legacy_argument = True
            if (
                "source_files" in retry_kwargs
                and _legacy_signature_type_error(
                    error,
                    argument_name="source_files",
                )
            ):
                retry_kwargs.pop("source_files", None)
                removed_legacy_argument = True
            if not removed_legacy_argument:
                raise
            result = builder(**retry_kwargs)

        if not isinstance(result, tuple) or len(result) != 2:
            return None
        package, raw_payload = result
        if isinstance(raw_payload, memoryview):
            payload_bytes = raw_payload.tobytes()
        elif isinstance(raw_payload, bytearray):
            payload_bytes = bytes(raw_payload)
        elif isinstance(raw_payload, bytes):
            payload_bytes = raw_payload
        else:
            return None
        if not payload_bytes:
            return None
        return package, payload_bytes

    def _resolve_compilation_profile_id_for_intake(
        *,
        forum: FilingForum,
        requested_profile_id: str | None,
    ) -> str | None:
        resolver = getattr(package_service, "resolve_compilation_profile_id", None)
        if not callable(resolver):
            return None
        resolved_profile_id = resolver(
            forum=forum.value,
            requested_profile_id=requested_profile_id,
        )
        normalized_resolved_profile_id = str(resolved_profile_id or "").strip().lower()
        return normalized_resolved_profile_id or None

    def _support_matrix_payload() -> dict[str, object]:
        return {
            "supported_profiles_by_forum": {
                forum.value: list(profiles)
                for forum, profiles in supported_profiles_by_forum.items()
            },
            "unsupported_profile_families": list(unsupported_profile_families),
        }

    def _invalid_compilation_profile_message(*, forum: FilingForum) -> str:
        supported_profiles = ", ".join(
            supported_profiles_by_forum.get(forum, ())
        ) or "none"
        unsupported_profiles = ", ".join(unsupported_profile_families)
        return (
            f"Unsupported compilation profile. Supported profiles for forum {forum.value}: "
            f"{supported_profiles}. Unsupported profile families: {unsupported_profiles}."
        )

    def _effective_profile_id_for_matter(
        *,
        forum: FilingForum,
        compilation_profile_id: str | None,
    ) -> str:
        normalized_profile_id = str(compilation_profile_id or "").strip().lower()
        if normalized_profile_id:
            return normalized_profile_id
        return default_profile_id_by_forum[forum]

    def _parse_optional_iso_date(*, value: str | None, field_name: str) -> date | None:
        normalized = str(value or "").strip()
        if not normalized:
            return None
        try:
            return date.fromisoformat(normalized)
        except ValueError as error:
            raise ValueError(f"{field_name} must use YYYY-MM-DD format") from error

    def _evaluate_filing_deadline_for_matter(
        *,
        forum: FilingForum,
        compilation_profile_id: str | None,
        filing_context: FilingDeadlineContext | None,
    ):
        effective_profile_id = _effective_profile_id_for_matter(
            forum=forum,
            compilation_profile_id=compilation_profile_id,
        )
        evaluation = evaluate_filing_deadline(
            profile_id=effective_profile_id,
            context=filing_context or FilingDeadlineContext(),
        )
        has_explicit_deadline_inputs = bool(
            (filing_context and filing_context.decision_date is not None)
            or (filing_context and filing_context.hearing_date is not None)
            or (filing_context and filing_context.service_date is not None)
            or (filing_context and filing_context.filing_date is not None)
            or (filing_context and filing_context.deadline_override_reason)
        )
        if has_explicit_deadline_inputs:
            return evaluation
        filtered_warnings = tuple(
            warning
            for warning in evaluation.warnings
            if warning != "filing_deadline_not_evaluated_missing_dates"
        )
        return FilingDeadlineEvaluation(
            profile_id=evaluation.profile_id,
            deadline_date=evaluation.deadline_date,
            blocking_issues=evaluation.blocking_issues,
            warnings=filtered_warnings,
        )

    def _readiness_response_for_matter(
        *,
        matter_id: str,
        forum: FilingForum,
        compilation_profile_id: str | None,
        results: list[DocumentIntakeResult] | tuple[DocumentIntakeResult, ...],
        source_files: list[StoredSourceFile] | tuple[StoredSourceFile, ...] | None = None,
        filing_context: FilingDeadlineContext | None = None,
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
        deadline_evaluation = _evaluate_filing_deadline_for_matter(
            forum=forum,
            compilation_profile_id=compilation_profile_id,
            filing_context=filing_context,
        )
        blocking_issues.update(deadline_evaluation.blocking_issues)
        warnings = sorted(
            {
                *{
                    issue
                    for result in results
                    if result.quality_status == "processed"
                    for issue in result.issues
                },
                *set(deadline_evaluation.warnings),
            }
        )
        readiness = _evaluate_readiness_for_matter(
            forum=forum,
            compilation_profile_id=compilation_profile_id,
            classified_doc_types=classified_doc_types,
            blocking_issues=blocking_issues,
        )
        try:
            package = _build_package_for_matter(
                matter_id=matter_id,
                forum=forum.value,
                compilation_profile_id=compilation_profile_id,
                intake_results=list(results),
                source_files=source_files,
                additional_blocking_issues=tuple(deadline_evaluation.blocking_issues),
            )
        except Exception:
            package = None
        toc_entries = [] if package is None else list(getattr(package, "toc_entries", []) or [])
        pagination_summary = (
            {"total_documents": 0, "total_pages": 0, "last_assigned_page": 0}
            if package is None
            else (
                getattr(package, "pagination_summary", None)
                or {"total_documents": 0, "total_pages": 0, "last_assigned_page": 0}
            )
        )
        rule_violations = [] if package is None else list(getattr(package, "rule_violations", []) or [])
        compilation_profile = (
            {"id": "legacy-intake-compat", "version": "1.0"}
            if package is None
            else (
                getattr(package, "compilation_profile", None)
                or {"id": "legacy-intake-compat", "version": "1.0"}
            )
        )
        compilation_output_mode = (
            "metadata_plan_only"
            if package is None
            else (
                str(getattr(package, "compilation_output_mode", "")).strip()
                or "metadata_plan_only"
            )
        )
        record_sections = (
            []
            if package is None
            else list(getattr(package, "record_sections", []) or [])
        )
        compiled_artifact = (
            None if package is None else getattr(package, "compiled_artifact", None)
        )
        blocking_rule_codes = _blocking_rule_violation_codes(rule_violations)
        merged_blocking_issues = sorted({*readiness.blocking_issues, *blocking_rule_codes})
        return DocumentReadinessResponse(
            matter_id=matter_id,
            forum=forum.value,
            is_ready=readiness.is_ready and not blocking_rule_codes,
            missing_required_items=list(readiness.missing_required_items),
            blocking_issues=merged_blocking_issues,
            warnings=warnings,
            requirement_statuses=[
                {
                    "item": requirement.item,
                    "status": requirement.status,
                    "rule_scope": requirement.rule_scope,
                    "reason": requirement.reason or None,
                }
                for requirement in readiness.requirement_statuses
            ],
            toc_entries=toc_entries,
            pagination_summary=pagination_summary,
            rule_violations=rule_violations,
            compilation_profile=compilation_profile,
            compilation_output_mode=compilation_output_mode,
            compiled_artifact=compiled_artifact,
            record_sections=record_sections,
        )

    def _resolve_matter_client_id(request: Request) -> str:
        raw_client_id = getattr(request.state, "client_id", None)
        resolved_client_id = str(raw_client_id).strip() if raw_client_id else ""
        return resolved_client_id or "anonymous"

    def _build_failed_result(*, original_filename: str, issue: str) -> DocumentIntakeResult:
        issue_detail = DocumentIntakeService.issue_detail_for_failed_result(issue=issue)
        if hasattr(intake_service, "build_failed_result"):
            failed_result = intake_service.build_failed_result(
                original_filename=original_filename,
                issue=issue,
            )
            if (
                isinstance(failed_result, DocumentIntakeResult)
                and not failed_result.issue_details
            ):
                return failed_result.model_copy(update={"issue_details": [issue_detail]})
            return failed_result
        file_id = uuid.uuid4().hex[:10]
        return DocumentIntakeResult(
            file_id=file_id,
            original_filename=original_filename,
            normalized_filename=f"unclassified-{file_id}.pdf",
            classification="unclassified",
            quality_status="failed",
            issues=[issue],
            issue_details=[issue_detail],
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

    def _count_results_with_issue_codes(
        results: list[DocumentIntakeResult] | tuple[DocumentIntakeResult, ...],
        issue_codes: set[str],
    ) -> int:
        total = 0
        for result in results:
            normalized_issues = {
                str(issue).strip().lower() for issue in result.issues if str(issue).strip()
            }
            if normalized_issues & issue_codes:
                total += 1
        return total

    async def _read_upload_with_size_cap(
        upload: UploadFile,
        *,
        max_bytes: int,
        size_limit_issue: str = "upload_size_exceeded",
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
                    return None, size_limit_issue
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
        compilation_profile_id: str | None = Form(default=None),
        submission_channel: str | None = Form(default="portal"),
        decision_date: str | None = Form(default=None),
        hearing_date: str | None = Form(default=None),
        service_date: str | None = Form(default=None),
        filing_date: str | None = Form(default=None),
        deadline_override_reason: str | None = Form(default=None),
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
            channel_limits = submission_channel_limits(submission_channel)
        except ValueError:
            _record_document_intake_event(
                request=request,
                matter_id=submitted_matter_id,
                forum=normalized_forum or None,
                file_count=submitted_file_count,
                outcome="rejected",
                policy_reason="document_submission_channel_invalid",
            )
            return _error_response(
                status_code=422,
                trace_id=trace_id,
                code="VALIDATION_ERROR",
                message="Unsupported submission channel value",
                policy_reason="document_submission_channel_invalid",
            )

        effective_upload_max_files = min(upload_max_files, channel_limits.max_files)
        if len(files) > effective_upload_max_files:
            _record_document_intake_event(
                request=request,
                matter_id=submitted_matter_id,
                forum=normalized_forum or None,
                file_count=submitted_file_count,
                outcome="rejected",
                policy_reason="document_submission_channel_file_count_exceeded",
            )
            return _error_response(
                status_code=422,
                trace_id=trace_id,
                code="VALIDATION_ERROR",
                message="File count exceeds submission channel constraints",
                policy_reason="document_submission_channel_file_count_exceeded",
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

        try:
            parsed_decision_date = _parse_optional_iso_date(
                value=decision_date,
                field_name="decision_date",
            )
            parsed_hearing_date = _parse_optional_iso_date(
                value=hearing_date,
                field_name="hearing_date",
            )
            parsed_service_date = _parse_optional_iso_date(
                value=service_date,
                field_name="service_date",
            )
            parsed_filing_date = _parse_optional_iso_date(
                value=filing_date,
                field_name="filing_date",
            )
            normalized_deadline_override_reason = (
                str(deadline_override_reason or "").strip() or None
            )
            if deadline_override_reason is not None and normalized_deadline_override_reason is None:
                raise ValueError("deadline_override_reason cannot be blank")
            if (
                parsed_service_date is not None
                and parsed_hearing_date is not None
                and parsed_service_date > parsed_hearing_date
            ):
                raise ValueError("service_date must be <= hearing_date")
        except ValueError as error:
            _record_document_intake_event(
                request=request,
                matter_id=submitted_matter_id,
                forum=normalized_forum or None,
                file_count=submitted_file_count,
                outcome="rejected",
                policy_reason="document_deadline_input_invalid",
            )
            return _error_response(
                status_code=422,
                trace_id=trace_id,
                code="VALIDATION_ERROR",
                message=str(error),
                policy_reason="document_deadline_input_invalid",
            )

        try:
            normalized_compilation_profile_id = _resolve_compilation_profile_id_for_intake(
                forum=parsed_forum,
                requested_profile_id=compilation_profile_id,
            )
        except (ValueError, KeyError):
            _record_document_intake_event(
                request=request,
                matter_id=submitted_matter_id,
                forum=normalized_forum or None,
                file_count=submitted_file_count,
                outcome="rejected",
                policy_reason="document_compilation_profile_invalid",
            )
            return _error_response(
                status_code=422,
                trace_id=trace_id,
                code="VALIDATION_ERROR",
                message=_invalid_compilation_profile_message(forum=parsed_forum),
                policy_reason="document_compilation_profile_invalid",
            )

        request_preflight_warnings: list[str] = []
        if is_near_submission_file_limit(
            file_count=submitted_file_count,
            limits=channel_limits,
        ):
            request_preflight_warnings.append("submission_channel_near_file_limit")
        resolved_filing_date = parsed_filing_date or date.today()
        filing_context = FilingDeadlineContext(
            submission_channel=channel_limits.channel,
            decision_date=parsed_decision_date,
            hearing_date=parsed_hearing_date,
            service_date=parsed_service_date,
            filing_date=resolved_filing_date,
            deadline_override_reason=normalized_deadline_override_reason,
            preflight_warnings=tuple(request_preflight_warnings),
        )

        effective_matter_id = submitted_matter_id or f"matter-{uuid.uuid4().hex[:12]}"

        results: list[DocumentIntakeResult] = []
        captured_source_files: list[StoredSourceFile] = []
        effective_upload_max_bytes = min(upload_max_bytes, channel_limits.max_bytes_per_file)
        size_limit_issue = (
            "submission_channel_size_exceeded"
            if channel_limits.max_bytes_per_file < upload_max_bytes
            else "upload_size_exceeded"
        )
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
                    max_bytes=effective_upload_max_bytes,
                    size_limit_issue=size_limit_issue,
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
                    captured_source_files.append(
                        StoredSourceFile(
                            file_id=processed.file_id,
                            filename=original_filename,
                            payload_bytes=payload_bytes,
                        )
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
            compilation_profile_id=normalized_compilation_profile_id,
            results=results,
            source_files=captured_source_files,
            filing_context=filing_context,
        )

        readiness = _readiness_response_for_matter(
            matter_id=effective_matter_id,
            forum=parsed_forum,
            compilation_profile_id=normalized_compilation_profile_id,
            results=results,
            source_files=captured_source_files,
            filing_context=filing_context,
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
            ocr_warning_files=_count_results_with_issue_codes(
                results,
                {"ocr_required", "ocr_low_confidence", "ocr_budget_reached"},
            ),
            low_confidence_classification_files=_count_results_with_issue_codes(
                results,
                {"classification_low_confidence"},
            ),
            parser_failure_files=_count_results_with_issue_codes(results, {"file_unreadable"}),
        )

        return DocumentIntakeResponse(
            matter_id=effective_matter_id,
            forum=parsed_forum.value,
            compilation_profile_id=normalized_compilation_profile_id,
            results=results,
            blocking_issues=readiness.blocking_issues,
            warnings=readiness.warnings,
        )

    @router.get("/support-matrix", response_model=None)
    async def get_document_support_matrix(
        request: Request,
        response: Response,
    ) -> dict[str, object]:
        trace_id = getattr(request.state, "trace_id", "")
        response.headers["x-trace-id"] = trace_id
        return _support_matrix_payload()

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
            compilation_profile_id=matter.compilation_profile_id,
            results=matter.results,
            source_files=matter.source_files,
            filing_context=matter.filing_context,
        )

    @router.patch(
        "/matters/{matter_id}/classification",
        response_model=DocumentReadinessResponse,
    )
    async def override_document_classification(
        matter_id: str,
        override_request: DocumentClassificationOverrideRequest,
        request: Request,
        response: Response,
    ) -> DocumentReadinessResponse | JSONResponse:
        trace_id = getattr(request.state, "trace_id", "")
        response.headers["x-trace-id"] = trace_id

        normalized_file_id = override_request.file_id.strip()
        if not normalized_file_id:
            _record_document_classification_override_event(
                request=request,
                matter_id=matter_id,
                forum=None,
                file_id=None,
                previous_classification=None,
                new_classification=None,
                outcome="rejected",
                policy_reason="document_file_id_invalid",
            )
            return _error_response(
                status_code=422,
                trace_id=trace_id,
                code="VALIDATION_ERROR",
                message="Document file ID is required for classification override",
                policy_reason="document_file_id_invalid",
            )

        client_scope_id = _resolve_matter_client_id(request)
        matter = matter_store.get(client_id=client_scope_id, matter_id=matter_id)
        if matter is None:
            _record_document_classification_override_event(
                request=request,
                matter_id=matter_id,
                forum=None,
                file_id=normalized_file_id,
                previous_classification=None,
                new_classification=None,
                outcome="rejected",
                policy_reason="document_matter_not_found",
            )
            return _error_response(
                status_code=404,
                trace_id=trace_id,
                code="SOURCE_UNAVAILABLE",
                message="Document matter was not found",
                policy_reason="document_matter_not_found",
            )

        try:
            normalized_classification = require_canonical_document_type(
                override_request.classification,
                context="classification override",
            )
        except ValueError:
            _record_document_classification_override_event(
                request=request,
                matter_id=matter_id,
                forum=matter.forum.value,
                file_id=normalized_file_id,
                previous_classification=None,
                new_classification=str(override_request.classification).strip().lower(),
                outcome="rejected",
                policy_reason="document_classification_invalid",
            )
            return _error_response(
                status_code=422,
                trace_id=trace_id,
                code="VALIDATION_ERROR",
                message="Unsupported document classification override value",
                policy_reason="document_classification_invalid",
            )

        matched_index: int | None = None
        matched_result: DocumentIntakeResult | None = None
        for index, result in enumerate(matter.results):
            if result.file_id.strip() == normalized_file_id:
                matched_index = index
                matched_result = result
                break

        if matched_index is None or matched_result is None:
            _record_document_classification_override_event(
                request=request,
                matter_id=matter_id,
                forum=matter.forum.value,
                file_id=normalized_file_id,
                previous_classification=None,
                new_classification=normalized_classification,
                outcome="rejected",
                policy_reason="document_file_not_found",
            )
            return _error_response(
                status_code=404,
                trace_id=trace_id,
                code="SOURCE_UNAVAILABLE",
                message="Document file was not found in this matter",
                policy_reason="document_file_not_found",
            )

        previous_classification = matched_result.classification.strip().lower()
        updated_results = list(matter.results)
        updated_results[matched_index] = matched_result.model_copy(
            update={"classification": normalized_classification}
        )
        matter_store.put(
            client_id=client_scope_id,
            matter_id=matter_id,
            forum=matter.forum,
            compilation_profile_id=matter.compilation_profile_id,
            results=updated_results,
            source_files=matter.source_files,
            filing_context=matter.filing_context,
        )
        _record_document_classification_override_event(
            request=request,
            matter_id=matter_id,
            forum=matter.forum.value,
            file_id=normalized_file_id,
            previous_classification=previous_classification,
            new_classification=normalized_classification,
            outcome="updated",
        )
        return _readiness_response_for_matter(
            matter_id=matter_id,
            forum=matter.forum,
            compilation_profile_id=matter.compilation_profile_id,
            results=updated_results,
            source_files=matter.source_files,
            filing_context=matter.filing_context,
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
            _record_document_compilation_event(
                request=request,
                matter_id=matter_id,
                forum=None,
                route="package",
                status_code=404,
                outcome="blocked",
                policy_reason="document_matter_not_found",
            )
            return _error_response(
                status_code=404,
                trace_id=trace_id,
                code="SOURCE_UNAVAILABLE",
                message="Document matter was not found",
                policy_reason="document_matter_not_found",
            )

        deadline_evaluation = _evaluate_filing_deadline_for_matter(
            forum=matter.forum,
            compilation_profile_id=matter.compilation_profile_id,
            filing_context=matter.filing_context,
        )
        deadline_blocking_issues = tuple(deadline_evaluation.blocking_issues)
        package = await run_in_threadpool(
            _build_package_for_matter,
            matter_id=matter_id,
            forum=matter.forum.value,
            compilation_profile_id=matter.compilation_profile_id,
            intake_results=matter.results,
            source_files=matter.source_files,
            additional_blocking_issues=deadline_blocking_issues,
        )
        blocking_rule_codes = _blocking_rule_violation_codes(
            list(getattr(package, "rule_violations", []) or [])
        )
        if (not package.is_ready) or blocking_rule_codes or deadline_blocking_issues:
            _record_document_compilation_event(
                request=request,
                matter_id=matter_id,
                forum=matter.forum.value,
                route="package",
                status_code=409,
                outcome="blocked",
                policy_reason="document_package_not_ready",
            )
            return _error_response(
                status_code=409,
                trace_id=trace_id,
                code="POLICY_BLOCKED",
                message="Document package is not ready for generation",
                policy_reason="document_package_not_ready",
            )
        _record_document_compilation_event(
            request=request,
            matter_id=matter_id,
            forum=matter.forum.value,
            route="package",
            status_code=200,
            outcome="compiled",
        )
        return package

    @router.get("/matters/{matter_id}/package/download", response_model=None)
    async def download_document_matter_package(
        matter_id: str,
        request: Request,
        response: Response,
    ) -> Response | JSONResponse:
        trace_id = getattr(request.state, "trace_id", "")
        response.headers["x-trace-id"] = trace_id

        client_scope_id = _resolve_matter_client_id(request)
        matter = matter_store.get(client_id=client_scope_id, matter_id=matter_id)
        if matter is None:
            _record_document_compilation_event(
                request=request,
                matter_id=matter_id,
                forum=None,
                route="package_download",
                status_code=404,
                outcome="blocked",
                policy_reason="document_matter_not_found",
            )
            return _error_response(
                status_code=404,
                trace_id=trace_id,
                code="SOURCE_UNAVAILABLE",
                message="Document matter was not found",
                policy_reason="document_matter_not_found",
            )

        deadline_evaluation = _evaluate_filing_deadline_for_matter(
            forum=matter.forum,
            compilation_profile_id=matter.compilation_profile_id,
            filing_context=matter.filing_context,
        )
        deadline_blocking_issues = tuple(deadline_evaluation.blocking_issues)
        package = await run_in_threadpool(
            _build_package_for_matter,
            matter_id=matter_id,
            forum=matter.forum.value,
            compilation_profile_id=matter.compilation_profile_id,
            intake_results=matter.results,
            source_files=matter.source_files,
            additional_blocking_issues=deadline_blocking_issues,
        )
        blocking_rule_codes = _blocking_rule_violation_codes(
            list(getattr(package, "rule_violations", []) or [])
        )
        if (not package.is_ready) or blocking_rule_codes or deadline_blocking_issues:
            _record_document_compilation_event(
                request=request,
                matter_id=matter_id,
                forum=matter.forum.value,
                route="package_download",
                status_code=409,
                outcome="blocked",
                policy_reason="document_package_not_ready",
            )
            return _error_response(
                status_code=409,
                trace_id=trace_id,
                code="POLICY_BLOCKED",
                message="Document package is not ready for generation",
                policy_reason="document_package_not_ready",
            )

        package_mode = str(getattr(package, "compilation_output_mode", "")).strip().lower()
        package_artifact = getattr(package, "compiled_artifact", None)
        if package_mode != "compiled_pdf" or package_artifact is None:
            _record_document_compilation_event(
                request=request,
                matter_id=matter_id,
                forum=matter.forum.value,
                route="package_download",
                status_code=409,
                outcome="blocked",
                policy_reason="document_compiled_artifact_unavailable",
            )
            return _error_response(
                status_code=409,
                trace_id=trace_id,
                code="POLICY_BLOCKED",
                message="Compiled document package is not available",
                policy_reason="document_compiled_artifact_unavailable",
            )

        compiled_payload = await run_in_threadpool(
            _build_compiled_binder_for_matter,
            matter_id=matter_id,
            forum=matter.forum.value,
            compilation_profile_id=matter.compilation_profile_id,
            intake_results=matter.results,
            source_files=matter.source_files,
        )
        if compiled_payload is None:
            _record_document_compilation_event(
                request=request,
                matter_id=matter_id,
                forum=matter.forum.value,
                route="package_download",
                status_code=409,
                outcome="blocked",
                policy_reason="document_compiled_artifact_unavailable",
            )
            return _error_response(
                status_code=409,
                trace_id=trace_id,
                code="POLICY_BLOCKED",
                message="Compiled document package is not available",
                policy_reason="document_compiled_artifact_unavailable",
            )

        compiled_package, payload_bytes = compiled_payload
        artifact = getattr(compiled_package, "compiled_artifact", None) or package_artifact
        if artifact is None:
            _record_document_compilation_event(
                request=request,
                matter_id=matter_id,
                forum=matter.forum.value,
                route="package_download",
                status_code=409,
                outcome="blocked",
                policy_reason="document_compiled_artifact_unavailable",
            )
            return _error_response(
                status_code=409,
                trace_id=trace_id,
                code="POLICY_BLOCKED",
                message="Compiled document package is not available",
                policy_reason="document_compiled_artifact_unavailable",
            )

        expected_byte_size = int(getattr(artifact, "byte_size", -1))
        expected_sha256 = str(getattr(artifact, "sha256", "")).strip().lower()
        actual_sha256 = hashlib.sha256(payload_bytes).hexdigest()
        if expected_byte_size != len(payload_bytes) or (
            expected_sha256 and expected_sha256 != actual_sha256
        ):
            _record_document_compilation_event(
                request=request,
                matter_id=matter_id,
                forum=matter.forum.value,
                route="package_download",
                status_code=409,
                outcome="blocked",
                policy_reason="document_compiled_artifact_unavailable",
            )
            return _error_response(
                status_code=409,
                trace_id=trace_id,
                code="POLICY_BLOCKED",
                message="Compiled document package is not available",
                policy_reason="document_compiled_artifact_unavailable",
            )

        raw_filename = str(getattr(artifact, "filename", "")).strip()
        filename = raw_filename.replace('"', "") or f"{matter_id}-compiled-binder.pdf"
        _record_document_compilation_event(
            request=request,
            matter_id=matter_id,
            forum=matter.forum.value,
            route="package_download",
            status_code=200,
            outcome="compiled",
        )
        return Response(
            content=payload_bytes,
            media_type="application/pdf",
            headers={
                "x-trace-id": trace_id,
                "content-disposition": f'attachment; filename="{filename}"',
            },
        )

    return router


__all__ = ["build_documents_router"]
