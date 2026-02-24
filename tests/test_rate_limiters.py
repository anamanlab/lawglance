from __future__ import annotations

import logging
import sys
import types

import pytest

from immcad_api.middleware.rate_limit import (
    InMemoryRateLimiter,
    RedisRateLimiter,
    build_rate_limiter,
)


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


def test_build_rate_limiter_logs_fallback_when_redis_unavailable(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    class _BrokenRedisClient:
        def ping(self) -> None:
            raise RuntimeError("redis unavailable")

    class _BrokenRedis:
        @staticmethod
        def from_url(*_args, **_kwargs):
            return _BrokenRedisClient()

    monkeypatch.setitem(sys.modules, "redis", types.SimpleNamespace(Redis=_BrokenRedis))

    with caplog.at_level(logging.WARNING, logger="immcad_api.rate_limit"):
        limiter = build_rate_limiter(limit_per_minute=10, redis_url="redis://localhost:6379/0")

    assert isinstance(limiter, InMemoryRateLimiter)
    assert "falling back to in-memory limiter" in caplog.text


def test_build_rate_limiter_uses_redis_when_available(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _HealthyRedisClient:
        def ping(self) -> None:
            return None

        def incr(self, _key: str) -> int:
            return 1

        def expire(self, _key: str, _ttl_seconds: int) -> None:
            return None

    class _HealthyRedis:
        @staticmethod
        def from_url(*_args, **_kwargs):
            return _HealthyRedisClient()

    monkeypatch.setitem(sys.modules, "redis", types.SimpleNamespace(Redis=_HealthyRedis))

    limiter = build_rate_limiter(limit_per_minute=10, redis_url="redis://localhost:6379/0")
    assert isinstance(limiter, RedisRateLimiter)
