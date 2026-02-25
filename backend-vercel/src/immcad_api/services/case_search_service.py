from __future__ import annotations

from immcad_api.errors import SourceUnavailableError
from immcad_api.schemas import CaseSearchRequest, CaseSearchResponse
from immcad_api.sources import CanLIIClient, OfficialCaseLawClient


class CaseSearchService:
    def __init__(
        self,
        *,
        canlii_client: CanLIIClient | None = None,
        official_client: OfficialCaseLawClient | None = None,
    ) -> None:
        self.canlii_client = canlii_client
        self.official_client = official_client

    def search(self, request: CaseSearchRequest) -> CaseSearchResponse:
        if self.official_client is not None:
            try:
                official_response = self.official_client.search_cases(request)
                return official_response
            except SourceUnavailableError:
                pass

        if self.canlii_client is not None:
            return self.canlii_client.search_cases(request)

        raise SourceUnavailableError("Case-law sources are unavailable. Please retry later.")
