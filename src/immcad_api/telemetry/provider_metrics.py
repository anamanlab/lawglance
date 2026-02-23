from __future__ import annotations

from collections import Counter, defaultdict
from threading import Lock


class ProviderMetrics:
    def __init__(self) -> None:
        self._lock = Lock()
        self._counters: dict[str, Counter[str]] = defaultdict(Counter)

    def increment(self, *, provider: str, event: str) -> None:
        with self._lock:
            self._counters[provider][event] += 1

    def snapshot(self) -> dict[str, dict[str, int]]:
        with self._lock:
            return {
                provider: dict(counter)
                for provider, counter in self._counters.items()
            }
