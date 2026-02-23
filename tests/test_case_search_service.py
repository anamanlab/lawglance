from __future__ import annotations

from datetime import date

from immcad_api.schemas import CaseSearchRequest, CaseSearchResponse, CaseSearchResult
from immcad_api.services.case_search_service import CaseSearchService


class _FakeCanLIIClient:
    def __init__(self) -> None:
        self.request: CaseSearchRequest | None = None

    def search_cases(self, request: CaseSearchRequest) -> CaseSearchResponse:
        self.request = request
        return CaseSearchResponse(
            results=[
                CaseSearchResult(
                    case_id="ABC-123",
                    title="Sample case",
                    citation="2024 FC 123",
                    decision_date=date(2024, 1, 15),
                    url="https://example.com/case/abc-123",
                )
            ]
        )


def test_case_search_service_delegates_to_canlii_client() -> None:
    client = _FakeCanLIIClient()
    service = CaseSearchService(client)
    request = CaseSearchRequest(query="express entry", jurisdiction="ca", limit=1)
    response = service.search(request)

    assert client.request is request
    assert len(response.results) == 1
    assert response.results[0].case_id == "ABC-123"
