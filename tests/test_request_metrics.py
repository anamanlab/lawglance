from __future__ import annotations

import pytest

from immcad_api.telemetry.request_metrics import RequestMetrics


def test_request_metrics_snapshot_reports_rates_and_percentiles() -> None:
    clock = {"now": 100.0}
    metrics = RequestMetrics(time_fn=lambda: clock["now"])

    metrics.record_api_response(status_code=200, duration_seconds=0.10)
    metrics.record_api_response(status_code=502, duration_seconds=0.40)
    metrics.record_chat_outcome(fallback_used=True, refusal_used=False)
    metrics.record_chat_outcome(fallback_used=False, refusal_used=True)

    clock["now"] = 160.0
    snapshot = metrics.snapshot()

    assert snapshot["window_seconds"] == pytest.approx(60.0)
    assert snapshot["requests"]["total"] == 2
    assert snapshot["requests"]["rate_per_minute"] == pytest.approx(2.0)
    assert snapshot["errors"]["total"] == 1
    assert snapshot["errors"]["rate"] == pytest.approx(0.5)
    assert snapshot["fallback"]["total"] == 1
    assert snapshot["fallback"]["rate"] == pytest.approx(0.5)
    assert snapshot["refusal"]["total"] == 1
    assert snapshot["refusal"]["rate"] == pytest.approx(0.5)
    assert snapshot["latency_ms"]["sample_count"] == 2
    assert snapshot["latency_ms"]["p50"] == pytest.approx(250.0)
    assert snapshot["latency_ms"]["p95"] == pytest.approx(385.0)
    assert snapshot["latency_ms"]["p99"] == pytest.approx(397.0)


def test_request_metrics_snapshot_handles_empty_state() -> None:
    metrics = RequestMetrics(time_fn=lambda: 10.0)
    snapshot = metrics.snapshot()

    assert snapshot["requests"]["total"] == 0
    assert snapshot["requests"]["rate_per_minute"] == 0.0
    assert snapshot["errors"]["total"] == 0
    assert snapshot["errors"]["rate"] == 0.0
    assert snapshot["fallback"]["total"] == 0
    assert snapshot["fallback"]["rate"] == 0.0
    assert snapshot["refusal"]["total"] == 0
    assert snapshot["refusal"]["rate"] == 0.0
    assert snapshot["latency_ms"]["sample_count"] == 0
    assert snapshot["latency_ms"]["p50"] == 0.0
    assert snapshot["latency_ms"]["p95"] == 0.0
    assert snapshot["latency_ms"]["p99"] == 0.0
