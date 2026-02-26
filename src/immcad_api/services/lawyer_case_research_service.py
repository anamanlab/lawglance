from __future__ import annotations

from datetime import date
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

_MAX_CASE_SEARCH_QUERY_LENGTH = 300
_CANLII_SOURCE_PREFIX = "CANLII"
_FALLBACK_OFFICIAL_SOURCE_IDS = frozenset(
    {"FC_DECISIONS", "FCA_DECISIONS", "SCC_DECISIONS"}
)
_CITATION_ANCHOR_PATTERN = re.compile(
    r"\b(?:19|20)\d{2}\s+(?:SCC|FCA|CAF|FC)\s+\d+\b",
    re.IGNORECASE,
)
_DOCKET_ANCHOR_PATTERN = re.compile(
    r"\b[a-z]{1,5}\s*-\s*\d{1,8}\s*-\s*\d{2,4}\b",
    re.IGNORECASE,
)


class _CaseSearchProtocol(Protocol):
    def search(self, request: CaseSearchRequest) -> CaseSearchResponse: ...


def _contains_word(text: str, word: str) -> bool:
    return re.search(rf"\b{re.escape(word)}\b", text) is not None


def _normalize_case_search_query(query: str) -> str | None:
    normalized = re.sub(r"\s+", " ", query.strip())
    if not normalized:
        return None
    if len(normalized) <= _MAX_CASE_SEARCH_QUERY_LENGTH:
        return normalized
    truncated = normalized[:_MAX_CASE_SEARCH_QUERY_LENGTH]
    trimmed = truncated.rsplit(" ", 1)[0].strip()
    return trimmed or truncated.strip()


def _extract_reference_anchors(text: str) -> set[str]:
    anchors: set[str] = set()
    for match in _CITATION_ANCHOR_PATTERN.finditer(text):
        anchors.add(re.sub(r"\s+", " ", match.group(0).strip().lower()))
    for match in _DOCKET_ANCHOR_PATTERN.finditer(text):
        anchors.add(re.sub(r"\s*-\s*", "-", match.group(0).strip().lower()))
    return anchors


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

    def _classify_source_id(self, source_id: str | None) -> str:
        normalized = (source_id or "").strip().upper()
        if not normalized:
            return "unknown"
        if normalized.startswith(_CANLII_SOURCE_PREFIX):
            return "canlii"

        if self.source_registry is not None:
            source_entry = self.source_registry.get_source(normalized)
            if source_entry is None:
                return "unknown"
            if source_entry.source_type != "case_law":
                return "unknown"
            return "official"

        if normalized in _FALLBACK_OFFICIAL_SOURCE_IDS:
            return "official"
        return "unknown"

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

        profile_anchors = matter_profile.get("anchor_references")
        if isinstance(profile_anchors, list) and profile_anchors:
            reference_anchors = {
                re.sub(r"\s*-\s*", "-", re.sub(r"\s+", " ", anchor.strip().lower()))
                for anchor in profile_anchors
                if isinstance(anchor, str) and anchor.strip()
            }
        else:
            reference_anchors = _extract_reference_anchors(matter_summary.lower())
        if reference_anchors:
            normalized_citation = re.sub(r"\s+", " ", case_result.citation.strip().lower())
            normalized_case_id = re.sub(r"\s*-\s*", "-", case_result.case_id.strip().lower())
            if any(
                anchor == normalized_case_id or anchor in normalized_citation
                for anchor in reference_anchors
            ):
                score += 10

        score += max(0, case_result.decision_date.year - 2000) // 2
        return score

    def _compute_research_confidence(
        self,
        *,
        cases: list[LawyerCaseSupport],
        source_status: dict[str, str],
        matter_summary: str,
        matter_profile: dict[str, list[str] | str | None],
        intake_payload: dict[str, object] | None,
    ) -> tuple[str, list[str]]:
        reasons: list[str] = []
        if not cases:
            if source_status.get("official") == "unavailable":
                reasons.append("Official court sources were unavailable during retrieval.")
            else:
                reasons.append(
                    "No matching precedents were found for the provided summary and intake."
                )
            return "low", reasons

        score = 0
        if source_status.get("official") == "ok":
            score += 2
            reasons.append("Official court sources returned relevant case-law results.")
        elif source_status.get("official") == "unavailable":
            reasons.append(
                "Official court sources were unavailable; confidence is constrained."
            )

        if source_status.get("canlii") == "used":
            reasons.append("Some matches were sourced from CanLII metadata search results.")

        top_cases = cases[:3]
        top_case_anchors = {
            re.sub(r"\s+", " ", case.citation.strip().lower()) for case in top_cases
        } | {
            re.sub(r"\s*-\s*", "-", case.case_id.strip().lower()) for case in top_cases
        }
        profile_anchors = matter_profile.get("anchor_references")
        anchor_references = (
            {
                re.sub(r"\s*-\s*", "-", re.sub(r"\s+", " ", anchor.strip().lower()))
                for anchor in profile_anchors
                if isinstance(anchor, str) and anchor.strip()
            }
            if isinstance(profile_anchors, list)
            else _extract_reference_anchors(matter_summary.lower())
        )
        if anchor_references and any(
            anchor in top_anchor or anchor == top_anchor
            for anchor in anchor_references
            for top_anchor in top_case_anchors
        ):
            score += 2
            reasons.append("At least one top result matches a citation/docket anchor.")

        structured_intake_fields = 0
        if isinstance(intake_payload, dict):
            if intake_payload.get("objective"):
                structured_intake_fields += 1
            if intake_payload.get("target_court"):
                structured_intake_fields += 1
            if intake_payload.get("procedural_posture"):
                structured_intake_fields += 1
            if intake_payload.get("issue_tags"):
                structured_intake_fields += 1
            if intake_payload.get("anchor_citations") or intake_payload.get("anchor_dockets"):
                structured_intake_fields += 1
            if intake_payload.get("fact_keywords"):
                structured_intake_fields += 1
            if intake_payload.get("date_from") or intake_payload.get("date_to"):
                structured_intake_fields += 1
        if structured_intake_fields >= 2:
            score += 1
            reasons.append("Structured intake details improved retrieval specificity.")
        elif structured_intake_fields == 0:
            reasons.append(
                "Confidence could improve with structured intake (court, issues, anchors)."
            )

        if len(cases) >= 3:
            score += 1
            reasons.append("Multiple supporting results were found for cross-checking.")

        target_court = matter_profile.get("target_court")
        if isinstance(target_court, str) and target_court:
            target_label = target_court.upper()
            if any((case.court or "").upper() == target_label for case in top_cases):
                score += 1
                reasons.append(f"Top results align with target court focus ({target_label}).")

        if score >= 6:
            confidence = "high"
        elif score >= 3:
            confidence = "medium"
        else:
            confidence = "low"

        if not reasons:
            reasons.append("Confidence based on available retrieval signals.")
        return confidence, reasons

    def _compute_intake_feedback(
        self,
        *,
        request: LawyerCaseResearchRequest,
        matter_summary: str,
        intake_payload: dict[str, object] | None,
    ) -> tuple[str, list[str]]:
        hints: list[str] = []
        score = 0
        has_target_court = bool(request.court and request.court.strip())
        has_objective = False
        has_posture = False
        has_issue_tags = False
        has_anchor = bool(_extract_reference_anchors(matter_summary.lower()))
        has_fact_keywords = False

        if isinstance(intake_payload, dict):
            has_target_court = has_target_court or bool(
                isinstance(intake_payload.get("target_court"), str)
                and str(intake_payload.get("target_court")).strip()
            )
            has_objective = bool(
                isinstance(intake_payload.get("objective"), str)
                and str(intake_payload.get("objective")).strip()
            )
            has_posture = bool(
                isinstance(intake_payload.get("procedural_posture"), str)
                and str(intake_payload.get("procedural_posture")).strip()
            )
            issue_tags = intake_payload.get("issue_tags")
            has_issue_tags = isinstance(issue_tags, list) and len(issue_tags) > 0
            anchors = intake_payload.get("anchor_citations")
            dockets = intake_payload.get("anchor_dockets")
            has_anchor = has_anchor or (
                (isinstance(anchors, list) and len(anchors) > 0)
                or (isinstance(dockets, list) and len(dockets) > 0)
            )
            fact_keywords = intake_payload.get("fact_keywords")
            has_fact_keywords = isinstance(fact_keywords, list) and len(fact_keywords) > 0

        if has_target_court:
            score += 1
        else:
            hints.append("Add target court to narrow precedents (FC/FCA/SCC).")

        if has_objective:
            score += 1
        else:
            hints.append(
                "Select research objective (support/distinguish/background) to focus retrieval."
            )

        if has_posture:
            score += 1

        if has_issue_tags:
            score += 1
        else:
            hints.append(
                "Add issue tags (for example procedural_fairness, inadmissibility)."
            )

        if has_anchor:
            score += 1
        else:
            hints.append("Add citation or docket anchor when available.")

        if has_fact_keywords:
            score += 1

        if score >= 4:
            completeness = "high"
        elif score >= 2:
            completeness = "medium"
        else:
            completeness = "low"

        if not hints:
            hints.append("Intake coverage is strong for focused precedent retrieval.")
        return completeness, hints[:4]

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

    def _filter_results_by_decision_date_range(
        self,
        *,
        results: list[CaseSearchResult],
        decision_date_from: date | None,
        decision_date_to: date | None,
    ) -> list[CaseSearchResult]:
        if decision_date_from is None and decision_date_to is None:
            return results
        return [
            result
            for result in results
            if self._is_within_decision_date_range(
                result.decision_date,
                decision_date_from=decision_date_from,
                decision_date_to=decision_date_to,
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
        else:
            if export_policy_reason:
                pdf_status, pdf_reason = "unavailable", export_policy_reason
            elif case_result.document_url:
                pdf_status, pdf_reason = "unavailable", "document_url_unverified_source"
            else:
                pdf_status, pdf_reason = "unavailable", "document_url_missing"

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
        intake_payload = (
            request.intake.model_dump(mode="json", exclude_none=True)
            if request.intake is not None
            else None
        )
        matter_profile = extract_matter_profile(request.matter_summary, intake=intake_payload)
        effective_court = request.court
        if not effective_court and isinstance(intake_payload, dict):
            intake_target_court = intake_payload.get("target_court")
            if isinstance(intake_target_court, str) and intake_target_court.strip():
                effective_court = intake_target_court.strip()
        decision_date_from = request.intake.date_from if request.intake is not None else None
        decision_date_to = request.intake.date_to if request.intake is not None else None
        queries = build_research_queries(
            request.matter_summary,
            court=effective_court,
            intake=intake_payload,
        )
        intake_completeness, intake_hints = self._compute_intake_feedback(
            request=request,
            matter_summary=request.matter_summary,
            intake_payload=intake_payload,
        )
        aggregated_results: list[CaseSearchResult] = []

        source_unavailable_errors = 0
        for query in queries:
            normalized_query = _normalize_case_search_query(query)
            if not normalized_query or len(normalized_query) < 2:
                continue
            try:
                response = self.case_search_service.search(
                    CaseSearchRequest(
                        query=normalized_query,
                        jurisdiction=request.jurisdiction,
                        court=effective_court,
                        decision_date_from=decision_date_from,
                        decision_date_to=decision_date_to,
                        limit=request.limit,
                    )
                )
            except SourceUnavailableError:
                source_unavailable_errors += 1
                continue
            aggregated_results.extend(response.results)

        aggregated_results = self._filter_results_by_decision_date_range(
            results=aggregated_results,
            decision_date_from=decision_date_from,
            decision_date_to=decision_date_to,
        )

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
            research_confidence, confidence_reasons = self._compute_research_confidence(
                cases=[],
                source_status=source_status,
                matter_summary=request.matter_summary,
                matter_profile=matter_profile,
                intake_payload=intake_payload,
            )
            return LawyerCaseResearchResponse(
                matter_profile=matter_profile,
                cases=[],
                source_status=source_status,
                research_confidence=research_confidence,
                confidence_reasons=confidence_reasons,
                intake_completeness=intake_completeness,
                intake_hints=intake_hints,
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

        source_types = [self._classify_source_id(case_result.source_id) for case_result in ranked]
        canlii_used = any(source_type == "canlii" for source_type in source_types)
        official_used = any(source_type == "official" for source_type in source_types)
        source_status = {
            "official": "ok" if official_used else "no_match",
            "canlii": "used" if canlii_used else "not_used",
        }
        research_confidence, confidence_reasons = self._compute_research_confidence(
            cases=cases,
            source_status=source_status,
            matter_summary=request.matter_summary,
            matter_profile=matter_profile,
            intake_payload=intake_payload,
        )

        return LawyerCaseResearchResponse(
            matter_profile=matter_profile,
            cases=cases,
            source_status=source_status,
            research_confidence=research_confidence,
            confidence_reasons=confidence_reasons,
            intake_completeness=intake_completeness,
            intake_hints=intake_hints,
        )
