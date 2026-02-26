from __future__ import annotations

from datetime import date

import pytest
from pydantic import ValidationError

from immcad_api.schemas import (
    LawyerCaseResearchRequest,
    LawyerCaseResearchResponse,
    LawyerResearchIntake,
    LawyerCaseSupport,
)


def test_lawyer_case_research_request_accepts_valid_payload() -> None:
    payload = LawyerCaseResearchRequest(
        session_id="session-123456",
        matter_summary="Appeal based on procedural fairness in FC immigration decision",
        jurisdiction="ca",
        intake=LawyerResearchIntake(
            objective="support_precedent",
            target_court="fc",
            procedural_posture="appeal",
            issue_tags=["procedural_fairness", "inadmissibility"],
            anchor_citations=["2024 FC 101"],
            fact_keywords=["detention", "credibility"],
        ),
        limit=5,
    )

    assert payload.limit == 5
    assert payload.jurisdiction == "ca"
    assert payload.intake is not None
    assert payload.intake.target_court == "fc"


def test_lawyer_case_support_enforces_pdf_status_literal() -> None:
    with pytest.raises(ValidationError):
        LawyerCaseSupport(
            case_id="2026-FC-101",
            title="Example v Canada",
            citation="2026 FC 101",
            court="FC",
            decision_date=date(2026, 2, 1),
            url="https://decisions.fct-cf.gc.ca/fc-cf/decisions/en/item/101/index.do",
            document_url="https://decisions.fct-cf.gc.ca/fc-cf/decisions/en/101/1/document.do",
            pdf_status="unknown",
            relevance_reason="Procedural fairness in immigration judicial review.",
        )


def test_lawyer_research_intake_rejects_invalid_date_range() -> None:
    with pytest.raises(ValidationError):
        LawyerResearchIntake(
            date_from=date(2026, 2, 10),
            date_to=date(2026, 1, 1),
        )


def test_lawyer_case_research_response_accepts_structured_payload() -> None:
    response = LawyerCaseResearchResponse(
        matter_profile={
            "issue_tags": ["procedural_fairness", "inadmissibility"],
            "target_court": "fc",
            "procedural_posture": "appeal",
        },
        cases=[
            LawyerCaseSupport(
                case_id="2026-FC-101",
                title="Example v Canada",
                citation="2026 FC 101",
                court="FC",
                decision_date=date(2026, 2, 1),
                url="https://decisions.fct-cf.gc.ca/fc-cf/decisions/en/item/101/index.do",
                document_url="https://decisions.fct-cf.gc.ca/fc-cf/decisions/en/101/1/document.do",
                pdf_status="available",
                relevance_reason="Addresses procedural fairness where reasons were inadequate.",
                summary="The court set aside a refusal due to inadequate reasons.",
            )
        ],
        source_status={
            "official": "ok",
            "canlii": "not_used",
        },
        research_confidence="high",
        confidence_reasons=[
            "Official court sources returned aligned precedent results.",
            "Citation anchor matched at least one result.",
        ],
        intake_completeness="high",
        intake_hints=[],
    )

    assert response.cases[0].pdf_status == "available"
    assert response.source_status["official"] == "ok"
    assert response.research_confidence == "high"
    assert len(response.confidence_reasons) == 2
    assert response.intake_completeness == "high"
