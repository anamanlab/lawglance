from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import date
import re
from threading import Lock, Thread, current_thread
import time
import xml.etree.ElementTree as ET

import httpx

from immcad_api.errors import SourceUnavailableError
from immcad_api.schemas import CaseSearchRequest, CaseSearchResponse, CaseSearchResult
from immcad_api.sources.canada_courts import (
    CourtCode,
    CourtDecisionRecord,
    parse_decisia_rss_feed,
    parse_decisia_search_results_html,
    parse_fca_decisions_html_feed,
    parse_scc_json_feed,
)
from immcad_api.sources.source_registry import SourceRegistry

_SOURCE_IDS_BY_COURT = {
    "scc": ("SCC_DECISIONS",),
    "fc": ("FC_DECISIONS",),
    "fct": ("FC_DECISIONS",),
    "fc-cf": ("FC_DECISIONS",),
    "fca": ("FCA_DECISIONS",),
    "caf": ("FCA_DECISIONS",),
    "fca-caf": ("FCA_DECISIONS",),
}
_DEFAULT_SOURCE_IDS = ("FC_DECISIONS", "FCA_DECISIONS", "SCC_DECISIONS")
_SEARCH_CONFIG_BY_SOURCE: dict[str, tuple[str, CourtCode, str]] = {
    "SCC_DECISIONS": (
        "https://decisions.scc-csc.ca/scc-csc/en/d/s/index.do",
        "SCC",
        "1",
    ),
    "FC_DECISIONS": (
        "https://decisions.fct-cf.gc.ca/fc-cf/en/d/s/index.do",
        "FC",
        "54",
    ),
    "FCA_DECISIONS": (
        "https://decisions.fca-caf.gc.ca/fca-caf/en/d/s/index.do",
        "FCA",
        "53",
    ),
}
_QUERY_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "are",
        "be",
        "by",
        "canada",
        "for",
        "from",
        "how",
        "i",
        "in",
        "is",
        "it",
        "me",
        "my",
        "of",
        "on",
        "or",
        "the",
        "to",
        "was",
        "what",
        "when",
        "where",
        "who",
        "why",
        "with",
    }
)
_IMMIGRATION_TERMS = frozenset(
    {
        "immigration",
        "refugee",
        "citizenship",
        "inadmissibility",
        "admissibility",
        "visa",
        "permit",
        "permanent",
        "resident",
        "residence",
        "pr",
        "prtd",
        "deportation",
        "removal",
        "asylum",
        "express",
        "entry",
        "sponsorship",
        "irpa",
        "irpr",
    }
)
_IMMIGRATION_TEXT_PATTERNS = (
    re.compile(r"citizenship and immigration"),
    re.compile(r"immigration"),
    re.compile(r"refugee"),
    re.compile(r"asylum"),
    re.compile(r"sponsor"),
    re.compile(r"visa"),
    re.compile(r"permit"),
    re.compile(r"permanent resident"),
    re.compile(r"residence"),
    re.compile(r"inadmissib"),
    re.compile(r"admissib"),
    re.compile(r"removal"),
    re.compile(r"deport"),
    re.compile(r"express entry"),
    re.compile(r"\birpa\b"),
    re.compile(r"\birpr\b"),
)
_YEAR_PATTERN = re.compile(r"\b((?:19|20)\d{2})\b")


@dataclass
class OfficialCaseLawClient:
    source_registry: SourceRegistry
    timeout_seconds: float = 8.0
    cache_ttl_seconds: float = 300.0
    stale_cache_ttl_seconds: float = 900.0
    _cache_lock: Lock = field(default_factory=Lock, init=False, repr=False)
    _cached_records_by_source: dict[str, list[CourtDecisionRecord]] = field(
        default_factory=dict, init=False, repr=False
    )
    _cache_refreshed_at_monotonic_by_source: dict[str, float] = field(
        default_factory=dict,
        init=False,
        repr=False,
    )
    _refresh_thread: Thread | None = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        if self.cache_ttl_seconds <= 0:
            raise ValueError("cache_ttl_seconds must be > 0")
        if self.stale_cache_ttl_seconds < self.cache_ttl_seconds:
            raise ValueError(
                "stale_cache_ttl_seconds must be >= cache_ttl_seconds"
            )

    def search_cases(self, request: CaseSearchRequest) -> CaseSearchResponse:
        source_ids = self._resolve_source_ids(request.court)
        resolved_sources, errors = self._resolve_sources(source_ids)

        if not resolved_sources:
            raise SourceUnavailableError(
                "Official court case-law sources are currently unavailable. Please retry later."
            )

        records_by_source: dict[str, list[CourtDecisionRecord]] = {}
        query_records, fallback_sources, query_errors = self._fetch_query_search_records(
            request=request,
            resolved_sources=resolved_sources,
        )
        records_by_source.update(query_records)
        errors.extend(query_errors)

        fallback_source_ids = tuple(source_id for source_id, _source_url in fallback_sources)
        if fallback_source_ids:
            cache_snapshot = self._get_cache_snapshot(fallback_source_ids)
            if cache_snapshot is not None:
                cached_records, cache_age = cache_snapshot
                if cache_age <= self.cache_ttl_seconds:
                    records = self._merge_cached_and_live_records(
                        source_ids,
                        cached_records=cached_records,
                        live_records_by_source=records_by_source,
                    )
                    return self._build_search_response(records, request)
                if cache_age <= self.stale_cache_ttl_seconds:
                    self._schedule_background_refresh(fallback_sources)
                    records = self._merge_cached_and_live_records(
                        source_ids,
                        cached_records=cached_records,
                        live_records_by_source=records_by_source,
                    )
                    return self._build_search_response(records, request)

            fallback_records_by_source, fetch_errors = self._fetch_records_for_sources(
                fallback_sources
            )
            errors.extend(fetch_errors)
            if fallback_records_by_source:
                self._update_cache(fallback_records_by_source)
                records_by_source.update(fallback_records_by_source)

        if records_by_source:
            records = self._collect_records(source_ids, records_by_source)
            return self._build_search_response(records, request)

        if errors:
            raise SourceUnavailableError(
                "Official court case-law sources are currently unavailable. Please retry later."
            )

        return CaseSearchResponse(results=[])

    def _resolve_sources(
        self,
        source_ids: tuple[str, ...],
    ) -> tuple[list[tuple[str, str]], list[str]]:
        resolved_sources: list[tuple[str, str]] = []
        errors: list[str] = []
        for source_id in source_ids:
            source = self.source_registry.get_source(source_id)
            if source is None:
                errors.append(f"{source_id}: source is not configured in registry")
                continue
            resolved_sources.append((source_id, str(source.url)))
        return resolved_sources, errors

    def _get_cache_snapshot(
        self,
        source_ids: tuple[str, ...],
    ) -> tuple[list[CourtDecisionRecord], float] | None:
        with self._cache_lock:
            if not all(
                source_id in self._cached_records_by_source for source_id in source_ids
            ):
                return None
            if not all(
                source_id in self._cache_refreshed_at_monotonic_by_source
                for source_id in source_ids
            ):
                return None
            now = time.monotonic()
            cache_age = max(
                now - self._cache_refreshed_at_monotonic_by_source[source_id]
                for source_id in source_ids
            )
            records = self._collect_records(source_ids, self._cached_records_by_source)
            return records, cache_age

    def _update_cache(
        self,
        records_by_source: dict[str, list[CourtDecisionRecord]],
    ) -> None:
        refreshed_at = time.monotonic()
        with self._cache_lock:
            for source_id, records in records_by_source.items():
                self._cached_records_by_source[source_id] = list(records)
                self._cache_refreshed_at_monotonic_by_source[source_id] = refreshed_at

    def _schedule_background_refresh(
        self,
        resolved_sources: list[tuple[str, str]],
    ) -> None:
        with self._cache_lock:
            if self._refresh_thread and self._refresh_thread.is_alive():
                return
            refresh_thread = Thread(
                target=self._refresh_cache_worker,
                args=(list(resolved_sources),),
                daemon=True,
                name="official-case-cache-refresh",
            )
            self._refresh_thread = refresh_thread
            refresh_thread.start()

    def _refresh_cache_worker(self, resolved_sources: list[tuple[str, str]]) -> None:
        try:
            records_by_source, _ = self._fetch_records_for_sources(resolved_sources)
            if records_by_source:
                self._update_cache(records_by_source)
        finally:
            with self._cache_lock:
                if self._refresh_thread is current_thread():
                    self._refresh_thread = None

    def _fetch_and_parse_source_payload(
        self,
        *,
        source_id: str,
        source_url: str,
    ) -> list[CourtDecisionRecord]:
        with httpx.Client(
            timeout=self.timeout_seconds,
            follow_redirects=True,
        ) as client:
            response = client.get(source_url)
            response.raise_for_status()
        return self._parse_source_payload(source_id, response.content)

    def _fetch_records_for_sources(
        self,
        resolved_sources: list[tuple[str, str]],
    ) -> tuple[dict[str, list[CourtDecisionRecord]], list[str]]:
        records_by_source: dict[str, list[CourtDecisionRecord]] = {}
        errors: list[str] = []
        max_workers = min(len(resolved_sources), 3)
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = {
                pool.submit(
                    self._fetch_and_parse_source_payload,
                    source_id=source_id,
                    source_url=source_url,
                ): source_id
                for source_id, source_url in resolved_sources
            }
            for future in as_completed(futures):
                source_id = futures[future]
                try:
                    records_by_source[source_id] = future.result()
                except Exception as exc:
                    errors.append(f"{source_id}: {exc}")
        return records_by_source, errors

    def _fetch_query_search_records(
        self,
        *,
        request: CaseSearchRequest,
        resolved_sources: list[tuple[str, str]],
    ) -> tuple[dict[str, list[CourtDecisionRecord]], list[tuple[str, str]], list[str]]:
        if not request.query.strip():
            return {}, list(resolved_sources), []

        records_by_source: dict[str, list[CourtDecisionRecord]] = {}
        fallback_sources: list[tuple[str, str]] = []
        errors: list[str] = []
        for source_id, source_url in resolved_sources:
            if source_id not in _SEARCH_CONFIG_BY_SOURCE:
                fallback_sources.append((source_id, source_url))
                continue
            try:
                records_by_source[source_id] = self._fetch_source_records_via_query_search(
                    source_id=source_id,
                    request=request,
                )
            except Exception as exc:
                errors.append(f"{source_id}: {exc}")
                fallback_sources.append((source_id, source_url))
        return records_by_source, fallback_sources, errors

    def _fetch_source_records_via_query_search(
        self,
        *,
        source_id: str,
        request: CaseSearchRequest,
    ) -> list[CourtDecisionRecord]:
        config = _SEARCH_CONFIG_BY_SOURCE.get(source_id)
        if config is None:
            return []
        endpoint_url, court_code, collection = config
        params: dict[str, str] = {
            "cont": request.query.strip(),
            "col": collection,
            "iframe": "true",
        }
        if request.decision_date_from is not None:
            params["d1"] = request.decision_date_from.isoformat()
        if request.decision_date_to is not None:
            params["d2"] = request.decision_date_to.isoformat()

        with httpx.Client(
            timeout=self.timeout_seconds,
            follow_redirects=True,
        ) as client:
            response = client.get(endpoint_url, params=params)
            response.raise_for_status()

        return parse_decisia_search_results_html(
            response.content,
            source_id=source_id,
            court_code=court_code,
            base_url=endpoint_url,
        )

    def _collect_records(
        self,
        source_ids: tuple[str, ...],
        records_by_source: dict[str, list[CourtDecisionRecord]],
    ) -> list[CourtDecisionRecord]:
        records: list[CourtDecisionRecord] = []
        for source_id in source_ids:
            records.extend(records_by_source.get(source_id, []))
        return records

    def _merge_cached_and_live_records(
        self,
        source_ids: tuple[str, ...],
        *,
        cached_records: list[CourtDecisionRecord],
        live_records_by_source: dict[str, list[CourtDecisionRecord]],
    ) -> list[CourtDecisionRecord]:
        cached_records_by_source: dict[str, list[CourtDecisionRecord]] = {}
        for record in cached_records:
            cached_records_by_source.setdefault(record.source_id, []).append(record)

        merged: list[CourtDecisionRecord] = []
        for source_id in source_ids:
            if source_id in live_records_by_source:
                merged.extend(live_records_by_source[source_id])
                continue
            merged.extend(cached_records_by_source.get(source_id, []))
        return merged

    def _build_search_response(
        self,
        records: list[CourtDecisionRecord],
        request: CaseSearchRequest,
    ) -> CaseSearchResponse:
        filtered_records = self._filter_records_by_decision_date(records, request)
        ranked_records = self._rank_records(filtered_records, request.query)
        if ranked_records:
            return CaseSearchResponse(
                results=[
                    self._to_result(record)
                    for record in ranked_records[: request.limit]
                ]
            )
        return CaseSearchResponse(results=[])

    def _resolve_source_ids(self, court: str | None) -> tuple[str, ...]:
        if not court:
            return _DEFAULT_SOURCE_IDS

        normalized = court.strip().lower()
        if normalized in _SOURCE_IDS_BY_COURT:
            return _SOURCE_IDS_BY_COURT[normalized]

        for source_id in _DEFAULT_SOURCE_IDS:
            if normalized == source_id.lower():
                return (source_id,)

        return _DEFAULT_SOURCE_IDS

    def _parse_source_payload(
        self,
        source_id: str,
        payload: bytes,
    ) -> list[CourtDecisionRecord]:
        if source_id == "SCC_DECISIONS":
            return parse_scc_json_feed(payload)

        if source_id == "FC_DECISIONS":
            return parse_decisia_rss_feed(
                payload,
                source_id=source_id,
                court_code="FC",
            )

        if source_id == "FCA_DECISIONS":
            try:
                records = parse_decisia_rss_feed(
                    payload,
                    source_id=source_id,
                    court_code="FCA",
                )
            except ET.ParseError:
                records = parse_fca_decisions_html_feed(payload)

            if not records:
                return parse_fca_decisions_html_feed(payload)
            return records

        return []

    def _filter_records_by_decision_date(
        self,
        records: list[CourtDecisionRecord],
        request: CaseSearchRequest,
    ) -> list[CourtDecisionRecord]:
        if request.decision_date_from is None and request.decision_date_to is None:
            return records
        return [
            record
            for record in records
            if self._is_within_decision_date_range(
                record.decision_date,
                decision_date_from=request.decision_date_from,
                decision_date_to=request.decision_date_to,
            )
        ]

    def _is_within_decision_date_range(
        self,
        decision_date: date | None,
        *,
        decision_date_from: date | None,
        decision_date_to: date | None,
    ) -> bool:
        if decision_date is None:
            return False
        if decision_date_from is not None and decision_date < decision_date_from:
            return False
        if decision_date_to is not None and decision_date > decision_date_to:
            return False
        return True

    def _rank_records(
        self,
        records: list[CourtDecisionRecord],
        query: str,
    ) -> list[CourtDecisionRecord]:
        normalized_query = query.lower()
        raw_query_tokens = re.findall(r"[a-z0-9]+", query.lower())
        query_tokens = [
            token
            for token in raw_query_tokens
            if token not in _QUERY_STOPWORDS and len(token) > 1
        ]
        compact_query = " ".join(query_tokens)
        immigration_focused = any(token in _IMMIGRATION_TERMS for token in query_tokens) or any(
            pattern.search(normalized_query) for pattern in _IMMIGRATION_TEXT_PATTERNS
        )
        if not query_tokens:
            return sorted(
                records,
                key=lambda record: (
                    record.decision_date or date.min,
                    record.case_id,
                ),
                reverse=True,
            )

        scored_records: list[tuple[int, date, int, CourtDecisionRecord]] = []
        for index, record in enumerate(records):
            haystack = (
                f"{record.title} {record.citation} {record.case_id}".lower().strip()
            )
            if not haystack:
                continue

            haystack_tokens = set(re.findall(r"[a-z0-9]+", haystack))
            token_hits = sum(1 for token in query_tokens if token in haystack_tokens)
            immigration_signal_hits = sum(
                1 for pattern in _IMMIGRATION_TEXT_PATTERNS if pattern.search(haystack)
            )
            if token_hits == 0:
                # Do not return generic immigration records for unrelated/noise queries.
                if not immigration_focused:
                    continue
                if immigration_signal_hits == 0:
                    continue

            score = token_hits * 3
            if compact_query and compact_query in haystack:
                score += 8
            score += immigration_signal_hits * 2

            if immigration_focused and record.court_code in {"FC", "FCA"}:
                score += 3
            if score <= 0:
                continue

            scored_records.append(
                (
                    score,
                    record.decision_date or date.min,
                    -index,
                    record,
                )
            )

        scored_records.sort(reverse=True)
        return [record for _, _, _, record in scored_records]

    def _to_result(self, record: CourtDecisionRecord) -> CaseSearchResult:
        decision_date = record.decision_date
        if decision_date is None:
            citation_year_match = _YEAR_PATTERN.search(record.citation)
            if citation_year_match:
                decision_date = date(int(citation_year_match.group(1)), 1, 1)
            else:
                decision_date = date(1900, 1, 1)
        return CaseSearchResult(
            case_id=record.case_id or "unknown-case",
            title=record.title or "Untitled",
            citation=record.citation or "Unreported",
            decision_date=decision_date,
            url=record.decision_url,
            source_id=record.source_id,
            document_url=record.pdf_url or record.decision_url,
            docket_numbers=list(record.docket_numbers) or None,
            source_event_type=record.source_event_type,
        )
