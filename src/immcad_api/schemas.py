from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl


Confidence = Literal["low", "medium", "high"]
FallbackReason = Literal["timeout", "rate_limit", "policy_block", "provider_error"]
ChatLocale = Literal["en-CA", "fr-CA"]
ChatMode = Literal["standard"]


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


class ChatResponse(BaseModel):
    answer: str
    citations: list[Citation]
    confidence: Confidence
    disclaimer: str
    fallback_used: FallbackUsed


class CaseSearchRequest(BaseModel):
    query: str = Field(min_length=2, max_length=300)
    jurisdiction: str = Field(default="ca", max_length=16)
    court: str | None = Field(default=None, max_length=32)
    limit: int = Field(default=10, ge=1, le=25)


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
    limit: int = Field(default=10, ge=1, le=25)


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
