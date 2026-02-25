from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import re
import xml.etree.ElementTree as ET

import httpx

from immcad_api.errors import SourceUnavailableError
from immcad_api.schemas import CaseSearchRequest, CaseSearchResponse, CaseSearchResult
from immcad_api.sources.canada_courts import (
    CourtDecisionRecord,
    parse_decisia_rss_feed,
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
_DEFAULT_SOURCE_IDS = ("SCC_DECISIONS", "FC_DECISIONS", "FCA_DECISIONS")


@dataclass
class OfficialCaseLawClient:
    source_registry: SourceRegistry
    timeout_seconds: float = 8.0

    def search_cases(self, request: CaseSearchRequest) -> CaseSearchResponse:
        source_ids = self._resolve_source_ids(request.court)
        records: list[CourtDecisionRecord] = []
        errors: list[str] = []

        with httpx.Client(timeout=self.timeout_seconds) as client:
            for source_id in source_ids:
                source = self.source_registry.get_source(source_id)
                if source is None:
                    continue

                try:
                    response = client.get(str(source.url))
                    response.raise_for_status()
                    records.extend(
                        self._parse_source_payload(source_id, response.content)
                    )
                except Exception as exc:
                    errors.append(f"{source_id}: {exc}")

        ranked_records = self._rank_records(records, request.query)
        if ranked_records:
            return CaseSearchResponse(
                results=[
                    self._to_result(record)
                    for record in ranked_records[: request.limit]
                ]
            )

        if records:
            return CaseSearchResponse(results=[])

        if errors:
            raise SourceUnavailableError(
                "Official court case-law sources are currently unavailable. Please retry later."
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

    def _rank_records(
        self,
        records: list[CourtDecisionRecord],
        query: str,
    ) -> list[CourtDecisionRecord]:
        query_tokens = re.findall(r"[a-z0-9]+", query.lower())
        compact_query = " ".join(query_tokens)
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

            token_hits = sum(1 for token in query_tokens if token in haystack)
            if token_hits == 0:
                continue

            score = token_hits
            if compact_query and compact_query in haystack:
                score += 5

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
        return CaseSearchResult(
            case_id=record.case_id or "unknown-case",
            title=record.title or "Untitled",
            citation=record.citation or "Unreported",
            decision_date=record.decision_date or date.today(),
            url=record.decision_url,
        )
