from __future__ import annotations

from dataclasses import dataclass

from immcad_api.providers.base import Provider, ProviderError, ProviderResult


@dataclass
class RoutingResult:
    result: ProviderResult
    fallback_used: bool
    fallback_reason: str | None


class ProviderRouter:
    def __init__(self, providers: list[Provider], primary_provider_name: str) -> None:
        if not providers:
            raise ValueError("ProviderRouter requires at least one provider")
        self.providers = providers
        self.primary_provider_name = primary_provider_name

    def generate(self, *, message: str, citations, locale: str) -> RoutingResult:
        last_error: ProviderError | None = None

        for provider in self.providers:
            try:
                result = provider.generate(message=message, citations=citations, locale=locale)
                fallback_used = provider.name != self.primary_provider_name
                fallback_reason = last_error.code if fallback_used and last_error else None
                return RoutingResult(
                    result=result,
                    fallback_used=fallback_used,
                    fallback_reason=fallback_reason,
                )
            except ProviderError as exc:
                last_error = exc

        if last_error:
            raise last_error
        raise ProviderError("router", "provider_error", "No provider returned a response")
