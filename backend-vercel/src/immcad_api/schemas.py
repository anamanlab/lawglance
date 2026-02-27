from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl, field_validator, model_validator


Confidence = Literal["low", "medium", "high"]
FallbackReason = Literal["timeout", "rate_limit", "policy_block", "provider_error"]
ChatLocale = Literal["en-CA", "fr-CA"]
ChatMode = Literal["standard"]
ResearchObjective = Literal[
    "support_precedent",
    "distinguish_precedent",
    "background_research",
]
ResearchPosture = Literal["judicial_review", "appeal", "motion", "application"]
DocumentForum = Literal["federal_court_jr", "rpd", "rad", "iad", "id"]
DocumentQualityStatus = Literal["processed", "needs_review", "failed"]
DocumentChecklistStatus = Literal["present", "missing", "warning"]
DocumentRuleScope = Literal["base", "conditional"]


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
    export_allowed: bool | None = None
    export_policy_reason: str | None = None


class CaseSearchResponse(BaseModel):
    results: list[CaseSearchResult]


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
    client_reference: str | None = Field(default=None, min_length=1, max_length=128)
    language: ChatLocale = "en-CA"


class DocumentIssue(BaseModel):
    code: str = Field(min_length=1, max_length=128)
    message: str | None = Field(default=None, max_length=500)
    severity: Literal["warning", "blocking", "error"] = "warning"


class DocumentIntakeResult(BaseModel):
    file_id: str = Field(min_length=3, max_length=128)
    original_filename: str = Field(min_length=1, max_length=260)
    normalized_filename: str = Field(min_length=1, max_length=260)
    classification: str = Field(min_length=1, max_length=128)
    quality_status: DocumentQualityStatus
    issues: list[str] = Field(default_factory=list)
    used_ocr: bool = False


class DocumentIntakeResponse(BaseModel):
    matter_id: str = Field(min_length=3, max_length=128)
    forum: DocumentForum
    results: list[DocumentIntakeResult]
    blocking_issues: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class DocumentRequirementStatus(BaseModel):
    item: str = Field(min_length=1, max_length=128)
    status: DocumentChecklistStatus
    rule_scope: DocumentRuleScope = "base"
    reason: str | None = Field(default=None, max_length=500)


class DocumentReadinessResponse(BaseModel):
    matter_id: str = Field(min_length=3, max_length=128)
    forum: DocumentForum
    is_ready: bool
    missing_required_items: list[str] = Field(default_factory=list)
    blocking_issues: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    requirement_statuses: list[DocumentRequirementStatus] = Field(default_factory=list)


class DocumentTableOfContentsEntry(BaseModel):
    position: int = Field(ge=1)
    document_type: str = Field(min_length=1, max_length=128)
    filename: str = Field(min_length=1, max_length=260)


class DocumentDisclosureChecklistEntry(BaseModel):
    item: str = Field(min_length=1, max_length=128)
    status: DocumentChecklistStatus
    rule_scope: DocumentRuleScope = "base"
    reason: str | None = Field(default=None, max_length=500)


class DocumentPackageResponse(BaseModel):
    matter_id: str = Field(min_length=3, max_length=128)
    forum: DocumentForum
    is_ready: bool
    table_of_contents: list[DocumentTableOfContentsEntry] = Field(default_factory=list)
    disclosure_checklist: list[DocumentDisclosureChecklistEntry] = Field(default_factory=list)
    cover_letter_draft: str = Field(default="", max_length=24000)


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
