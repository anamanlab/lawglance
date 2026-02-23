from __future__ import annotations

from immcad_api.providers.base import ProviderResult
from immcad_api.schemas import Citation


class ScaffoldProvider:
    """Deterministic local provider for development and tests."""

    name = "scaffold"

    def generate(self, *, message: str, citations: list[Citation], locale: str) -> ProviderResult:
        answer = (
            "Scaffold response: this environment is using deterministic fallback content. "
            "Replace provider adapters with production SDK integrations. "
            f"Query received: {message.strip()}"
        )
        return ProviderResult(
            provider=self.name,
            answer=answer,
            citations=citations,
            confidence="low",
        )
