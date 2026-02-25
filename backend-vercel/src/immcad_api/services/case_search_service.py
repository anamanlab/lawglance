from __future__ import annotations

from immcad_api.errors import ApiError, SourceUnavailableError
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
        official_response: CaseSearchResponse | None = None
        official_error: SourceUnavailableError | None = None
        if self.official_client is not None:
            try:
                official_response = self.official_client.search_cases(request)
            except SourceUnavailableError as exc:
                official_error = exc

        canlii_response: CaseSearchResponse | None = None
        canlii_error: ApiError | None = None
        should_query_canlii = self.canlii_client is not None and (
            official_response is None or not official_response.results
        )
        if should_query_canlii and self.canlii_client is not None:
            try:
                canlii_response = self.canlii_client.search_cases(request)
            except ApiError as exc:
                canlii_error = exc

        if official_response is not None:
            if official_response.results:
                return official_response
            if canlii_response is not None and canlii_response.results:
                return canlii_response
            return official_response

        if canlii_response is not None:
            return canlii_response

        if canlii_error is not None:
            raise canlii_error

        if official_error is not None:
            raise official_error

        raise SourceUnavailableError("Case-law sources are unavailable. Please retry later.")
