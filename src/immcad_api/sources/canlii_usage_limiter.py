from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from threading import Lock
import time
from typing import Protocol
from uuid import uuid4


class CanLIIUsageLimitExceeded(Exception):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class CanLIIUsageLease(Protocol):
    def release(self) -> None: ...


class CanLIIUsageLimiter(Protocol):
    def acquire(self) -> CanLIIUsageLease: ...


@dataclass(frozen=True)
class CanLIIUsageLimits:
    daily_limit: int = 5_000
    per_second_limit: int = 2
    max_in_flight: int = 1


class _NoOpCanLIIUsageLease:
    def release(self) -> None:
        return None


@dataclass
class _InMemoryCanLIIUsageLease:
    limiter: "InMemoryCanLIIUsageLimiter"
    released: bool = False

    def release(self) -> None:
        if self.released:
            return
        self.released = True
        self.limiter._release()


class InMemoryCanLIIUsageLimiter:
    """Enforces CanLII limits in a single process."""

    def __init__(self, limits: CanLIIUsageLimits) -> None:
        self.limits = limits
        self._lock = Lock()
        self._in_flight = 0
        self._current_day = datetime.now(tz=UTC).date()
        self._daily_count = 0
        self._second_window_start = int(time.time())
        self._second_count = 0

    def _advance_windows(self, now_epoch_seconds: int) -> None:
        now_day = datetime.now(tz=UTC).date()
        if now_day != self._current_day:
            self._current_day = now_day
            self._daily_count = 0

        if now_epoch_seconds != self._second_window_start:
            self._second_window_start = now_epoch_seconds
            self._second_count = 0

    def acquire(self) -> CanLIIUsageLease:
        now_epoch_seconds = int(time.time())
        with self._lock:
            self._advance_windows(now_epoch_seconds)

            if self._in_flight >= self.limits.max_in_flight:
                raise CanLIIUsageLimitExceeded("concurrent_limit")
            if self._second_count >= self.limits.per_second_limit:
                raise CanLIIUsageLimitExceeded("per_second_limit")
            if self._daily_count >= self.limits.daily_limit:
                raise CanLIIUsageLimitExceeded("daily_limit")

            self._in_flight += 1
            self._second_count += 1
            self._daily_count += 1

        return _InMemoryCanLIIUsageLease(limiter=self)

    def _release(self) -> None:
        with self._lock:
            if self._in_flight > 0:
                self._in_flight -= 1


_REDIS_ACQUIRE_SCRIPT = """
local daily_key = KEYS[1]
local second_key = KEYS[2]
local lock_key = KEYS[3]

local lock_token = ARGV[1]
local daily_limit = tonumber(ARGV[2])
local per_second_limit = tonumber(ARGV[3])
local lock_ttl_ms = tonumber(ARGV[4])
local daily_ttl_seconds = tonumber(ARGV[5])
local second_ttl_seconds = tonumber(ARGV[6])

if redis.call('exists', lock_key) == 1 then
  return 1
end

local second_count = tonumber(redis.call('get', second_key) or '0')
if second_count >= per_second_limit then
  return 2
end

local daily_count = tonumber(redis.call('get', daily_key) or '0')
if daily_count >= daily_limit then
  return 3
end

daily_count = redis.call('incr', daily_key)
if daily_count == 1 then
  redis.call('expire', daily_key, daily_ttl_seconds)
end

second_count = redis.call('incr', second_key)
if second_count == 1 then
  redis.call('expire', second_key, second_ttl_seconds)
end

redis.call('psetex', lock_key, lock_ttl_ms, lock_token)
return 0
"""

_REDIS_RELEASE_SCRIPT = """
local lock_key = KEYS[1]
local lock_token = ARGV[1]

local existing = redis.call('get', lock_key)
if existing == lock_token then
  return redis.call('del', lock_key)
end

return 0
"""


@dataclass
class _RedisCanLIIUsageLease:
    limiter: "RedisCanLIIUsageLimiter"
    token: str
    released: bool = False

    def release(self) -> None:
        if self.released:
            return
        self.released = True
        self.limiter._release(self.token)


class RedisCanLIIUsageLimiter:
    def __init__(
        self,
        redis_client,
        limits: CanLIIUsageLimits,
        *,
        lock_ttl_seconds: float = 12.0,
        key_prefix: str = "immcad:canlii",
    ) -> None:
        self.redis_client = redis_client
        self.limits = limits
        self.lock_ttl_ms = max(int(lock_ttl_seconds * 1000), 1_000)
        self.key_prefix = key_prefix

    def _daily_key(self) -> str:
        return f"{self.key_prefix}:daily:{datetime.now(tz=UTC).date().isoformat()}"

    def _second_key(self) -> str:
        return f"{self.key_prefix}:rps:{int(time.time())}"

    def _lock_key(self) -> str:
        return f"{self.key_prefix}:lock"

    def _seconds_until_next_utc_day(self) -> int:
        now = datetime.now(tz=UTC)
        tomorrow = (now + timedelta(days=1)).date()
        next_midnight = datetime.combine(tomorrow, datetime.min.time(), tzinfo=UTC)
        delta = int((next_midnight - now).total_seconds())
        return max(delta, 1)

    def acquire(self) -> CanLIIUsageLease:
        token = str(uuid4())
        result = int(
            self.redis_client.eval(
                _REDIS_ACQUIRE_SCRIPT,
                3,
                self._daily_key(),
                self._second_key(),
                self._lock_key(),
                token,
                self.limits.daily_limit,
                self.limits.per_second_limit,
                self.lock_ttl_ms,
                self._seconds_until_next_utc_day(),
                2,
            )
        )

        if result == 0:
            return _RedisCanLIIUsageLease(limiter=self, token=token)
        if result == 1:
            raise CanLIIUsageLimitExceeded("concurrent_limit")
        if result == 2:
            raise CanLIIUsageLimitExceeded("per_second_limit")
        if result == 3:
            raise CanLIIUsageLimitExceeded("daily_limit")
        raise CanLIIUsageLimitExceeded("unknown_limit")

    def _release(self, token: str) -> None:
        try:
            self.redis_client.eval(_REDIS_RELEASE_SCRIPT, 1, self._lock_key(), token)
        except Exception:
            return None


def build_canlii_usage_limiter(
    *,
    redis_url: str | None,
    limits: CanLIIUsageLimits | None = None,
    lock_ttl_seconds: float = 12.0,
) -> CanLIIUsageLimiter:
    resolved_limits = limits or CanLIIUsageLimits()
    if not redis_url:
        return InMemoryCanLIIUsageLimiter(resolved_limits)

    try:
        import redis

        redis_client = redis.Redis.from_url(
            redis_url,
            socket_timeout=0.5,
            socket_connect_timeout=0.5,
        )
        redis_client.ping()
        return RedisCanLIIUsageLimiter(
            redis_client=redis_client,
            limits=resolved_limits,
            lock_ttl_seconds=lock_ttl_seconds,
        )
    except Exception:
        return InMemoryCanLIIUsageLimiter(resolved_limits)
