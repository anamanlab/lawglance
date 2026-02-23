from __future__ import annotations

from immcad_api.schemas import CaseSearchRequest, CaseSearchResponse
from immcad_api.sources import CanLIIClient


class CaseSearchService:
    def __init__(self, canlii_client: CanLIIClient) -> None:
        self.canlii_client = canlii_client

    def search(self, request: CaseSearchRequest) -> CaseSearchResponse:
        return self.canlii_client.search_cases(request)
