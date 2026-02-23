from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from immcad_api.schemas import Citation, Confidence


class ProviderError(Exception):
    def __init__(self, provider: str, code: str, message: str) -> None:
        super().__init__(message)
        self.provider = provider
        self.code = code
        self.message = message


@dataclass
class ProviderResult:
    provider: str
    answer: str
    citations: list[Citation]
    confidence: Confidence


class Provider(Protocol):
    name: str

    def generate(
        self,
        *,
        message: str,
        citations: list[Citation],
        locale: str,
        grounding_context: Sequence[str] | None = None,
    ) -> ProviderResult:
        ...
