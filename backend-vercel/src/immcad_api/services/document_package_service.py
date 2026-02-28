from __future__ import annotations

import hashlib
import inspect
import os

try:
    import fitz
except Exception:  # pragma: no cover - optional compiled PDF dependency
    fitz = None  # type: ignore[assignment]
from immcad_api.policy.document_compilation_rules import (
    DocumentCompilationCatalog,
    DocumentCompilationProfile as CatalogCompilationProfile,
    load_document_compilation_rules,
)
from immcad_api.policy.document_compilation_validator import (
    DocumentCompilationViolation,
    validate_document_compilation,
)
from immcad_api.policy.document_requirements import (
    FilingForum,
    ReadinessResult,
    RequirementStatus,
    requirement_rules_for_forum,
    required_doc_types_for_forum,
)
from immcad_api.schemas import (
    DocumentCompiledArtifactMetadata,
    DocumentCompilationProfile,
    DocumentDisclosureChecklistEntry,
    DocumentIntakeResult,
    DocumentPackageResponse,
    DocumentPaginationSummary,
    DocumentRecordSection,
    DocumentRecordSectionSlotStatus,
    DocumentRuleViolation,
    DocumentTableOfContentsEntry,
)
from immcad_api.services.document_assembly_service import (
    AssemblyDocumentMetadata,
    DocumentAssemblyPlan,
    DocumentAssemblyService,
)
from immcad_api.services.document_matter_store import StoredSourceFile
from immcad_api.services.record_builders import RecordSection, build_record_sections

_FALLBACK_RULE_SOURCE_URL = "https://www.justice.gc.ca/eng/"
_COMPILED_PDF_ENABLED_VALUES = frozenset({"1", "true", "yes", "on"})
_PROFILE_ID_BY_FORUM: dict[FilingForum, str] = {
    FilingForum.FEDERAL_COURT_JR: "federal_court_jr_leave",
    FilingForum.RPD: "rpd",
    FilingForum.RAD: "rad",
    FilingForum.ID: "id",
    FilingForum.IAD: "iad",
    FilingForum.IRCC_APPLICATION: "ircc_pr_card_renewal",
}


class DocumentPackageService:
    def __init__(
        self,
        *,
        catalog: DocumentCompilationCatalog | None = None,
        assembly_service: DocumentAssemblyService | None = None,
    ) -> None:
        self._catalog = catalog or load_document_compilation_rules()
        self._assembly_service = assembly_service or DocumentAssemblyService(self._catalog)

    @staticmethod
    def _parse_forum(value: str) -> FilingForum:
        return FilingForum(value.strip().lower())

    def _resolve_profile_id(
        self,
        *,
        forum: FilingForum,
        requested_profile_id: str | None,
    ) -> str:
        normalized_profile_id = str(requested_profile_id or "").strip().lower()
        if not normalized_profile_id:
            return _PROFILE_ID_BY_FORUM[forum]
        profile = self._catalog.require_profile(normalized_profile_id)
        if profile.forum != forum.value:
            raise ValueError(
                "Compilation profile does not match forum"
            )
        return profile.profile_id

    def resolve_compilation_profile_id(
        self,
        forum: str,
        requested_profile_id: str | None,
    ) -> str:
        parsed_forum = self._parse_forum(forum)
        return self._resolve_profile_id(
            forum=parsed_forum,
            requested_profile_id=requested_profile_id,
        )

    @staticmethod
    def _collect_blocking_issues(intake_results: list[DocumentIntakeResult]) -> tuple[str, ...]:
        issues: set[str] = set()
        for result in intake_results:
            if result.quality_status in {"failed", "needs_review"}:
                issues.update(result.issues)
        return tuple(sorted(issues))

    @staticmethod
    def _collect_warning_issues(intake_results: list[DocumentIntakeResult]) -> tuple[str, ...]:
        warnings: set[str] = set()
        for result in intake_results:
            if result.quality_status == "processed":
                warnings.update(result.issues)
        return tuple(sorted(warnings))

    @staticmethod
    def _normalize_document_types(
        document_types: set[str] | list[str] | tuple[str, ...],
    ) -> set[str]:
        normalized: set[str] = set()
        for raw_doc_type in document_types:
            doc_type = str(raw_doc_type).strip().lower()
            if doc_type:
                normalized.add(doc_type)
        return normalized

    @staticmethod
    def _required_doc_types_for_profile(
        *,
        profile: CatalogCompilationProfile,
        classified_doc_types: set[str],
    ) -> tuple[str, ...]:
        ordered_doc_types: list[str] = []
        seen_doc_types: set[str] = set()

        def _append_doc_type(raw_doc_type: str) -> None:
            doc_type = str(raw_doc_type).strip().lower()
            if not doc_type or doc_type in seen_doc_types:
                return
            seen_doc_types.add(doc_type)
            ordered_doc_types.append(doc_type)

        for rule in profile.required_documents:
            _append_doc_type(rule.document_type)

        for rule in profile.conditional_rules:
            if str(rule.when_document_type).strip().lower() not in classified_doc_types:
                continue
            _append_doc_type(rule.requires_document_type)

        return tuple(ordered_doc_types)

    @classmethod
    def _evaluate_readiness_for_profile(
        cls,
        *,
        profile: CatalogCompilationProfile,
        classified_doc_types: set[str],
        blocking_issues: tuple[str, ...],
    ) -> ReadinessResult:
        required_doc_types = cls._required_doc_types_for_profile(
            profile=profile,
            classified_doc_types=classified_doc_types,
        )
        missing_required_items = tuple(
            doc_type for doc_type in required_doc_types if doc_type not in classified_doc_types
        )
        normalized_blocking_issues = tuple(
            sorted(
                {
                    str(issue).strip().lower()
                    for issue in blocking_issues
                    if str(issue).strip()
                }
            )
        )
        return ReadinessResult(
            is_ready=not missing_required_items and not normalized_blocking_issues,
            missing_required_items=missing_required_items,
            blocking_issues=normalized_blocking_issues,
        )

    def evaluate_readiness(
        self,
        *,
        forum: str,
        compilation_profile_id: str | None,
        classified_doc_types: set[str] | list[str] | tuple[str, ...],
        blocking_issues: set[str] | list[str] | tuple[str, ...] | None = None,
    ) -> ReadinessResult:
        parsed_forum = self._parse_forum(forum)
        profile_id = self._resolve_profile_id(
            forum=parsed_forum,
            requested_profile_id=compilation_profile_id,
        )
        profile = self._catalog.require_profile(profile_id)
        normalized_doc_types = self._normalize_document_types(classified_doc_types)
        required_doc_types = self._required_doc_types_for_profile(
            profile=profile,
            classified_doc_types=normalized_doc_types,
        )
        missing_required_items = tuple(
            doc_type for doc_type in required_doc_types if doc_type not in normalized_doc_types
        )
        normalized_blocking_issues = tuple(
            sorted(
                {
                    str(issue).strip().lower()
                    for issue in blocking_issues or ()
                    if str(issue).strip()
                }
            )
        )

        requirement_statuses: list[RequirementStatus] = []
        for rule in profile.required_documents:
            document_type = str(rule.document_type).strip().lower()
            doc_present = document_type in normalized_doc_types
            requirement_statuses.append(
                RequirementStatus(
                    item=document_type,
                    status="present" if doc_present else "missing",
                    rule_scope="base",
                    reason=rule.remediation if not doc_present else "",
                )
            )
        for rule in profile.conditional_rules:
            when_document_type = str(rule.when_document_type).strip().lower()
            if when_document_type not in normalized_doc_types:
                continue
            requires_document_type = str(rule.requires_document_type).strip().lower()
            doc_present = requires_document_type in normalized_doc_types
            requirement_statuses.append(
                RequirementStatus(
                    item=requires_document_type,
                    status="present" if doc_present else "missing",
                    rule_scope="conditional",
                    reason=rule.remediation if not doc_present else "",
                )
            )

        return ReadinessResult(
            is_ready=not missing_required_items and not normalized_blocking_issues,
            missing_required_items=missing_required_items,
            blocking_issues=normalized_blocking_issues,
            requirement_statuses=tuple(requirement_statuses),
        )

    @staticmethod
    def _resolved_page_count(result: DocumentIntakeResult) -> int:
        if result.total_pages > 0:
            return result.total_pages
        if result.page_char_counts:
            return len(result.page_char_counts)
        return 1

    @staticmethod
    def _build_checklist(
        *,
        forum: FilingForum,
        classified_doc_types: set[str],
    ) -> list[DocumentDisclosureChecklistEntry]:
        required_items = required_doc_types_for_forum(
            forum=forum,
            classified_doc_types=classified_doc_types,
        )
        requirement_rules = requirement_rules_for_forum(
            forum=forum,
            classified_doc_types=classified_doc_types,
        )
        rule_by_item = {rule.item: rule for rule in requirement_rules}
        checklist: list[DocumentDisclosureChecklistEntry] = []
        for required_doc_type in required_items:
            status = "present" if required_doc_type in classified_doc_types else "missing"
            rule = rule_by_item.get(required_doc_type)
            checklist.append(
                DocumentDisclosureChecklistEntry(
                    item=required_doc_type,
                    status=status,
                    rule_scope=rule.rule_scope if rule is not None else "base",
                    reason=rule.reason if rule is not None else None,
                )
            )
        return checklist

    @staticmethod
    def _rule_document_type_to_section_id(
        *,
        profile: CatalogCompilationProfile,
        sections: tuple[RecordSection, ...],
    ) -> dict[str, str]:
        rule_document_types = {
            *(
                rule.document_type
                for rule in profile.required_documents
            ),
            *(
                rule.requires_document_type
                for rule in profile.conditional_rules
            ),
        }
        mapping: dict[str, str] = {}
        for document_type in sorted(rule_document_types):
            matching_sections = [
                section.section_id for section in sections if document_type in section.document_types
            ]
            if len(matching_sections) != 1:
                raise ValueError(
                    "Record section slot mapping is ambiguous or missing "
                    f"for profile '{profile.profile_id}' and document_type '{document_type}'"
                )
            mapping[document_type] = matching_sections[0]
        return mapping

    def _build_record_sections(
        self,
        *,
        profile: CatalogCompilationProfile,
        classified_doc_types: set[str],
    ) -> list[DocumentRecordSection]:
        sections = build_record_sections(profile.profile_id)
        section_slot_statuses: dict[str, list[DocumentRecordSectionSlotStatus]] = {
            section.section_id: [] for section in sections
        }
        section_mapping = self._rule_document_type_to_section_id(
            profile=profile,
            sections=sections,
        )

        for rule in profile.required_documents:
            section_id = section_mapping[rule.document_type]
            is_present = rule.document_type in classified_doc_types
            section_slot_statuses[section_id].append(
                DocumentRecordSectionSlotStatus(
                    document_type=rule.document_type,
                    status="present" if is_present else "missing",
                    rule_scope="base",
                    reason=None if is_present else rule.remediation,
                )
            )

        for rule in profile.conditional_rules:
            section_id = section_mapping[rule.requires_document_type]
            is_triggered = rule.when_document_type in classified_doc_types
            is_present = (not is_triggered) or (rule.requires_document_type in classified_doc_types)
            section_slot_statuses[section_id].append(
                DocumentRecordSectionSlotStatus(
                    document_type=rule.requires_document_type,
                    status="present" if is_present else "missing",
                    rule_scope="conditional",
                    reason=None if is_present else rule.remediation,
                )
            )

        hydrated_sections: list[DocumentRecordSection] = []
        for section in sections:
            slot_statuses = section_slot_statuses.get(section.section_id, [])
            missing_document_types = sorted(
                {
                    slot_status.document_type
                    for slot_status in slot_statuses
                    if slot_status.status == "missing"
                }
            )
            missing_reasons = [
                slot_status.reason
                for slot_status in slot_statuses
                if slot_status.status == "missing" and slot_status.reason
            ]
            hydrated_sections.append(
                DocumentRecordSection(
                    section_id=section.section_id,
                    title=section.title,
                    instructions=section.instructions,
                    document_types=list(section.document_types),
                    section_status="missing" if missing_document_types else "present",
                    slot_statuses=slot_statuses,
                    missing_document_types=missing_document_types,
                    missing_reasons=missing_reasons,
                )
            )
        return hydrated_sections

    @staticmethod
    def _hydrate_record_sections(
        sections: list[DocumentRecordSection],
    ) -> list[DocumentRecordSection]:
        hydrated_sections: list[DocumentRecordSection] = []
        for section in sections:
            normalized_section = DocumentRecordSection.model_validate(section)
            missing_document_types = list(normalized_section.missing_document_types) or sorted(
                {
                    slot_status.document_type
                    for slot_status in normalized_section.slot_statuses
                    if slot_status.status == "missing"
                }
            )
            missing_reasons = list(normalized_section.missing_reasons) or [
                slot_status.reason
                for slot_status in normalized_section.slot_statuses
                if slot_status.status == "missing" and slot_status.reason
            ]
            hydrated_sections.append(
                normalized_section.model_copy(
                    update={
                        "section_status": "missing" if missing_document_types else "present",
                        "missing_document_types": missing_document_types,
                        "missing_reasons": missing_reasons,
                    }
                )
            )
        return hydrated_sections

    @staticmethod
    def _build_cover_letter_draft(
        *,
        forum: FilingForum,
        matter_id: str,
        missing_required_items: tuple[str, ...],
        blocking_issues: tuple[str, ...],
    ) -> str:
        lines = [
            f"Re: Procedural filing package draft for matter {matter_id}",
            f"Forum: {forum.value}",
            "",
            "Please find enclosed the current document package prepared for procedural review.",
        ]
        if missing_required_items:
            lines.append(
                "The following required items are currently missing: "
                + ", ".join(missing_required_items)
                + "."
            )
        if blocking_issues:
            lines.append(
                "The following blocking issues must be resolved before filing: "
                + ", ".join(blocking_issues)
                + "."
            )
        if not missing_required_items and not blocking_issues:
            lines.append("No blocking completeness gaps were detected in this package.")

        lines.append("")
        lines.append("This is a procedural draft and requires legal review before filing.")
        return "\n".join(lines)

    @staticmethod
    def _rule_violation_from_catalog(
        violation: DocumentCompilationViolation,
    ) -> DocumentRuleViolation:
        return DocumentRuleViolation(
            violation_code=violation.violation_code,
            severity=violation.severity,
            rule_id=violation.rule_id,
            rule_source_url=violation.rule_source_url or _FALLBACK_RULE_SOURCE_URL,
            remediation=violation.remediation,
        )

    @staticmethod
    def _sort_rule_violations(
        violations: list[DocumentRuleViolation],
    ) -> list[DocumentRuleViolation]:
        severity_rank = {"blocking": 0, "warning": 1}
        return sorted(
            violations,
            key=lambda violation: (
                severity_rank.get(violation.severity, 99),
                violation.violation_code,
                violation.rule_id or "",
                violation.rule_source_url,
            ),
        )

    def _evaluate_rule_violations(
        self,
        *,
        profile_id: str,
        intake_results: list[DocumentIntakeResult],
        page_ranges: tuple[tuple[int, int], ...],
        assembly_violations: tuple[DocumentCompilationViolation, ...],
    ) -> list[DocumentRuleViolation]:
        profile = self._catalog.require_profile(profile_id)
        classified_doc_types = {
            result.classification.strip().lower()
            for result in intake_results
            if result.classification.strip()
        }
        computed_violations = validate_document_compilation(
            profile=profile,
            provided_document_types=classified_doc_types,
            page_ranges=page_ranges,
        )

        violations = [
            self._rule_violation_from_catalog(violation)
            for violation in (assembly_violations or computed_violations)
        ]

        for issue in self._collect_blocking_issues(intake_results):
            violations.append(
                DocumentRuleViolation(
                    violation_code=f"blocking_issue_{issue}",
                    severity="blocking",
                    message=f"Blocking intake issue: {issue}",
                    rule_id=issue,
                    rule_source_url=_FALLBACK_RULE_SOURCE_URL,
                    remediation="Resolve blocking intake issues and re-upload affected files.",
                )
            )

        for warning in self._collect_warning_issues(intake_results):
            violations.append(
                DocumentRuleViolation(
                    violation_code=f"warning_issue_{warning}",
                    severity="warning",
                    message=f"Non-blocking intake warning: {warning}",
                    rule_id=warning,
                    rule_source_url=_FALLBACK_RULE_SOURCE_URL,
                )
            )

        return self._sort_rule_violations(violations)

    @staticmethod
    def _build_pagination_summary(
        toc_entries: list[DocumentTableOfContentsEntry],
    ) -> DocumentPaginationSummary:
        if not toc_entries:
            return DocumentPaginationSummary()
        total_pages = max(entry.end_page or 0 for entry in toc_entries)
        return DocumentPaginationSummary(
            total_documents=len(toc_entries),
            total_pages=total_pages,
            last_assigned_page=total_pages,
        )

    def _invoke_rule_violations(
        self,
        *,
        forum: FilingForum,
        profile_id: str,
        intake_results: list[DocumentIntakeResult],
        page_ranges: tuple[tuple[int, int], ...],
        assembly_violations: tuple[DocumentCompilationViolation, ...],
    ) -> list[DocumentRuleViolation]:
        evaluator = self._evaluate_rule_violations
        all_kwargs = {
            "forum": forum.value,
            "profile_id": profile_id,
            "intake_results": intake_results,
            "page_ranges": page_ranges,
            "assembly_violations": assembly_violations,
        }
        try:
            parameters = inspect.signature(evaluator).parameters.values()
        except (TypeError, ValueError):
            return evaluator(
                profile_id=profile_id,
                intake_results=intake_results,
                page_ranges=page_ranges,
                assembly_violations=assembly_violations,
            )

        accepts_kwargs = any(parameter.kind == inspect.Parameter.VAR_KEYWORD for parameter in parameters)
        if accepts_kwargs:
            return evaluator(**all_kwargs)

        supported_names = {
            parameter.name
            for parameter in parameters
            if parameter.kind
            in {
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
                inspect.Parameter.KEYWORD_ONLY,
            }
        }
        evaluator_kwargs = {name: value for name, value in all_kwargs.items() if name in supported_names}
        return evaluator(**evaluator_kwargs)

    @staticmethod
    def _compiled_pdf_enabled() -> bool:
        raw_value = os.getenv("IMMCAD_ENABLE_COMPILED_PDF", "")
        return raw_value.strip().lower() in _COMPILED_PDF_ENABLED_VALUES

    @staticmethod
    def _normalize_source_files(
        source_files: list[StoredSourceFile] | tuple[StoredSourceFile, ...] | None,
    ) -> tuple[StoredSourceFile, ...]:
        if not source_files:
            return ()
        normalized_files: list[StoredSourceFile] = []
        for item in source_files:
            if isinstance(item, dict):
                file_id = str(item.get("file_id", "")).strip()
                filename = str(item.get("filename", "")).strip()
                raw_payload = item.get("payload_bytes")
            else:
                file_id = str(getattr(item, "file_id", "")).strip()
                filename = str(getattr(item, "filename", "")).strip()
                raw_payload = getattr(item, "payload_bytes", b"")
            if isinstance(raw_payload, memoryview):
                payload_bytes = raw_payload.tobytes()
            elif isinstance(raw_payload, bytearray):
                payload_bytes = bytes(raw_payload)
            elif isinstance(raw_payload, bytes):
                payload_bytes = raw_payload
            else:
                continue
            if not file_id or not filename:
                continue
            normalized_files.append(
                StoredSourceFile(
                    file_id=file_id,
                    filename=filename,
                    payload_bytes=payload_bytes,
                )
            )
        return tuple(normalized_files)

    @staticmethod
    def _inferred_filetype(filename: str) -> str | None:
        normalized_filename = filename.strip().lower()
        if normalized_filename.endswith(".pdf"):
            return "pdf"
        if normalized_filename.endswith(".png"):
            return "png"
        if normalized_filename.endswith(".jpg") or normalized_filename.endswith(".jpeg"):
            return "jpeg"
        if normalized_filename.endswith(".tif") or normalized_filename.endswith(".tiff"):
            return "tiff"
        return None

    @classmethod
    def _open_source_as_pdf_document(cls, source_file: StoredSourceFile):
        if fitz is None:
            raise ValueError("compiled_pdf_runtime_unavailable")
        payload_bytes = source_file.payload_bytes
        if not payload_bytes:
            raise ValueError("source file payload is empty")
        try:
            pdf_document = fitz.open(stream=payload_bytes, filetype="pdf")
            if pdf_document.page_count > 0 and bool(getattr(pdf_document, "is_pdf", False)):
                return pdf_document
            pdf_document.close()
        except Exception:
            pass

        inferred_filetype = cls._inferred_filetype(source_file.filename)
        if inferred_filetype is None or inferred_filetype == "pdf":
            raise ValueError("source file is not a readable PDF payload")

        image_document = fitz.open(stream=payload_bytes, filetype=inferred_filetype)
        try:
            converted_pdf_bytes = image_document.convert_to_pdf()
        finally:
            image_document.close()
        converted_pdf_document = fitz.open(stream=converted_pdf_bytes, filetype="pdf")
        if converted_pdf_document.page_count > 0:
            return converted_pdf_document
        converted_pdf_document.close()
        raise ValueError("source file did not produce a readable PDF payload")

    @staticmethod
    def _compiled_filename(matter_id: str) -> str:
        normalized_matter_id = matter_id.strip()
        safe_matter_id = "".join(
            ch if ch.isalnum() or ch in {"-", "_"} else "-"
            for ch in normalized_matter_id
        )
        safe_matter_id = safe_matter_id.strip("-_") or "matter"
        return f"{safe_matter_id}-compiled-binder.pdf"

    @staticmethod
    def _bookmark_title_for_entry(entry) -> str:
        document_type_label = entry.document_type.replace("_", " ")
        return f"{entry.position}. {entry.filename} ({document_type_label})"

    @classmethod
    def _bookmark_spec_for_plan(
        cls,
        *,
        assembly_plan: DocumentAssemblyPlan,
    ) -> list[list[object]]:
        return [
            [
                1,
                cls._bookmark_title_for_entry(entry),
                max(1, int(entry.start_page)),
            ]
            for entry in assembly_plan.table_of_contents
        ]

    @staticmethod
    def _apply_page_stamps(*, merged_pdf) -> None:
        page_count = merged_pdf.page_count
        for page_index in range(page_count):
            page = merged_pdf.load_page(page_index)
            page_rect = page.rect
            stamp_text = f"IMMCAD page {page_index + 1} of {page_count}"
            stamp_x = max(24, page_rect.width - 160)
            stamp_y = max(24, page_rect.height - 18)
            page.insert_text(
                (stamp_x, stamp_y),
                stamp_text,
                fontsize=8,
                color=(0.25, 0.25, 0.25),
                overlay=True,
            )

    @classmethod
    def _validate_compiled_pdf_document(
        cls,
        *,
        merged_pdf,
        assembly_plan: DocumentAssemblyPlan,
    ) -> bool:
        expected_page_count = len(assembly_plan.page_map)
        if expected_page_count < 1 or merged_pdf.page_count != expected_page_count:
            return False

        if assembly_plan.table_of_contents:
            if assembly_plan.table_of_contents[-1].end_page != merged_pdf.page_count:
                return False
            actual_toc = merged_pdf.get_toc(simple=True)
            expected_toc = cls._bookmark_spec_for_plan(assembly_plan=assembly_plan)
            if len(actual_toc) != len(expected_toc):
                return False
            for actual, expected in zip(actual_toc, expected_toc, strict=False):
                actual_level, actual_title, actual_page = actual
                expected_level, expected_title, expected_page = expected
                if (
                    int(actual_level) != int(expected_level)
                    or str(actual_title) != str(expected_title)
                    or int(actual_page) != int(expected_page)
                ):
                    return False
        return True

    def _ordered_source_files_for_assembly_plan(
        self,
        *,
        assembly_plan: DocumentAssemblyPlan,
        source_files: list[StoredSourceFile] | tuple[StoredSourceFile, ...] | None,
    ) -> tuple[StoredSourceFile, ...]:
        normalized_source_files = self._normalize_source_files(source_files)
        if not normalized_source_files:
            return ()

        source_files_by_id = {
            source_file.file_id: source_file for source_file in normalized_source_files
        }
        ordered_source_files: list[StoredSourceFile] = []
        for toc_entry in assembly_plan.table_of_contents:
            source_file = source_files_by_id.get(toc_entry.document_id)
            if source_file is None:
                return ()
            ordered_source_files.append(source_file)
        return tuple(ordered_source_files)

    def _build_compiled_pdf_payload(
        self,
        *,
        assembly_plan: DocumentAssemblyPlan,
        source_files: list[StoredSourceFile] | tuple[StoredSourceFile, ...] | None,
    ) -> tuple[bytes, int] | None:
        if not self._compiled_pdf_enabled() or fitz is None:
            return None

        ordered_source_files = self._ordered_source_files_for_assembly_plan(
            assembly_plan=assembly_plan,
            source_files=source_files,
        )
        if not ordered_source_files:
            return None

        try:
            merged_pdf = fitz.open()
            try:
                for source_file in ordered_source_files:
                    source_pdf = self._open_source_as_pdf_document(source_file)
                    try:
                        merged_pdf.insert_pdf(source_pdf)
                    finally:
                        source_pdf.close()
                bookmark_spec = self._bookmark_spec_for_plan(assembly_plan=assembly_plan)
                if bookmark_spec:
                    merged_pdf.set_toc(bookmark_spec)
                self._apply_page_stamps(merged_pdf=merged_pdf)
                page_count = merged_pdf.page_count
                if page_count < 1:
                    return None
                if not self._validate_compiled_pdf_document(
                    merged_pdf=merged_pdf,
                    assembly_plan=assembly_plan,
                ):
                    return None
                compiled_payload_bytes = merged_pdf.tobytes(garbage=4, deflate=True)
            finally:
                merged_pdf.close()
        except Exception:
            return None

        if not compiled_payload_bytes:
            return None
        return compiled_payload_bytes, page_count

    def _compiled_artifact_from_payload(
        self,
        *,
        matter_id: str,
        payload_bytes: bytes,
        page_count: int,
    ) -> DocumentCompiledArtifactMetadata:
        return DocumentCompiledArtifactMetadata(
            filename=self._compiled_filename(matter_id),
            byte_size=len(payload_bytes),
            sha256=hashlib.sha256(payload_bytes).hexdigest(),
            page_count=page_count,
        )

    def _build_compiled_artifact_metadata(
        self,
        *,
        matter_id: str,
        assembly_plan: DocumentAssemblyPlan,
        source_files: list[StoredSourceFile] | tuple[StoredSourceFile, ...] | None,
    ) -> DocumentCompiledArtifactMetadata | None:
        compiled_payload = self._build_compiled_pdf_payload(
            assembly_plan=assembly_plan,
            source_files=source_files,
        )
        if compiled_payload is None:
            return None
        payload_bytes, page_count = compiled_payload
        return self._compiled_artifact_from_payload(
            matter_id=matter_id,
            payload_bytes=payload_bytes,
            page_count=page_count,
        )

    def build_compiled_binder(
        self,
        *,
        matter_id: str,
        forum: str,
        compilation_profile_id: str | None = None,
        intake_results: list[DocumentIntakeResult],
        source_files: list[StoredSourceFile] | tuple[StoredSourceFile, ...] | None = None,
    ) -> tuple[DocumentPackageResponse, bytes] | None:
        package = self.build_package(
            matter_id=matter_id,
            forum=forum,
            compilation_profile_id=compilation_profile_id,
            intake_results=intake_results,
            source_files=source_files,
        )
        if (not package.is_ready) or package.compiled_artifact is None:
            return None

        parsed_forum = self._parse_forum(forum)
        profile_id = self._resolve_profile_id(
            forum=parsed_forum,
            requested_profile_id=compilation_profile_id,
        )
        profile = self._catalog.require_profile(profile_id)
        metadata = [
            AssemblyDocumentMetadata(
                document_id=result.file_id,
                document_type=result.classification.strip().lower(),
                filename=result.normalized_filename,
                page_count=self._resolved_page_count(result),
            )
            for result in intake_results
            if result.classification.strip()
        ]
        assembly_plan = self._assembly_service.plan_assembly(
            profile_id=profile.profile_id,
            documents=metadata,
        )
        compiled_payload = self._build_compiled_pdf_payload(
            assembly_plan=assembly_plan,
            source_files=source_files,
        )
        if compiled_payload is None:
            return None
        payload_bytes, page_count = compiled_payload

        actual_metadata = self._compiled_artifact_from_payload(
            matter_id=matter_id,
            payload_bytes=payload_bytes,
            page_count=page_count,
        )
        return (
            package.model_copy(
                update={
                    "compiled_artifact": actual_metadata,
                    "compilation_output_mode": "compiled_pdf",
                }
            ),
            payload_bytes,
        )

    def build_package(
        self,
        *,
        matter_id: str,
        forum: str,
        compilation_profile_id: str | None = None,
        intake_results: list[DocumentIntakeResult],
        source_files: list[StoredSourceFile] | tuple[StoredSourceFile, ...] | None = None,
        additional_blocking_issues: tuple[str, ...] | list[str] | None = None,
    ) -> DocumentPackageResponse:
        parsed_forum = self._parse_forum(forum)
        profile_id = self._resolve_profile_id(
            forum=parsed_forum,
            requested_profile_id=compilation_profile_id,
        )
        profile = self._catalog.require_profile(profile_id)
        classified_doc_types = {
            result.classification.strip().lower()
            for result in intake_results
            if result.classification.strip()
        }
        blocking_issues = self._collect_blocking_issues(intake_results)
        if additional_blocking_issues:
            blocking_issues = tuple(
                sorted(
                    {
                        *blocking_issues,
                        *{
                            str(issue).strip().lower()
                            for issue in additional_blocking_issues
                            if str(issue).strip()
                        },
                    }
                )
            )
        readiness = self._evaluate_readiness_for_profile(
            profile=profile,
            classified_doc_types=classified_doc_types,
            blocking_issues=blocking_issues,
        )
        metadata = [
            AssemblyDocumentMetadata(
                document_id=result.file_id,
                document_type=result.classification.strip().lower(),
                filename=result.normalized_filename,
                page_count=self._resolved_page_count(result),
            )
            for result in intake_results
            if result.classification.strip()
        ]
        assembly_plan = self._assembly_service.plan_assembly(profile_id=profile.profile_id, documents=metadata)

        toc_entries = [
            DocumentTableOfContentsEntry(
                position=entry.position,
                document_type=entry.document_type,
                filename=entry.filename,
                start_page=entry.start_page,
                end_page=entry.end_page,
            )
            for entry in assembly_plan.table_of_contents
        ]
        pagination_summary = self._build_pagination_summary(toc_entries)
        page_ranges = tuple(
            (entry.start_page or 1, entry.end_page or entry.start_page or 1)
            for entry in toc_entries
        )
        disclosure_checklist = self._build_checklist(
            forum=parsed_forum,
            classified_doc_types=classified_doc_types,
        )
        record_sections = self._hydrate_record_sections(
            self._build_record_sections(
                profile=profile,
                classified_doc_types=classified_doc_types,
            )
        )
        rule_violations = self._sort_rule_violations(
            self._invoke_rule_violations(
                forum=parsed_forum,
                profile_id=profile.profile_id,
                intake_results=intake_results,
                page_ranges=page_ranges,
                assembly_violations=assembly_plan.violations,
            )
        )
        blocking_rule_codes = tuple(
            violation.violation_code for violation in rule_violations if violation.severity == "blocking"
        )
        merged_blocking_issues = tuple(sorted({*readiness.blocking_issues, *blocking_rule_codes}))
        cover_letter_draft = self._build_cover_letter_draft(
            forum=parsed_forum,
            matter_id=matter_id,
            missing_required_items=readiness.missing_required_items,
            blocking_issues=merged_blocking_issues,
        )
        compiled_artifact = self._build_compiled_artifact_metadata(
            matter_id=matter_id,
            assembly_plan=assembly_plan,
            source_files=source_files,
        )
        compilation_output_mode = (
            "compiled_pdf" if compiled_artifact is not None else "metadata_plan_only"
        )
        return DocumentPackageResponse(
            matter_id=matter_id,
            forum=parsed_forum.value,
            is_ready=readiness.is_ready and not blocking_rule_codes,
            table_of_contents=toc_entries,
            disclosure_checklist=disclosure_checklist,
            cover_letter_draft=cover_letter_draft,
            toc_entries=toc_entries,
            pagination_summary=pagination_summary,
            rule_violations=rule_violations,
            compilation_profile=DocumentCompilationProfile(
                id=assembly_plan.profile_id,
                version=assembly_plan.catalog_version,
            ),
            compilation_output_mode=compilation_output_mode,
            compiled_artifact=compiled_artifact,
            record_sections=record_sections,
        )


__all__ = ["DocumentPackageService"]
