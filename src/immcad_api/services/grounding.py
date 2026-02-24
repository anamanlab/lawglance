from __future__ import annotations

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
