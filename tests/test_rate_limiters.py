from __future__ import annotations

from immcad_api.middleware.rate_limit import InMemoryRateLimiter, RedisRateLimiter


class _FakeRedis:
    def __init__(self) -> None:
        self.store: dict[str, int] = {}
        self.expiries: dict[str, int] = {}

    def incr(self, key: str) -> int:
        self.store[key] = self.store.get(key, 0) + 1
        return self.store[key]

    def expire(self, key: str, ttl_seconds: int) -> None:
        self.expiries[key] = ttl_seconds


def test_in_memory_rate_limiter_blocks_after_limit() -> None:
    limiter = InMemoryRateLimiter(limit_per_minute=2)
    assert limiter.allow("client-a") is True
    assert limiter.allow("client-a") is True
    assert limiter.allow("client-a") is False


def test_redis_rate_limiter_blocks_after_limit() -> None:
    fake_redis = _FakeRedis()
    limiter = RedisRateLimiter(fake_redis, limit_per_minute=2)
    assert limiter.allow("client-a") is True
    assert limiter.allow("client-a") is True
    assert limiter.allow("client-a") is False

