from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl, field_validator, model_validator


Confidence = Literal["low", "medium", "high"]
FallbackReason = Literal[
    "timeout",
    "rate_limit",
    "policy_block",
    "provider_error",
    "insufficient_context",
]
ChatLocale = Literal["en-CA", "fr-CA"]
ChatMode = Literal["standard"]
SourceEventType = Literal["new", "updated", "translated", "corrected"]
SourceFreshnessStatus = Literal["fresh", "stale", "missing", "unknown"]
ResearchObjective = Literal[
    "support_precedent",
    "distinguish_precedent",
    "background_research",
]
ResearchPosture = Literal["judicial_review", "appeal", "motion", "application"]
DocumentForum = Literal[
    "federal_court_jr", "rpd", "rad", "iad", "id", "ircc_application"
]
DocumentCompilationProfileId = Literal[
    "federal_court_jr_leave",
    "federal_court_jr_hearing",
    "rpd",
    "rad",
    "id",
    "iad",
    "iad_sponsorship",
    "iad_residency",
    "iad_admissibility",
    "ircc_pr_card_renewal",
]
DocumentQualityStatus = Literal["processed", "needs_review", "failed"]
DocumentChecklistStatus = Literal["present", "missing", "warning"]
DocumentRuleScope = Literal["base", "conditional"]
DocumentViolationSeverity = Literal["warning", "blocking"]
DocumentCompilationOutputMode = Literal["metadata_plan_only", "compiled_pdf"]
DocumentSubmissionChannel = Literal["portal", "email", "fax", "mail", "in_person"]


class ChatRequest(BaseModel):
    session_id: str = Field(min_length=8, max_length=128)
    message: str = Field(min_length=1, max_length=8000)
    locale: ChatLocale = "en-CA"
    mode: ChatMode = "standard"


class Citation(BaseModel):
    source_id: str
    title: str
    url: str
    pin: str
    snippet: str


class FallbackUsed(BaseModel):
    used: bool
    provider: str | None = None
    reason: FallbackReason | None = None


class ChatResearchPreview(BaseModel):
    retrieval_mode: Literal["auto", "manual"]
    query: str
    source_status: dict[str, str]
    cases: list[LawyerCaseSupport]


class ChatResponse(BaseModel):
    answer: str
    citations: list[Citation]
    confidence: Confidence
    disclaimer: str
    fallback_used: FallbackUsed
    research_preview: ChatResearchPreview | None = None


class CaseSearchRequest(BaseModel):
    query: str = Field(min_length=2, max_length=300)
    jurisdiction: str = Field(default="ca", max_length=16)
    court: str | None = Field(default=None, max_length=32)
    decision_date_from: date | None = None
    decision_date_to: date | None = None
    limit: int = Field(default=10, ge=1, le=25)

    @model_validator(mode="after")
    def _validate_decision_date_range(self):
        if (
            self.decision_date_from is not None
            and self.decision_date_to is not None
            and self.decision_date_from > self.decision_date_to
        ):
            raise ValueError("decision_date_from must be <= decision_date_to")
        return self


class CaseSearchResult(BaseModel):
    case_id: str
    title: str
    citation: str
    decision_date: date
    url: str
    source_id: str | None = None
    document_url: str | None = None
    docket_numbers: list[str] | None = None
    source_event_type: SourceEventType | None = None
    export_allowed: bool | None = None
    export_policy_reason: str | None = None


class CaseSearchResponse(BaseModel):
    results: list[CaseSearchResult]


class SourceTransparencyCheckpoint(BaseModel):
    path: str
    exists: bool
    updated_at: str | None = None


class CaseLawSourceTransparencyItem(BaseModel):
    source_id: str
    court: str | None = None
    instrument: str
    url: str
    update_cadence: str
    source_class: str | None = None
    production_ingest_allowed: bool | None = None
    answer_citation_allowed: bool | None = None
    export_fulltext_allowed: bool | None = None
    last_success_at: str | None = None
    last_http_status: int | None = None
    freshness_seconds: int | None = None
    freshness_status: SourceFreshnessStatus


class SourceTransparencyResponse(BaseModel):
    jurisdiction: str
    registry_version: str
    generated_at: str
    supported_courts: list[str]
    checkpoint: SourceTransparencyCheckpoint
    case_law_sources: list[CaseLawSourceTransparencyItem]


class LawyerCaseResearchRequest(BaseModel):
    session_id: str = Field(min_length=8, max_length=128)
    matter_summary: str = Field(min_length=10, max_length=12000)
    jurisdiction: str = Field(default="ca", max_length=16)
    court: str | None = Field(default=None, max_length=32)
    intake: LawyerResearchIntake | None = None
    limit: int = Field(default=10, ge=1, le=25)


class LawyerResearchIntake(BaseModel):
    objective: ResearchObjective | None = None
    target_court: str | None = Field(default=None, max_length=32)
    procedural_posture: ResearchPosture | None = None
    issue_tags: list[str] = Field(default_factory=list)
    anchor_citations: list[str] = Field(default_factory=list)
    anchor_dockets: list[str] = Field(default_factory=list)
    fact_keywords: list[str] = Field(default_factory=list)
    date_from: date | None = None
    date_to: date | None = None

    @field_validator(
        "issue_tags",
        "anchor_citations",
        "anchor_dockets",
        "fact_keywords",
        mode="before",
    )
    @classmethod
    def _normalize_list_values(cls, value) -> list[str]:
        if value is None:
            return []
        if not isinstance(value, list):
            raise TypeError("intake list fields must be arrays of strings")
        normalized: list[str] = []
        seen: set[str] = set()
        for raw_item in value:
            if not isinstance(raw_item, str):
                continue
            item = raw_item.strip()
            if not item:
                continue
            dedupe_key = item.lower()
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            normalized.append(item[:120])
        return normalized[:12]

    @model_validator(mode="after")
    def _validate_date_range(self):
        if self.date_from and self.date_to and self.date_from > self.date_to:
            raise ValueError("intake date_from must be <= intake date_to")
        return self


class LawyerCaseSupport(BaseModel):
    case_id: str
    title: str
    citation: str
    source_id: str | None = None
    court: str | None = None
    decision_date: date
    url: str
    document_url: str | None = None
    docket_numbers: list[str] | None = None
    source_event_type: SourceEventType | None = None
    pdf_status: Literal["available", "unavailable"]
    pdf_reason: str | None = None
    export_allowed: bool | None = None
    export_policy_reason: str | None = None
    relevance_reason: str
    summary: str | None = None


class LawyerCaseResearchResponse(BaseModel):
    matter_profile: dict[str, list[str] | str | None]
    cases: list[LawyerCaseSupport]
    source_status: dict[str, str]
    priority_source_status: dict[str, SourceFreshnessStatus] = Field(default_factory=dict)
    research_confidence: Confidence = "low"
    confidence_reasons: list[str] = Field(default_factory=list)
    intake_completeness: Confidence = "low"
    intake_hints: list[str] = Field(default_factory=list)


class CaseExportRequest(BaseModel):
    source_id: str = Field(min_length=2, max_length=128)
    case_id: str = Field(min_length=1, max_length=256)
    document_url: HttpUrl
    format: Literal["pdf"] = "pdf"
    user_approved: bool = False
    approval_token: str | None = Field(default=None, min_length=16, max_length=4096)


class CaseExportResponse(BaseModel):
    source_id: str
    case_id: str
    format: Literal["pdf"]
    export_allowed: bool
    policy_reason: str | None = None


class CaseExportApprovalRequest(BaseModel):
    source_id: str = Field(min_length=2, max_length=128)
    case_id: str = Field(min_length=1, max_length=256)
    document_url: HttpUrl
    user_approved: bool = False


class CaseExportApprovalResponse(BaseModel):
    approval_token: str
    expires_at_epoch: int = Field(ge=1)


class DocumentIntakeInitRequest(BaseModel):
    forum: DocumentForum
    matter_id: str | None = Field(default=None, min_length=3, max_length=128)
    compilation_profile_id: DocumentCompilationProfileId | None = None
    client_reference: str | None = Field(default=None, min_length=1, max_length=128)
    submission_channel: DocumentSubmissionChannel = "portal"
    decision_date: date | None = None
    hearing_date: date | None = None
    service_date: date | None = None
    filing_date: date | None = None
    deadline_override_reason: str | None = Field(
        default=None, min_length=1, max_length=500
    )
    language: ChatLocale = "en-CA"

    @field_validator("deadline_override_reason", mode="before")
    @classmethod
    def _normalize_deadline_override_reason(cls, value):
        if value is None:
            return None
        if not isinstance(value, str):
            raise TypeError("deadline_override_reason must be a string when provided")
        normalized = value.strip()
        if not normalized:
            raise ValueError("deadline_override_reason cannot be blank")
        return normalized

    @model_validator(mode="after")
    def _validate_deadline_dates(self):
        if (
            self.service_date is not None
            and self.hearing_date is not None
            and self.service_date > self.hearing_date
        ):
            raise ValueError("service_date must be <= hearing_date")
        return self


class DocumentIssue(BaseModel):
    code: str = Field(min_length=1, max_length=128)
    message: str | None = Field(default=None, max_length=500)
    severity: Literal["warning", "blocking", "error"] = "warning"
    remediation: str | None = Field(default=None, max_length=500)


class DocumentPageCharCount(BaseModel):
    page_number: int = Field(ge=1)
    extracted_char_count: int = Field(default=0, ge=0)


class DocumentClassificationCandidate(BaseModel):
    classification: str = Field(min_length=1, max_length=128)
    score: float = Field(ge=0.0, le=1.0)


class DocumentIntakeResult(BaseModel):
    file_id: str = Field(min_length=3, max_length=128)
    original_filename: str = Field(min_length=1, max_length=260)
    normalized_filename: str = Field(min_length=1, max_length=260)
    classification: str = Field(min_length=1, max_length=128)
    classification_confidence: Confidence | None = None
    classification_candidates: list[DocumentClassificationCandidate] = Field(
        default_factory=list
    )
    quality_status: DocumentQualityStatus
    issues: list[str] = Field(default_factory=list)
    issue_details: list[DocumentIssue] = Field(default_factory=list)
    used_ocr: bool = False
    total_pages: int = Field(default=0, ge=0)
    page_char_counts: list[DocumentPageCharCount] = Field(default_factory=list)
    file_hash: str | None = Field(default=None, min_length=8, max_length=128)
    ocr_confidence_class: Confidence | None = None
    ocr_capability: str | None = Field(default=None, max_length=128)


class DocumentIntakeResponse(BaseModel):
    matter_id: str = Field(min_length=3, max_length=128)
    forum: DocumentForum
    compilation_profile_id: DocumentCompilationProfileId | None = None
    results: list[DocumentIntakeResult]
    blocking_issues: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class DocumentClassificationOverrideRequest(BaseModel):
    file_id: str = Field(min_length=1, max_length=128)
    classification: str = Field(min_length=1, max_length=128)


class DocumentRequirementStatus(BaseModel):
    item: str = Field(min_length=1, max_length=128)
    status: DocumentChecklistStatus
    rule_scope: DocumentRuleScope = "base"
    reason: str | None = Field(default=None, max_length=500)


class DocumentRecordSectionSlotStatus(BaseModel):
    document_type: str = Field(min_length=1, max_length=128)
    status: DocumentChecklistStatus
    rule_scope: DocumentRuleScope = "base"
    reason: str | None = Field(default=None, max_length=500)


class DocumentRecordSection(BaseModel):
    section_id: str = Field(min_length=1, max_length=128)
    title: str = Field(min_length=1, max_length=260)
    instructions: str = Field(min_length=1, max_length=4000)
    document_types: list[str] = Field(default_factory=list)
    section_status: DocumentChecklistStatus = "present"
    slot_statuses: list[DocumentRecordSectionSlotStatus] = Field(default_factory=list)
    missing_document_types: list[str] = Field(default_factory=list)
    missing_reasons: list[str] = Field(default_factory=list)


class DocumentCompiledArtifactMetadata(BaseModel):
    filename: str = Field(min_length=1, max_length=260)
    byte_size: int = Field(ge=0)
    sha256: str = Field(min_length=64, max_length=64)
    page_count: int = Field(ge=0)


class DocumentReadinessResponse(BaseModel):
    matter_id: str = Field(min_length=3, max_length=128)
    forum: DocumentForum
    is_ready: bool
    missing_required_items: list[str] = Field(default_factory=list)
    blocking_issues: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    requirement_statuses: list[DocumentRequirementStatus] = Field(default_factory=list)
    toc_entries: list[DocumentTableOfContentsEntry] = Field(default_factory=list)
    pagination_summary: DocumentPaginationSummary = Field(
        default_factory=lambda: DocumentPaginationSummary()
    )
    rule_violations: list[DocumentRuleViolation] = Field(default_factory=list)
    compilation_profile: DocumentCompilationProfile = Field(
        default_factory=lambda: DocumentCompilationProfile()
    )
    compilation_output_mode: DocumentCompilationOutputMode = "metadata_plan_only"
    compiled_artifact: DocumentCompiledArtifactMetadata | None = None
    record_sections: list[DocumentRecordSection] = Field(default_factory=list)


class DocumentTableOfContentsEntry(BaseModel):
    position: int = Field(ge=1)
    document_type: str = Field(min_length=1, max_length=128)
    filename: str = Field(min_length=1, max_length=260)
    start_page: int | None = Field(default=None, ge=1)
    end_page: int | None = Field(default=None, ge=1)


class DocumentDisclosureChecklistEntry(BaseModel):
    item: str = Field(min_length=1, max_length=128)
    status: DocumentChecklistStatus
    rule_scope: DocumentRuleScope = "base"
    reason: str | None = Field(default=None, max_length=500)


class DocumentPaginationSummary(BaseModel):
    total_documents: int = Field(default=0, ge=0)
    total_pages: int = Field(default=0, ge=0)
    last_assigned_page: int = Field(default=0, ge=0)


class DocumentRuleViolation(BaseModel):
    violation_code: str = Field(min_length=1, max_length=128)
    severity: DocumentViolationSeverity = "warning"
    message: str | None = Field(default=None, max_length=500)
    rule_id: str | None = Field(default=None, max_length=128)
    rule_source_url: str = Field(min_length=1, max_length=2048)
    remediation: str | None = Field(default=None, max_length=500)


class DocumentCompilationProfile(BaseModel):
    id: str = Field(default="legacy-intake-compat", min_length=1, max_length=128)
    version: str = Field(default="1.0", min_length=1, max_length=64)


class DocumentPackageResponse(BaseModel):
    matter_id: str = Field(min_length=3, max_length=128)
    forum: DocumentForum
    is_ready: bool
    table_of_contents: list[DocumentTableOfContentsEntry] = Field(default_factory=list)
    disclosure_checklist: list[DocumentDisclosureChecklistEntry] = Field(
        default_factory=list
    )
    cover_letter_draft: str = Field(default="", max_length=24000)
    toc_entries: list[DocumentTableOfContentsEntry] = Field(default_factory=list)
    pagination_summary: DocumentPaginationSummary = Field(
        default_factory=lambda: DocumentPaginationSummary()
    )
    rule_violations: list[DocumentRuleViolation] = Field(default_factory=list)
    compilation_profile: DocumentCompilationProfile = Field(
        default_factory=lambda: DocumentCompilationProfile()
    )
    compilation_output_mode: DocumentCompilationOutputMode = "metadata_plan_only"
    compiled_artifact: DocumentCompiledArtifactMetadata | None = None
    record_sections: list[DocumentRecordSection] = Field(default_factory=list)


class ErrorBody(BaseModel):
    code: Literal[
        "VALIDATION_ERROR",
        "PROVIDER_ERROR",
        "SOURCE_UNAVAILABLE",
        "POLICY_BLOCKED",
        "RATE_LIMITED",
        "UNAUTHORIZED",
    ]
    message: str
    trace_id: str
    policy_reason: str | None = None


class ErrorEnvelope(BaseModel):
    error: ErrorBody


ChatResearchPreview.model_rebuild()
ChatResponse.model_rebuild()
DocumentReadinessResponse.model_rebuild()
DocumentPackageResponse.model_rebuild()
