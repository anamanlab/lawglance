from __future__ import annotations

import pytest

from immcad_api.sources.canlii_usage_limiter import (
    CanLIIUsageLimitExceeded,
    CanLIIUsageLimits,
    InMemoryCanLIIUsageLimiter,
)


def test_in_memory_limiter_enforces_concurrency_limit_and_reports_snapshot() -> None:
    limiter = InMemoryCanLIIUsageLimiter(
        CanLIIUsageLimits(daily_limit=10, per_second_limit=10, max_in_flight=1)
    )

    lease = limiter.acquire()
    try:
        with pytest.raises(CanLIIUsageLimitExceeded, match="concurrent_limit"):
            limiter.acquire()
    finally:
        lease.release()

    snapshot = limiter.snapshot()
    assert snapshot["mode"] == "in_memory"
    assert snapshot["limits"]["max_in_flight"] == 1
    assert snapshot["usage"]["daily_count"] >= 1
    assert snapshot["blocked"]["concurrent_limit"] >= 1


def test_in_memory_limiter_enforces_daily_limit_and_reports_remaining() -> None:
    limiter = InMemoryCanLIIUsageLimiter(
        CanLIIUsageLimits(daily_limit=1, per_second_limit=10, max_in_flight=1)
    )

    lease = limiter.acquire()
    lease.release()

    with pytest.raises(CanLIIUsageLimitExceeded, match="daily_limit"):
        limiter.acquire()

    snapshot = limiter.snapshot()
    assert snapshot["limits"]["daily_limit"] == 1
    assert snapshot["usage"]["daily_count"] == 1
    assert snapshot["usage"]["daily_remaining"] == 0
    assert snapshot["blocked"]["daily_limit"] >= 1
