from __future__ import annotations

from dataclasses import dataclass
import time

from immcad_api.telemetry import ProviderMetrics

from immcad_api.providers.base import Provider, ProviderError, ProviderResult


@dataclass
class RoutingResult:
    result: ProviderResult
    fallback_used: bool
    fallback_reason: str | None


@dataclass
class _CircuitState:
    failures: int = 0
    open_until: float | None = None


class ProviderRouter:
    def __init__(
        self,
        providers: list[Provider],
        primary_provider_name: str,
        *,
        circuit_breaker_failure_threshold: int = 3,
        circuit_breaker_open_seconds: float = 30.0,
        telemetry: ProviderMetrics | None = None,
        time_fn=None,
    ) -> None:
        if not providers:
            raise ValueError("ProviderRouter requires at least one provider")
        if circuit_breaker_failure_threshold < 1:
            raise ValueError("circuit_breaker_failure_threshold must be >= 1")
        if circuit_breaker_open_seconds <= 0:
            raise ValueError("circuit_breaker_open_seconds must be > 0")
        self.providers = providers
        self.primary_provider_name = primary_provider_name
        self.circuit_breaker_failure_threshold = circuit_breaker_failure_threshold
        self.circuit_breaker_open_seconds = circuit_breaker_open_seconds
        self.telemetry = telemetry or ProviderMetrics()
        self._time_fn = time_fn or time.monotonic
        self._states: dict[str, _CircuitState] = {
            provider.name: _CircuitState() for provider in providers
        }

    def _is_circuit_open(self, provider_name: str) -> bool:
        state = self._states.setdefault(provider_name, _CircuitState())
        if state.open_until is None:
            return False
        now = self._time_fn()
        if now >= state.open_until:
            state.open_until = None
            state.failures = 0
            return False
        return True

    def _record_failure(self, provider_name: str) -> None:
        state = self._states.setdefault(provider_name, _CircuitState())
        state.failures += 1
        self.telemetry.increment(provider=provider_name, event="failure")
        if state.failures >= self.circuit_breaker_failure_threshold:
            state.open_until = self._time_fn() + self.circuit_breaker_open_seconds
            self.telemetry.increment(provider=provider_name, event="circuit_open")

    def _record_success(self, provider_name: str, *, fallback_used: bool) -> None:
        state = self._states.setdefault(provider_name, _CircuitState())
        state.failures = 0
        state.open_until = None
        self.telemetry.increment(provider=provider_name, event="success")
        if fallback_used:
            self.telemetry.increment(provider=provider_name, event="fallback_success")

    def telemetry_snapshot(self) -> dict[str, dict[str, int]]:
        return self.telemetry.snapshot()

    def generate(self, *, message: str, citations, locale: str) -> RoutingResult:
        last_error: ProviderError | None = None

        for provider in self.providers:
            if self._is_circuit_open(provider.name):
                self.telemetry.increment(provider=provider.name, event="circuit_skip")
                if last_error is None:
                    last_error = ProviderError(
                        provider.name,
                        "provider_error",
                        f"Circuit breaker open for provider '{provider.name}'",
                    )
                continue
            try:
                result = provider.generate(message=message, citations=citations, locale=locale)
                fallback_used = provider.name != self.primary_provider_name
                fallback_reason = last_error.code if fallback_used and last_error else None
                self._record_success(provider.name, fallback_used=fallback_used)
                return RoutingResult(
                    result=result,
                    fallback_used=fallback_used,
                    fallback_reason=fallback_reason,
                )
            except ProviderError as exc:
                self._record_failure(provider.name)
                last_error = exc

        if last_error:
            raise last_error
        raise ProviderError("router", "provider_error", "No provider returned a response")
