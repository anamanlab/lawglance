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
    metrics.record_export_outcome(
        outcome="allowed", policy_reason="source_export_allowed"
    )
    metrics.record_export_outcome(
        outcome="blocked",
        policy_reason="source_export_blocked_by_policy",
    )
    metrics.record_export_outcome(
        outcome="fetch_failed", policy_reason="source_export_fetch_failed"
    )
    metrics.record_lawyer_research_outcome(
        case_count=2,
        pdf_available_count=1,
        pdf_unavailable_count=1,
        source_status={"official": "ok", "canlii": "not_used"},
    )
    metrics.record_export_audit_event(
        trace_id="trace-1",
        client_id="203.0.113.10",
        source_id="SCC_DECISIONS",
        case_id="scc-2024-3",
        document_host="decisions.scc-csc.ca",
        user_approved=True,
        outcome="allowed",
        policy_reason="source_export_allowed",
    )

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
    assert snapshot["export"]["attempts"] == 3
    assert snapshot["export"]["allowed"] == 1
    assert snapshot["export"]["blocked"] == 1
    assert snapshot["export"]["fetch_failures"] == 1
    assert snapshot["export"]["too_large"] == 0
    assert snapshot["export"]["policy_reasons"]["source_export_allowed"] == 1
    assert snapshot["export"]["policy_reasons"]["source_export_blocked_by_policy"] == 1
    assert snapshot["export"]["policy_reasons"]["source_export_fetch_failed"] == 1
    assert len(snapshot["export"]["audit_recent"]) == 1
    assert snapshot["export"]["audit_recent"][0]["trace_id"] == "trace-1"
    assert snapshot["export"]["audit_recent"][0]["client_id"] == "203.0.113.10"
    assert snapshot["export"]["audit_recent"][0]["source_id"] == "SCC_DECISIONS"
    assert snapshot["export"]["audit_recent"][0]["case_id"] == "scc-2024-3"
    assert snapshot["export"]["audit_recent"][0]["document_host"] == "decisions.scc-csc.ca"
    assert snapshot["export"]["audit_recent"][0]["user_approved"] is True
    assert snapshot["export"]["audit_recent"][0]["outcome"] == "allowed"
    assert (
        snapshot["export"]["audit_recent"][0]["policy_reason"]
        == "source_export_allowed"
    )
    assert snapshot["export"]["audit_recent"][0]["timestamp_utc"].endswith("Z")
    assert snapshot["lawyer_research"]["requests"] == 1
    assert snapshot["lawyer_research"]["cases_returned_total"] == 2
    assert snapshot["lawyer_research"]["cases_per_request"] == pytest.approx(2.0)
    assert snapshot["lawyer_research"]["pdf_available_total"] == 1
    assert snapshot["lawyer_research"]["pdf_unavailable_total"] == 1
    assert snapshot["lawyer_research"]["source_unavailable_events"] == 0
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
    assert snapshot["export"]["attempts"] == 0
    assert snapshot["export"]["allowed"] == 0
    assert snapshot["export"]["blocked"] == 0
    assert snapshot["export"]["fetch_failures"] == 0
    assert snapshot["export"]["too_large"] == 0
    assert snapshot["export"]["policy_reasons"] == {}
    assert snapshot["export"]["audit_recent"] == []
    assert snapshot["lawyer_research"]["requests"] == 0
    assert snapshot["lawyer_research"]["cases_returned_total"] == 0
    assert snapshot["lawyer_research"]["cases_per_request"] == 0.0
    assert snapshot["lawyer_research"]["pdf_available_total"] == 0
    assert snapshot["lawyer_research"]["pdf_unavailable_total"] == 0
    assert snapshot["lawyer_research"]["source_unavailable_events"] == 0
    assert snapshot["latency_ms"]["sample_count"] == 0
    assert snapshot["latency_ms"]["p50"] == 0.0
    assert snapshot["latency_ms"]["p95"] == 0.0
    assert snapshot["latency_ms"]["p99"] == 0.0


def test_lawyer_research_source_unavailable_events_count_per_request() -> None:
    metrics = RequestMetrics(time_fn=lambda: 10.0)
    metrics.record_lawyer_research_outcome(
        case_count=0,
        pdf_available_count=0,
        pdf_unavailable_count=0,
        source_status={"official": "unavailable", "canlii": "unavailable"},
    )

    snapshot = metrics.snapshot()
    assert snapshot["lawyer_research"]["requests"] == 1
    assert snapshot["lawyer_research"]["source_unavailable_events"] == 1
