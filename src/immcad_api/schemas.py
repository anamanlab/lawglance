from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field


Confidence = Literal["low", "medium", "high"]
FallbackReason = Literal["timeout", "rate_limit", "policy_block", "provider_error"]


class ChatRequest(BaseModel):
    session_id: str = Field(min_length=8, max_length=128)
    message: str = Field(min_length=1, max_length=8000)
    locale: str = Field(default="en-CA", max_length=16)
    mode: str = Field(default="standard", max_length=32)


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


class CaseSearchResponse(BaseModel):
    results: list[CaseSearchResult]


class SourceExportResponse(BaseModel):
    source_id: str
    export_allowed: bool
    policy_reason: str
    source_type: str
    instrument: str
    download_url: str
    registry_version: str
    jurisdiction: str
    status: Literal["ready", "not_implemented"]
    message: str


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


class ErrorEnvelope(BaseModel):
    error: ErrorBody
