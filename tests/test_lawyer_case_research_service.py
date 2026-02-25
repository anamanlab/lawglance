from __future__ import annotations

from datetime import date

from immcad_api.errors import SourceUnavailableError
from immcad_api.schemas import (
    CaseSearchRequest,
    CaseSearchResponse,
    CaseSearchResult,
    LawyerCaseResearchRequest,
)
from immcad_api.services.lawyer_case_research_service import LawyerCaseResearchService


class _MockCaseSearchService:
    def __init__(self, *, raise_unavailable: bool = False) -> None:
        self.raise_unavailable = raise_unavailable
        self.requests: list[CaseSearchRequest] = []

    def search(self, request: CaseSearchRequest) -> CaseSearchResponse:
        self.requests.append(request)
        if self.raise_unavailable:
            raise SourceUnavailableError("Case-law sources unavailable")

        shared_case = CaseSearchResult(
            case_id="2026-FC-101",
            title="Example v Canada",
            citation="2026 FC 101",
            decision_date=date(2026, 2, 1),
            url="https://decisions.fct-cf.gc.ca/fc-cf/decisions/en/item/101/index.do",
            source_id="FC_DECISIONS",
            document_url="https://decisions.fct-cf.gc.ca/fc-cf/decisions/en/101/1/document.do",
        )
        secondary_case = CaseSearchResult(
            case_id="2025-FCA-44",
            title="Another v Canada",
            citation="2025 FCA 44",
            decision_date=date(2025, 7, 10),
            url="https://decisions.fca-caf.gc.ca/fca-caf/decisions/en/item/44/index.do",
            source_id="FCA_DECISIONS",
            document_url="https://decisions.fca-caf.gc.ca/fca-caf/decisions/en/44/1/document.do",
        )
        if "precedent" in request.query.lower():
            return CaseSearchResponse(results=[shared_case, secondary_case])
        return CaseSearchResponse(results=[shared_case])


def _request(limit: int = 5) -> LawyerCaseResearchRequest:
    return LawyerCaseResearchRequest(
        session_id="session-123456",
        matter_summary="Federal Court appeal on procedural fairness and inadmissibility",
        jurisdiction="ca",
        court="fc",
        limit=limit,
    )


def test_orchestrator_merges_results_and_deduplicates() -> None:
    service = LawyerCaseResearchService(case_search_service=_MockCaseSearchService())

    response = service.research(_request())

    assert len(response.cases) == 2
    assert len({case.citation for case in response.cases}) == len(response.cases)
    assert all(case.relevance_reason for case in response.cases)


def test_orchestrator_respects_limit() -> None:
    service = LawyerCaseResearchService(case_search_service=_MockCaseSearchService())

    response = service.research(_request(limit=1))

    assert len(response.cases) == 1


def test_orchestrator_returns_structured_source_status_when_sources_unavailable() -> None:
    service = LawyerCaseResearchService(
        case_search_service=_MockCaseSearchService(raise_unavailable=True)
    )

    response = service.research(_request())

    assert response.cases == []
    assert response.source_status["official"] == "unavailable"
    assert response.source_status["canlii"] == "unavailable"
