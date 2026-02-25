from __future__ import annotations

from datetime import date

from immcad_api.errors import SourceUnavailableError
from immcad_api.schemas import CaseSearchRequest, CaseSearchResponse, CaseSearchResult
from immcad_api.services.case_search_service import CaseSearchService


class _OfficialClient:
    def __init__(self, response: CaseSearchResponse | None = None, fail: bool = False) -> None:
        self.response = response
        self.fail = fail
        self.calls = 0

    def search_cases(self, request: CaseSearchRequest) -> CaseSearchResponse:
        del request
        self.calls += 1
        if self.fail:
            raise SourceUnavailableError("official unavailable")
        if self.response is not None:
            return self.response
        return CaseSearchResponse(results=[])


class _CanliiClient:
    def __init__(self, response: CaseSearchResponse) -> None:
        self.response = response
        self.calls = 0

    def search_cases(self, request: CaseSearchRequest) -> CaseSearchResponse:
        del request
        self.calls += 1
        return self.response


def test_case_search_service_uses_official_response_first() -> None:
    official = _OfficialClient(
        response=CaseSearchResponse(
            results=[
                CaseSearchResult(
                    case_id="2026-FC-100",
                    title="Example v Canada",
                    citation="2026 FC 100",
                    decision_date=date(2026, 1, 1),
                    url="https://decisions.fct-cf.gc.ca/fc-cf/decisions/en/item/100/index.do",
                )
            ]
        )
    )
    canlii = _CanliiClient(
        response=CaseSearchResponse(
            results=[
                CaseSearchResult(
                    case_id="canlii-1",
                    title="CanLII Case",
                    citation="2026 FC 1",
                    decision_date=date(2026, 1, 1),
                    url="https://www.canlii.org/en/ca/fct/doc/2026/2026fc1/2026fc1.html",
                )
            ]
        )
    )

    service = CaseSearchService(canlii_client=canlii, official_client=official)
    response = service.search(
        CaseSearchRequest(query="citizenship", jurisdiction="ca", court="fc", limit=2)
    )

    assert official.calls == 1
    assert canlii.calls == 0
    assert response.results[0].case_id == "2026-FC-100"


def test_case_search_service_falls_back_to_canlii_when_official_unavailable() -> None:
    official = _OfficialClient(fail=True)
    canlii = _CanliiClient(
        response=CaseSearchResponse(
            results=[
                CaseSearchResult(
                    case_id="canlii-1",
                    title="CanLII fallback",
                    citation="2026 FC 1",
                    decision_date=date(2026, 1, 1),
                    url="https://www.canlii.org/en/ca/fct/doc/2026/2026fc1/2026fc1.html",
                )
            ]
        )
    )

    service = CaseSearchService(canlii_client=canlii, official_client=official)
    response = service.search(
        CaseSearchRequest(query="inadmissibility", jurisdiction="ca", court="fc", limit=2)
    )

    assert official.calls == 1
    assert canlii.calls == 1
    assert response.results[0].title == "CanLII fallback"
