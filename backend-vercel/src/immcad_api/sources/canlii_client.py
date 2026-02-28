from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import re
from urllib.parse import quote_plus

import httpx

from immcad_api.errors import RateLimitError, SourceUnavailableError
from immcad_api.schemas import CaseSearchRequest, CaseSearchResponse, CaseSearchResult
from immcad_api.sources.canlii_usage_limiter import (
    CanLIIUsageLimitExceeded,
    CanLIIUsageLimiter,
    build_canlii_usage_limiter,
)

_CANLII_SOURCE_ID = "CANLII_CASE_BROWSE"
_DATABASE_ID_ALIASES = {
    "fc": "fct",
    "fct": "fct",
    "fc-cf": "fct",
    "federal court": "fct",
    "fca": "fca",
    "caf": "fca",
    "fca-caf": "fca",
    "federal court of appeal": "fca",
    "scc": "scc",
    "scc-csc": "scc",
    "supreme court of canada": "scc",
}


@dataclass
class CanLIIClient:
    api_key: str | None
    base_url: str = "https://api.canlii.org/v1"
    timeout_seconds: float = 8.0
    allow_scaffold_fallback: bool = True
    default_database_id: str = "fct"
    max_metadata_scan: int = 100
    usage_limiter: CanLIIUsageLimiter | None = None

    def __post_init__(self) -> None:
        if self.usage_limiter is None:
            self.usage_limiter = build_canlii_usage_limiter(redis_url=None)

    def search_cases(self, request: CaseSearchRequest) -> CaseSearchResponse:
        if not self.api_key:
            return self._fallback_or_error(request)

        database_id = self._resolve_database_id(request)
        params = {
            "offset": 0,
            "resultCount": self._resolve_result_count(request.limit),
            "api_key": self.api_key,
        }

        endpoint = f"{self.base_url.rstrip('/')}/caseBrowse/en/{database_id}/"

        try:
            lease = self.usage_limiter.acquire()
        except CanLIIUsageLimitExceeded as exc:
            message = self._build_rate_limit_message(exc.reason)
            raise RateLimitError(message)
        except Exception:
            return self._fallback_or_error(request)

        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                response = client.get(endpoint, params=params)
                response.raise_for_status()
                payload = response.json()
        except Exception:
            return self._fallback_or_error(request)
        finally:
            lease.release()

        cases = self._extract_cases(payload)
        if cases is None:
            return self._fallback_or_error(request)
        if not cases:
            return CaseSearchResponse(results=[])

        ranked_cases = self._rank_cases(cases, request.query)
        results: list[CaseSearchResult] = []
        for item in ranked_cases:
            decision_date = self._parse_decision_date(
                item.get("decisionDate") or item.get("publishedDate") or item.get("date")
            )
            case_id = self._extract_case_id(item.get("caseId"), item.get("databaseId"))
            title = self._coerce_string(item.get("title")) or "Untitled"
            citation = self._coerce_string(item.get("citation")) or ""
            decision_url = self._extract_case_url(
                item=item,
                database_id=database_id,
                case_id=case_id,
                title=title,
                citation=citation,
            )
            results.append(
                CaseSearchResult(
                    case_id=case_id,
                    title=title,
                    citation=citation,
                    decision_date=decision_date,
                    url=decision_url,
                    source_id=_CANLII_SOURCE_ID,
                    document_url=decision_url,
                )
            )

        filtered_results = self._filter_results_by_decision_date(results, request)
        return CaseSearchResponse(results=filtered_results[: request.limit])

    def _fallback(self, request: CaseSearchRequest) -> CaseSearchResponse:
        court = request.court or self.default_database_id
        results = []

        for index in range(1, min(request.limit, 3) + 1):
            slug = request.query.lower().replace(" ", "-")[:48]
            results.append(
                CaseSearchResult(
                    case_id=f"{court.upper()}-{date.today().year}-{index}",
                    title=f"Scaffold Case {index}: {request.query}",
                    citation=f"{court.upper()} {date.today().year} {index}",
                    decision_date=date.today(),
                    url=f"https://www.canlii.org/en/ca/{court}/doc/{date.today().year}/{slug}-{index}.html",
                    source_id=_CANLII_SOURCE_ID,
                    document_url=f"https://www.canlii.org/en/ca/{court}/doc/{date.today().year}/{slug}-{index}.html",
                )
            )

        filtered_results = self._filter_results_by_decision_date(results, request)
        return CaseSearchResponse(results=filtered_results[: request.limit])

    def _fallback_or_error(self, request: CaseSearchRequest) -> CaseSearchResponse:
        if self.allow_scaffold_fallback:
            return self._fallback(request)
        raise SourceUnavailableError("Case-law source is currently unavailable. Please retry later.")

    def _resolve_database_id(self, request: CaseSearchRequest) -> str:
        candidate = self._coerce_string(request.court)
        if candidate:
            normalized = candidate.lower()
            return _DATABASE_ID_ALIASES.get(normalized, normalized)
        return self.default_database_id

    def _resolve_result_count(self, limit: int) -> int:
        target = max(limit * 8, 40)
        return min(target, self.max_metadata_scan)

    def _build_rate_limit_message(self, reason: str) -> str:
        reason_map = {
            "daily_limit": "CanLII daily quota reached. Please retry after UTC midnight.",
            "per_second_limit": "CanLII per-second request limit reached. Please retry shortly.",
            "concurrent_limit": "CanLII concurrent request limit reached. Please retry shortly.",
        }
        return reason_map.get(reason, "CanLII request quota exceeded. Please retry later.")

    def _coerce_string(self, value) -> str | None:
        if isinstance(value, str):
            normalized = value.strip()
            return normalized if normalized else None
        return None

    def _extract_case_id(self, case_id_value, database_id_value) -> str:
        if isinstance(case_id_value, str) and case_id_value.strip():
            return case_id_value.strip()
        if isinstance(case_id_value, dict):
            for key in ("en", "fr"):
                candidate = case_id_value.get(key)
                if isinstance(candidate, str) and candidate.strip():
                    return candidate.strip()
            for candidate in case_id_value.values():
                if isinstance(candidate, str) and candidate.strip():
                    return candidate.strip()

        database_id = self._coerce_string(database_id_value)
        if database_id:
            return database_id
        return "unknown-case"

    def _extract_case_url(
        self,
        *,
        item: dict,
        database_id: str,
        case_id: str,
        title: str,
        citation: str,
    ) -> str:
        explicit_url = self._coerce_string(item.get("url"))
        if explicit_url:
            return explicit_url

        search_seed = case_id or citation or title
        if not search_seed:
            return "https://www.canlii.org/"
        return f"https://www.canlii.org/en/#search/type=decision&text={quote_plus(search_seed)}&id={quote_plus(database_id)}"

    def _rank_cases(self, cases: list[dict], query: str) -> list[dict]:
        query_tokens = re.findall(r"[a-z0-9]+", query.lower())
        if not query_tokens:
            return cases

        scored_cases: list[tuple[int, int, dict]] = []
        compact_query = " ".join(query_tokens)
        for index, item in enumerate(cases):
            title = self._coerce_string(item.get("title")) or ""
            citation = self._coerce_string(item.get("citation")) or ""
            case_id = self._extract_case_id(item.get("caseId"), item.get("databaseId"))
            haystack = f"{title} {citation} {case_id}".lower()
            if not haystack.strip():
                continue

            token_hits = sum(1 for token in query_tokens if token in haystack)
            if token_hits == 0:
                continue
            score = token_hits
            if compact_query and compact_query in haystack:
                score += 5
            scored_cases.append((score, index, item))

        if not scored_cases:
            # Avoid returning arbitrary metadata rows when query terms do not match.
            return []

        scored_cases.sort(key=lambda value: (-value[0], value[1]))
        return [item for _, _, item in scored_cases]

    def _extract_cases(self, payload) -> list[dict] | None:
        if not isinstance(payload, dict):
            return None

        if isinstance(payload.get("cases"), list):
            return payload["cases"]
        if isinstance(payload.get("results"), list):
            return payload["results"]
        if isinstance(payload.get("caseResults"), list):
            return payload["caseResults"]
        return None

    def _parse_decision_date(self, value) -> date:
        if not isinstance(value, str) or not value.strip():
            return date.today()
        normalized = value.split("T", 1)[0]
        try:
            return date.fromisoformat(normalized)
        except ValueError:
            return date.today()

    def _filter_results_by_decision_date(
        self,
        results: list[CaseSearchResult],
        request: CaseSearchRequest,
    ) -> list[CaseSearchResult]:
        if request.decision_date_from is None and request.decision_date_to is None:
            return results
        return [
            result
            for result in results
            if self._is_within_decision_date_range(
                result.decision_date,
                decision_date_from=request.decision_date_from,
                decision_date_to=request.decision_date_to,
            )
        ]

    def _is_within_decision_date_range(
        self,
        decision_date: date,
        *,
        decision_date_from: date | None,
        decision_date_to: date | None,
    ) -> bool:
        if decision_date_from is not None and decision_date < decision_date_from:
            return False
        if decision_date_to is not None and decision_date > decision_date_to:
            return False
        return True
