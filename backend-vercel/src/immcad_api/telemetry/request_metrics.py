from __future__ import annotations

from collections import Counter, deque
import math
from threading import Lock
import time
from typing import Callable


class RequestMetrics:
    def __init__(
        self,
        *,
        max_latency_samples: int = 2048,
        time_fn: Callable[[], float] | None = None,
    ) -> None:
        if max_latency_samples < 1:
            raise ValueError("max_latency_samples must be >= 1")
        self._time_fn = time_fn or time.monotonic
        self._started_at = self._time_fn()
        self._lock = Lock()
        self._api_requests = 0
        self._api_errors = 0
        self._chat_requests = 0
        self._chat_fallbacks = 0
        self._chat_refusals = 0
        self._export_attempts = 0
        self._export_allowed = 0
        self._export_blocked = 0
        self._export_fetch_failures = 0
        self._export_too_large = 0
        self._export_policy_reasons: Counter[str] = Counter()
        self._latencies_ms: deque[float] = deque(maxlen=max_latency_samples)

    def record_api_response(self, *, status_code: int, duration_seconds: float) -> None:
        latency_ms = max(duration_seconds * 1000.0, 0.0)
        with self._lock:
            self._api_requests += 1
            if status_code >= 400:
                self._api_errors += 1
            self._latencies_ms.append(latency_ms)

    def record_chat_outcome(self, *, fallback_used: bool, refusal_used: bool) -> None:
        with self._lock:
            self._chat_requests += 1
            if fallback_used:
                self._chat_fallbacks += 1
            if refusal_used:
                self._chat_refusals += 1

    def record_export_outcome(
        self, *, outcome: str, policy_reason: str | None = None
    ) -> None:
        with self._lock:
            self._export_attempts += 1
            if outcome == "allowed":
                self._export_allowed += 1
            elif outcome == "blocked":
                self._export_blocked += 1
            elif outcome == "fetch_failed":
                self._export_fetch_failures += 1
            elif outcome == "too_large":
                self._export_too_large += 1
            if policy_reason:
                self._export_policy_reasons[policy_reason] += 1

    def snapshot(self) -> dict[str, object]:
        with self._lock:
            elapsed_seconds = max(self._time_fn() - self._started_at, 1e-9)
            api_requests = self._api_requests
            api_errors = self._api_errors
            chat_requests = self._chat_requests
            chat_fallbacks = self._chat_fallbacks
            chat_refusals = self._chat_refusals
            export_attempts = self._export_attempts
            export_allowed = self._export_allowed
            export_blocked = self._export_blocked
            export_fetch_failures = self._export_fetch_failures
            export_too_large = self._export_too_large
            export_policy_reasons = dict(self._export_policy_reasons)
            latencies = list(self._latencies_ms)

        request_rate_per_minute = (api_requests / elapsed_seconds) * 60.0
        error_rate = (api_errors / api_requests) if api_requests else 0.0
        fallback_rate = (chat_fallbacks / chat_requests) if chat_requests else 0.0
        refusal_rate = (chat_refusals / chat_requests) if chat_requests else 0.0

        return {
            "window_seconds": elapsed_seconds,
            "requests": {
                "total": api_requests,
                "rate_per_minute": request_rate_per_minute,
            },
            "errors": {
                "total": api_errors,
                "rate": error_rate,
            },
            "fallback": {
                "total": chat_fallbacks,
                "rate": fallback_rate,
            },
            "refusal": {
                "total": chat_refusals,
                "rate": refusal_rate,
            },
            "export": {
                "attempts": export_attempts,
                "allowed": export_allowed,
                "blocked": export_blocked,
                "fetch_failures": export_fetch_failures,
                "too_large": export_too_large,
                "policy_reasons": export_policy_reasons,
            },
            "latency_ms": {
                "sample_count": len(latencies),
                "p50": self._percentile(latencies, 50.0),
                "p95": self._percentile(latencies, 95.0),
                "p99": self._percentile(latencies, 99.0),
            },
        }

    @staticmethod
    def _percentile(values: list[float], percentile: float) -> float:
        if not values:
            return 0.0
        if len(values) == 1:
            return float(values[0])

        ordered = sorted(values)
        rank = (len(ordered) - 1) * (percentile / 100.0)
        lower_index = int(math.floor(rank))
        upper_index = int(math.ceil(rank))
        lower_value = ordered[lower_index]
        upper_value = ordered[upper_index]
        if lower_index == upper_index:
            return float(lower_value)
        blend = rank - lower_index
        return float(lower_value + (upper_value - lower_value) * blend)
