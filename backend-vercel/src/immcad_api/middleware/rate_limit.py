from __future__ import annotations

from collections import defaultdict, deque
import importlib
import logging
from threading import Lock
import time


LOGGER = logging.getLogger(__name__)


class InMemoryRateLimiter:
    """Simple per-client in-memory limiter for MVP environments."""

    def __init__(self, limit_per_minute: int) -> None:
        self.limit_per_minute = max(limit_per_minute, 1)
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def allow(self, client_id: str) -> bool:
        now = time.time()
        window_start = now - 60

        with self._lock:
            bucket = self._events[client_id]
            while bucket and bucket[0] < window_start:
                bucket.popleft()

            if len(bucket) >= self.limit_per_minute:
                return False

            bucket.append(now)
            return True


class RedisRateLimiter:
    """Fixed-window rate limiter backed by Redis."""

    def __init__(
        self, redis_client, *, limit_per_minute: int, prefix: str = "immcad:ratelimit"
    ) -> None:
        self.redis_client = redis_client
        self.limit_per_minute = max(limit_per_minute, 1)
        self.prefix = prefix

    def allow(self, client_id: str) -> bool:
        current_window = int(time.time() // 60)
        key = f"{self.prefix}:{client_id}:{current_window}"
        value = self.redis_client.incr(key)
        if value == 1:
            self.redis_client.expire(key, 65)
        return int(value) <= self.limit_per_minute


def build_rate_limiter(*, limit_per_minute: int, redis_url: str | None):
    if not redis_url:
        LOGGER.info("Using in-memory API rate limiter (redis_url not configured)")
        return InMemoryRateLimiter(limit_per_minute)

    try:
        redis = importlib.import_module("redis")

        redis_client = redis.Redis.from_url(
            redis_url,
            socket_timeout=0.5,
            socket_connect_timeout=0.5,
        )
        redis_client.ping()
        LOGGER.info("Using Redis-backed API rate limiter")
        return RedisRateLimiter(redis_client, limit_per_minute=limit_per_minute)
    except Exception as exc:
        # Keep the service available even if Redis is absent in dev environments.
        LOGGER.warning(
            "Redis rate limiter unavailable; falling back to in-memory limiter",
            exc_info=exc,
        )
        return InMemoryRateLimiter(limit_per_minute)
