from __future__ import annotations

from immcad_api.providers.base import ProviderError


def map_provider_exception(provider: str, exc: Exception) -> ProviderError:
    message = str(exc)
    lowered = message.lower()

    if "rate" in lowered or "429" in lowered or "quota" in lowered:
        return ProviderError(provider, "rate_limit", message)

    if "timeout" in lowered or "timed out" in lowered or "deadline" in lowered:
        return ProviderError(provider, "timeout", message)

    return ProviderError(provider, "provider_error", message)
