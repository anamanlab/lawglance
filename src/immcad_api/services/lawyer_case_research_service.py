from __future__ import annotations

import re
from typing import Protocol

from immcad_api.errors import SourceUnavailableError
from immcad_api.policy import SourcePolicy, is_source_export_allowed
from immcad_api.schemas import (
    CaseSearchRequest,
    CaseSearchResponse,
    CaseSearchResult,
    LawyerCaseResearchRequest,
    LawyerCaseResearchResponse,
    LawyerCaseSupport,
)
from immcad_api.services.case_document_resolver import (
    allowed_hosts_for_source,
    is_url_allowed_for_source,
    resolve_pdf_status_with_reason,
)
from immcad_api.services.lawyer_research_planner import (
    build_research_queries,
    extract_matter_profile,
)
from immcad_api.sources import SourceRegistry


class _CaseSearchProtocol(Protocol):
    def search(self, request: CaseSearchRequest) -> CaseSearchResponse: ...


def _contains_word(text: str, word: str) -> bool:
    return re.search(rf"\b{re.escape(word)}\b", text) is not None


class LawyerCaseResearchService:
    def __init__(
        self,
        *,
        case_search_service: _CaseSearchProtocol,
        source_policy: SourcePolicy | None = None,
        source_registry: SourceRegistry | None = None,
    ) -> None:
        self.case_search_service = case_search_service
        self.source_policy = source_policy
        self.source_registry = source_registry

    def _resolve_court_label(self, case_result: CaseSearchResult) -> str | None:
        source_id = (case_result.source_id or "").strip().upper()
        if source_id == "FC_DECISIONS":
            return "FC"
        if source_id == "FCA_DECISIONS":
            return "FCA"
        if source_id == "SCC_DECISIONS":
            return "SCC"
        citation = case_result.citation.strip().upper()
        if " FCA " in f" {citation} ":
            return "FCA"
        if " FC " in f" {citation} ":
            return "FC"
        if " SCC " in f" {citation} ":
            return "SCC"
        return None

    def _resolve_export_status(
        self,
        *,
        case_result: CaseSearchResult,
    ) -> tuple[bool | None, str | None, str | None]:
        source_id = case_result.source_id
        if not source_id:
            return None, "source_export_metadata_missing", None
        if self.source_registry is None:
            return None, None, None

        source_entry = self.source_registry.get_source(source_id)
        if source_entry is None:
            return False, "source_not_in_registry_for_export", None

        source_url = str(source_entry.url)
        if case_result.document_url:
            allowed_hosts = allowed_hosts_for_source(source_url)
            if not is_url_allowed_for_source(case_result.document_url, allowed_hosts):
                return False, "export_url_not_allowed_for_source", source_url

        if self.source_policy is None:
            return None, None, source_url
        export_allowed, export_policy_reason = is_source_export_allowed(
            source_id,
            source_policy=self.source_policy,
        )
        return export_allowed, export_policy_reason, source_url

    def _score_case(
        self,
        *,
        case_result: CaseSearchResult,
        matter_summary: str,
        matter_profile: dict[str, list[str] | str | None],
    ) -> int:
        haystack = (
            f"{case_result.title} {case_result.citation} {case_result.case_id}"
        ).lower()
        summary_tokens = re.findall(r"[a-z0-9]+", matter_summary.lower())

        score = sum(1 for token in summary_tokens if len(token) >= 4 and token in haystack)

        issue_tags = matter_profile.get("issue_tags")
        if isinstance(issue_tags, list):
            for issue_tag in issue_tags:
                for issue_term in issue_tag.split("_"):
                    if issue_term and issue_term in haystack:
                        score += 2

        target_court = matter_profile.get("target_court")
        source_id = (case_result.source_id or "").lower()
        court = str(target_court).lower() if isinstance(target_court, str) else ""
        if court and (
            _contains_word(haystack, court)
            or (court == "fc" and "fc_decisions" in source_id)
            or (court == "fca" and "fca_decisions" in source_id)
            or (court == "scc" and "scc_decisions" in source_id)
        ):
            score += 3

        score += max(0, case_result.decision_date.year - 2000) // 2
        return score

    def _build_relevance_reason(
        self,
        *,
        case_result: CaseSearchResult,
        matter_profile: dict[str, list[str] | str | None],
    ) -> str:
        issue_tags = matter_profile.get("issue_tags")
        issue_fragment = ""
        if isinstance(issue_tags, list) and issue_tags:
            issue_fragment = ", ".join(tag.replace("_", " ") for tag in issue_tags[:2])

        target_court = matter_profile.get("target_court")
        court_fragment = str(target_court).upper() if isinstance(target_court, str) and target_court else "the target court"

        if issue_fragment:
            return (
                f"This case aligns with the matter issues ({issue_fragment}) "
                f"and appears relevant for {court_fragment} precedent support."
            )
        return (
            "This case matches key terms from the matter summary and is a potential "
            f"precedent source for {court_fragment}."
        )

    def _to_support(
        self,
        *,
        case_result: CaseSearchResult,
        matter_profile: dict[str, list[str] | str | None],
    ) -> LawyerCaseSupport:
        export_allowed, export_policy_reason, source_url = self._resolve_export_status(
            case_result=case_result
        )
        if source_url:
            pdf_status, pdf_reason = resolve_pdf_status_with_reason(
                document_url=case_result.document_url,
                source_url=source_url,
            )
        elif case_result.document_url:
            pdf_status, pdf_reason = "available", "document_url_present_unverified"
        else:
            pdf_status, pdf_reason = "unavailable", "document_url_missing"

        if pdf_status == "unavailable" and export_allowed is None and case_result.source_id:
            export_allowed = False
            if export_policy_reason is None:
                export_policy_reason = "source_export_metadata_missing"

        return LawyerCaseSupport(
            case_id=case_result.case_id,
            title=case_result.title,
            citation=case_result.citation,
            source_id=case_result.source_id,
            court=self._resolve_court_label(case_result),
            decision_date=case_result.decision_date,
            url=case_result.url,
            document_url=case_result.document_url,
            pdf_status=pdf_status,
            pdf_reason=pdf_reason,
            export_allowed=export_allowed,
            export_policy_reason=export_policy_reason,
            relevance_reason=self._build_relevance_reason(
                case_result=case_result,
                matter_profile=matter_profile,
            ),
            summary=None,
        )

    def research(self, request: LawyerCaseResearchRequest) -> LawyerCaseResearchResponse:
        matter_profile = extract_matter_profile(request.matter_summary)
        queries = build_research_queries(request.matter_summary, court=request.court)
        aggregated_results: list[CaseSearchResult] = []

        source_unavailable_errors = 0
        for query in queries:
            try:
                response = self.case_search_service.search(
                    CaseSearchRequest(
                        query=query,
                        jurisdiction=request.jurisdiction,
                        court=request.court,
                        limit=request.limit,
                    )
                )
            except SourceUnavailableError:
                source_unavailable_errors += 1
                continue
            aggregated_results.extend(response.results)

        if not aggregated_results:
            if source_unavailable_errors == len(queries):
                source_status = {
                    "official": "unavailable",
                    "canlii": "unavailable",
                }
            else:
                source_status = {
                    "official": "no_match",
                    "canlii": "not_used",
                }
            return LawyerCaseResearchResponse(
                matter_profile=matter_profile,
                cases=[],
                source_status=source_status,
            )

        deduped: dict[tuple[str, str, str], CaseSearchResult] = {}
        for case_result in aggregated_results:
            key = (
                case_result.case_id.strip().lower(),
                case_result.citation.strip().lower(),
                case_result.url.strip().lower(),
            )
            existing = deduped.get(key)
            if existing is None or case_result.decision_date > existing.decision_date:
                deduped[key] = case_result

        ranked = sorted(
            deduped.values(),
            key=lambda case_result: (
                self._score_case(
                    case_result=case_result,
                    matter_summary=request.matter_summary,
                    matter_profile=matter_profile,
                ),
                case_result.decision_date,
            ),
            reverse=True,
        )

        cases = [
            self._to_support(case_result=case_result, matter_profile=matter_profile)
            for case_result in ranked[: request.limit]
        ]

        canlii_used = any(
            (case_result.source_id or "").upper().startswith("CANLII")
            for case_result in ranked
        )
        official_used = any(
            not (case_result.source_id or "").upper().startswith("CANLII")
            for case_result in ranked
        )
        source_status = {
            "official": "ok" if official_used else "no_match",
            "canlii": "used" if canlii_used else "not_used",
        }

        return LawyerCaseResearchResponse(
            matter_profile=matter_profile,
            cases=cases,
            source_status=source_status,
        )
