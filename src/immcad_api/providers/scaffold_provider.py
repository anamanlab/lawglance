from __future__ import annotations

from collections.abc import Sequence

from immcad_api.providers.base import ProviderResult
from immcad_api.schemas import Citation


class ScaffoldProvider:
    """Deterministic local provider for development and tests."""

    name = "scaffold"

    def generate(
        self,
        *,
        message: str,
        citations: list[Citation],
        locale: str,
        grounding_context: Sequence[str] | None = None,
    ) -> ProviderResult:
        grounding_note = ""
        if grounding_context:
            count = sum(1 for snippet in grounding_context if snippet and snippet.strip())
            if count:
                grounding_note = f" Grounding snippets supplied: {count}."
        answer = (
            "Scaffold response: this environment is using deterministic fallback content. "
            "Replace provider adapters with production SDK integrations. "
            f"Query received: {message.strip()}{grounding_note}"
        )
        return ProviderResult(
            provider=self.name,
            answer=answer,
            citations=citations,
            confidence="low",
        )
