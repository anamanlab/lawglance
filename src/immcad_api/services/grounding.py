from __future__ import annotations

import re
from typing import Protocol, Sequence

from immcad_api.schemas import Citation


class GroundingAdapter(Protocol):
    def citation_candidates(
        self,
        *,
        message: str,
        locale: str,
        mode: str,
    ) -> list[Citation]:
        """Return grounded citation candidates for the current chat request."""


class StaticGroundingAdapter:
    """Simple grounding adapter backed by explicit citation inputs."""

    def __init__(self, grounded_citations: Sequence[Citation] | None = None) -> None:
        citations = grounded_citations or []
        self._grounded_citations = tuple(citation.model_copy(deep=True) for citation in citations)

    def citation_candidates(
        self,
        *,
        message: str,
        locale: str,
        mode: str,
    ) -> list[Citation]:
        del message, locale, mode
        return [citation.model_copy(deep=True) for citation in self._grounded_citations]


class KeywordGroundingAdapter:
    """Select grounded citations from a curated catalog using keyword overlap."""

    def __init__(
        self,
        catalog: Sequence[tuple[Citation, tuple[str, ...]]],
        *,
        max_citations: int = 3,
    ) -> None:
        if not catalog:
            raise ValueError("KeywordGroundingAdapter requires a non-empty citation catalog")
        if max_citations < 1:
            raise ValueError("max_citations must be >= 1")
        self._catalog = tuple(
            (citation.model_copy(deep=True), tuple(keyword.strip().lower() for keyword in keywords))
            for citation, keywords in catalog
        )
        self._max_citations = max_citations

    def citation_candidates(
        self,
        *,
        message: str,
        locale: str,
        mode: str,
    ) -> list[Citation]:
        del locale, mode
        tokens = set(re.findall(r"[a-z0-9]+", message.lower()))

        baseline_citation = self._catalog[0][0].model_copy(deep=True)
        selected: list[Citation] = [baseline_citation]
        selected_keys = {(baseline_citation.source_id, baseline_citation.pin)}

        scored: list[tuple[int, int, Citation]] = []
        for index, (citation, keywords) in enumerate(self._catalog[1:], start=1):
            score = sum(1 for keyword in keywords if keyword in tokens)
            if score <= 0:
                continue
            scored.append((score, -index, citation))

        for _, _, citation in sorted(scored, reverse=True):
            key = (citation.source_id, citation.pin)
            if key in selected_keys:
                continue
            selected.append(citation.model_copy(deep=True))
            selected_keys.add(key)
            if len(selected) >= self._max_citations:
                break

        return selected


def scaffold_grounded_citations() -> list[Citation]:
    return [
        Citation(
            source_id="IRPA",
            snippet="Reference to IRPA; user context omitted for privacy.",
            title="Immigration and Refugee Protection Act",
            url="https://laws-lois.justice.gc.ca/eng/acts/I-2.5/FullText.html",
            pin="s. 11",
        )
    ]


def official_grounding_catalog() -> list[tuple[Citation, tuple[str, ...]]]:
    return [
        (
            Citation(
                source_id="IRPA",
                snippet=(
                    "Immigration and Refugee Protection Act framework reference "
                    "for eligibility and admission decisions."
                ),
                title="Immigration and Refugee Protection Act",
                url="https://laws-lois.justice.gc.ca/eng/acts/I-2.5/FullText.html",
                pin="s. 11",
            ),
            (
                "immigration",
                "express",
                "entry",
                "eligibility",
                "admissibility",
                "inadmissibility",
                "visa",
                "study",
                "work",
                "sponsorship",
                "spouse",
                "family",
                "citizenship",
                "application",
            ),
        ),
        (
            Citation(
                source_id="IRPA",
                snippet=(
                    "Permanent resident status and status documents reference, "
                    "including PR card considerations."
                ),
                title="Immigration and Refugee Protection Act",
                url="https://laws-lois.justice.gc.ca/eng/acts/I-2.5/FullText.html",
                pin="s. 31",
            ),
            (
                "pr",
                "permanent",
                "resident",
                "residence",
                "card",
                "expired",
                "renew",
                "renewal",
                "outside",
                "travel",
                "document",
                "td",
            ),
        ),
        (
            Citation(
                source_id="IRCC",
                snippet=(
                    "Official IRCC operational guidance for replacing or renewing "
                    "a permanent resident card."
                ),
                title="IRCC: Renew or Replace a PR Card",
                url=(
                    "https://www.canada.ca/en/immigration-refugees-citizenship/services/"
                    "application/application-forms-guides/application-renew-replace-"
                    "permanent-resident-card.html"
                ),
                pin="PR card renewal guide",
            ),
            (
                "pr",
                "permanent",
                "resident",
                "card",
                "renew",
                "replace",
                "expired",
                "status",
            ),
        ),
        (
            Citation(
                source_id="IRCC",
                snippet=(
                    "Official IRCC process for permanent residents outside Canada "
                    "who need a travel document to return."
                ),
                title="IRCC: Permanent Resident Travel Document",
                url=(
                    "https://www.canada.ca/en/immigration-refugees-citizenship/services/"
                    "application/application-forms-guides/application-apply-permanent-"
                    "resident-travel-document.html"
                ),
                pin="PRTD application guide",
            ),
            (
                "outside",
                "abroad",
                "travel",
                "document",
                "prtd",
                "return",
                "reentry",
                "expired",
                "card",
            ),
        ),
        (
            Citation(
                source_id="IRCC",
                snippet=(
                    "Program overview for Express Entry economic immigration pathways "
                    "and eligibility factors."
                ),
                title="IRCC: Express Entry",
                url=(
                    "https://www.canada.ca/en/immigration-refugees-citizenship/services/"
                    "immigrate-canada/express-entry.html"
                ),
                pin="Program overview",
            ),
            (
                "express",
                "entry",
                "crs",
                "draw",
                "fsw",
                "cec",
                "federal",
                "skilled",
                "worker",
                "points",
            ),
        ),
    ]
