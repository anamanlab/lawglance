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
from immcad_api.sources.source_registry import SourceRegistry, SourceRegistryEntry


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
    assert response.research_confidence == "low"
    assert response.confidence_reasons
    assert response.intake_completeness == "low"
    assert response.intake_hints


def test_orchestrator_marks_pdf_unavailable_when_source_metadata_not_loaded() -> None:
    service = LawyerCaseResearchService(case_search_service=_MockCaseSearchService())

    response = service.research(_request(limit=1))

    assert response.cases[0].pdf_status == "unavailable"
    assert response.cases[0].pdf_reason == "document_url_unverified_source"
    assert response.cases[0].export_allowed is None
    assert response.cases[0].export_policy_reason is None
    assert response.research_confidence in {"medium", "high"}
    assert response.confidence_reasons
    assert response.intake_completeness in {"low", "medium", "high"}
    assert response.intake_hints


def test_orchestrator_does_not_mark_unknown_sources_as_official() -> None:
    class _UnknownSourceCaseSearchService:
        def search(self, request: CaseSearchRequest) -> CaseSearchResponse:
            del request
            return CaseSearchResponse(
                results=[
                    CaseSearchResult(
                        case_id="UNK-1",
                        title="Unknown Source Decision",
                        citation="UNK 1",
                        decision_date=date(2025, 9, 1),
                        url="https://example.invalid/decisions/1",
                        source_id=None,
                        document_url="https://example.invalid/decisions/1/document.pdf",
                    )
                ]
            )

    service = LawyerCaseResearchService(case_search_service=_UnknownSourceCaseSearchService())
    response = service.research(_request(limit=1))

    assert response.cases
    assert response.source_status["official"] == "no_match"
    assert response.source_status["canlii"] == "not_used"


def test_orchestrator_uses_registry_for_official_source_classification() -> None:
    class _RegistryOfficialCaseSearchService:
        def search(self, request: CaseSearchRequest) -> CaseSearchResponse:
            del request
            return CaseSearchResponse(
                results=[
                    CaseSearchResult(
                        case_id="IRB-1",
                        title="Immigration Appeal Division Decision",
                        citation="IRB 2025 1",
                        decision_date=date(2025, 9, 2),
                        url="https://irb-cisr.gc.ca/decisions/1",
                        source_id="IRB_DECISIONS",
                        document_url="https://irb-cisr.gc.ca/decisions/1/document.pdf",
                    )
                ]
            )

    registry = SourceRegistry(
        version="2026-02-25",
        jurisdiction="ca",
        sources=[
            SourceRegistryEntry(
                source_id="IRB_DECISIONS",
                source_type="case_law",
                instrument="Immigration and Refugee Board Decisions",
                url="https://irb-cisr.gc.ca/decisions",
                update_cadence="daily",
            )
        ],
    )
    service = LawyerCaseResearchService(
        case_search_service=_RegistryOfficialCaseSearchService(),
        source_registry=registry,
    )
    response = service.research(_request(limit=1))

    assert response.cases
    assert response.source_status["official"] == "ok"
    assert response.source_status["canlii"] == "not_used"


def test_orchestrator_ranking_prioritizes_exact_citation_match_over_token_density() -> None:
    class _CitationRankingCaseSearchService:
        def search(self, request: CaseSearchRequest) -> CaseSearchResponse:
            del request
            return CaseSearchResponse(
                results=[
                    CaseSearchResult(
                        case_id="CIT-2024-101",
                        title="Reference decision",
                        citation="2024 FC 101",
                        decision_date=date(2024, 5, 1),
                        url="https://decisions.fct-cf.gc.ca/fc-cf/decisions/en/item/2024101/index.do",
                        source_id="FC_DECISIONS",
                        document_url="https://decisions.fct-cf.gc.ca/fc-cf/decisions/en/2024101/1/document.do",
                    ),
                    CaseSearchResult(
                        case_id="TOKEN-2026-999",
                        title="Inadmissibility precedent guidance decision",
                        citation="2026 FC 999",
                        decision_date=date(2026, 1, 15),
                        url="https://decisions.fct-cf.gc.ca/fc-cf/decisions/en/item/2026999/index.do",
                        source_id="FC_DECISIONS",
                        document_url="https://decisions.fct-cf.gc.ca/fc-cf/decisions/en/2026999/1/document.do",
                    ),
                ]
            )

    service = LawyerCaseResearchService(case_search_service=_CitationRankingCaseSearchService())
    request = LawyerCaseResearchRequest(
        session_id="session-123456",
        matter_summary="Need precedent guidance based on 2024 FC 101 inadmissibility decision",
        jurisdiction="ca",
        court="fc",
        limit=2,
    )

    response = service.research(request)

    assert response.cases
    assert response.cases[0].citation == "2024 FC 101"
    assert response.research_confidence in {"medium", "high"}
    assert response.intake_completeness in {"low", "medium", "high"}


def test_orchestrator_uses_structured_intake_for_anchor_confidence_reason() -> None:
    service = LawyerCaseResearchService(case_search_service=_MockCaseSearchService())
    request = LawyerCaseResearchRequest(
        session_id="session-123456",
        matter_summary="Need support precedent for inadmissibility in Federal Court",
        jurisdiction="ca",
        court="fc",
        intake={
            "objective": "support_precedent",
            "anchor_citations": ["2026 FC 101"],
            "issue_tags": ["inadmissibility"],
            "procedural_posture": "judicial_review",
        },
        limit=2,
    )

    response = service.research(request)

    assert response.cases
    assert response.research_confidence in {"medium", "high"}
    assert any("anchor" in reason.lower() for reason in response.confidence_reasons)
    assert response.intake_completeness in {"medium", "high"}
    assert not any("target court" in hint.lower() for hint in response.intake_hints)


def test_orchestrator_returns_missing_intake_hints_for_sparse_input() -> None:
    service = LawyerCaseResearchService(case_search_service=_MockCaseSearchService())
    request = LawyerCaseResearchRequest(
        session_id="session-123456",
        matter_summary="Need precedent support for procedural fairness",
        jurisdiction="ca",
        limit=2,
    )

    response = service.research(request)

    assert response.cases
    assert response.intake_completeness == "low"
    assert any("target court" in hint.lower() for hint in response.intake_hints)


def test_orchestrator_passes_intake_date_range_to_case_search_requests() -> None:
    search_service = _MockCaseSearchService()
    service = LawyerCaseResearchService(case_search_service=search_service)
    request = LawyerCaseResearchRequest(
        session_id="session-123456",
        matter_summary="Need precedent support for inadmissibility",
        jurisdiction="ca",
        intake={
            "target_court": "fc",
            "date_from": date(2024, 1, 1),
            "date_to": date(2025, 12, 31),
        },
        limit=2,
    )

    service.research(request)

    assert search_service.requests
    assert all(search_request.decision_date_from == date(2024, 1, 1) for search_request in search_service.requests)
    assert all(search_request.decision_date_to == date(2025, 12, 31) for search_request in search_service.requests)


def test_orchestrator_filters_results_outside_requested_intake_date_range() -> None:
    class _DateRangeCaseSearchService:
        def search(self, request: CaseSearchRequest) -> CaseSearchResponse:
            del request
            return CaseSearchResponse(
                results=[
                    CaseSearchResult(
                        case_id="old-1",
                        title="Old case",
                        citation="2023 FC 1",
                        decision_date=date(2023, 5, 1),
                        url="https://example.test/old",
                        source_id="FC_DECISIONS",
                        document_url="https://example.test/old.pdf",
                    ),
                    CaseSearchResult(
                        case_id="new-1",
                        title="New case",
                        citation="2025 FC 2",
                        decision_date=date(2025, 5, 1),
                        url="https://example.test/new",
                        source_id="FC_DECISIONS",
                        document_url="https://example.test/new.pdf",
                    ),
                ]
            )

    service = LawyerCaseResearchService(case_search_service=_DateRangeCaseSearchService())
    request = LawyerCaseResearchRequest(
        session_id="session-123456",
        matter_summary="Need precedent support for inadmissibility",
        jurisdiction="ca",
        intake={
            "target_court": "fc",
            "date_from": date(2024, 1, 1),
            "date_to": date(2025, 12, 31),
        },
        limit=5,
    )

    response = service.research(request)

    assert len(response.cases) == 1
    assert response.cases[0].citation == "2025 FC 2"
