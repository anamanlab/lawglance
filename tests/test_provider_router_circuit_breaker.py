from __future__ import annotations

from dataclasses import dataclass

from immcad_api.providers import ProviderError, ProviderResult, ProviderRouter


@dataclass
class _FailingProvider:
    name: str
    code: str = "provider_error"
    message: str = "provider failed"

    def generate(self, *, message: str, citations, locale: str) -> ProviderResult:
        raise ProviderError(self.name, self.code, self.message)


@dataclass
class _FlakyProvider:
    name: str
    fail_once: bool = True

    def generate(self, *, message: str, citations, locale: str) -> ProviderResult:
        if self.fail_once:
            self.fail_once = False
            raise ProviderError(self.name, "provider_error", "temporary failure")
        return ProviderResult(provider=self.name, answer="ok", citations=citations, confidence="medium")


@dataclass
class _SuccessProvider:
    name: str
    answer: str = "fallback answer"

    def generate(self, *, message: str, citations, locale: str) -> ProviderResult:
        return ProviderResult(
            provider=self.name,
            answer=self.answer,
            citations=citations,
            confidence="medium",
        )


def test_router_records_fallback_metrics() -> None:
    failing = _FailingProvider(name="openai", code="timeout", message="timeout")
    fallback = _SuccessProvider(name="gemini")
    router = ProviderRouter(
        [failing, fallback],
        "openai",
        circuit_breaker_failure_threshold=3,
        circuit_breaker_open_seconds=30.0,
    )

    result = router.generate(message="q", citations=[], locale="en-CA")

    assert result.fallback_used is True
    assert result.fallback_reason == "timeout"

    metrics = router.telemetry_snapshot()
    assert metrics["openai"]["failure"] == 1
    assert metrics["gemini"]["success"] == 1
    assert metrics["gemini"]["fallback_success"] == 1


def test_router_circuit_breaker_skips_open_provider() -> None:
    current_time = [0.0]

    def _time_fn() -> float:
        return current_time[0]

    failing = _FailingProvider(name="openai")
    fallback = _SuccessProvider(name="gemini")
    router = ProviderRouter(
        [failing, fallback],
        "openai",
        circuit_breaker_failure_threshold=1,
        circuit_breaker_open_seconds=60.0,
        time_fn=_time_fn,
    )

    first = router.generate(message="q1", citations=[], locale="en-CA")
    second = router.generate(message="q2", citations=[], locale="en-CA")

    assert first.fallback_used is True
    assert second.fallback_used is True

    metrics = router.telemetry_snapshot()
    assert metrics["openai"]["failure"] == 1
    assert metrics["openai"]["circuit_open"] == 1
    assert metrics["openai"]["circuit_skip"] == 1


def test_router_resets_circuit_after_window() -> None:
    current_time = [0.0]

    def _time_fn() -> float:
        return current_time[0]

    flaky = _FlakyProvider(name="openai", fail_once=True)
    fallback = _SuccessProvider(name="gemini")
    router = ProviderRouter(
        [flaky, fallback],
        "openai",
        circuit_breaker_failure_threshold=1,
        circuit_breaker_open_seconds=5.0,
        time_fn=_time_fn,
    )

    first = router.generate(message="q1", citations=[], locale="en-CA")
    current_time[0] = 10.0
    second = router.generate(message="q2", citations=[], locale="en-CA")

    assert first.fallback_used is True
    assert second.fallback_used is False
    assert second.result.provider == "openai"

    metrics = router.telemetry_snapshot()
    assert metrics["openai"]["success"] == 1
