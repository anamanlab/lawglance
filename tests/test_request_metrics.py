from __future__ import annotations

import pytest

from immcad_api.telemetry.request_metrics import RequestMetrics


def test_request_metrics_snapshot_reports_rates_and_percentiles() -> None:
    clock = {"now": 100.0}
    metrics = RequestMetrics(time_fn=lambda: clock["now"])

    metrics.record_api_response(status_code=200, duration_seconds=0.10)
    metrics.record_api_response(status_code=502, duration_seconds=0.40)
    metrics.record_chat_outcome(
        fallback_used=True,
        refusal_used=False,
        constrained_used=True,
        friendly_used=False,
    )
    metrics.record_chat_outcome(
        fallback_used=False,
        refusal_used=True,
        constrained_used=False,
        friendly_used=False,
    )
    metrics.record_chat_outcome(
        fallback_used=False,
        refusal_used=False,
        constrained_used=False,
        friendly_used=True,
    )
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
    metrics.record_document_intake_event(
        trace_id="trace-doc-1",
        client_id="198.51.100.2",
        matter_id="matter-doc-1",
        forum="federal_court_jr",
        file_count=2,
        outcome="accepted",
        ocr_warning_files=1,
        low_confidence_classification_files=1,
        parser_failure_files=0,
    )
    metrics.record_document_intake_event(
        trace_id="trace-doc-2",
        client_id="198.51.100.3",
        matter_id="matter-doc-2",
        forum="iad",
        file_count=0,
        outcome="rejected",
        policy_reason="document_files_missing",
        ocr_warning_files=0,
        low_confidence_classification_files=0,
        parser_failure_files=0,
    )
    metrics.record_document_classification_override_event(
        trace_id="trace-doc-override-1",
        client_id="198.51.100.2",
        matter_id="matter-doc-1",
        forum="federal_court_jr",
        file_id="file-1",
        previous_classification="unclassified",
        new_classification="notice_of_application",
        outcome="updated",
    )
    metrics.record_document_classification_override_event(
        trace_id="trace-doc-override-2",
        client_id="198.51.100.3",
        matter_id="matter-doc-2",
        forum="iad",
        file_id="missing-file",
        previous_classification=None,
        new_classification="decision_under_review",
        outcome="rejected",
        policy_reason="document_file_not_found",
    )
    metrics.record_document_compilation_outcome(
        outcome="compiled",
        trace_id="trace-comp-1",
        client_id="198.51.100.2",
        matter_id="matter-doc-1",
        forum="federal_court_jr",
        route="package",
        http_status=200,
    )
    metrics.record_document_compilation_outcome(
        outcome="blocked",
        policy_reason="document_package_not_ready",
        trace_id="trace-comp-2",
        client_id="198.51.100.3",
        matter_id="matter-doc-2",
        forum="iad",
        route="package_download",
        http_status=409,
    )

    clock["now"] = 160.0
    snapshot = metrics.snapshot()

    assert snapshot["window_seconds"] == pytest.approx(60.0)
    assert snapshot["requests"]["total"] == 2
    assert snapshot["requests"]["rate_per_minute"] == pytest.approx(2.0)
    assert snapshot["errors"]["total"] == 1
    assert snapshot["errors"]["rate"] == pytest.approx(0.5)
    assert snapshot["fallback"]["total"] == 1
    assert snapshot["fallback"]["rate"] == pytest.approx(1 / 3)
    assert snapshot["refusal"]["total"] == 1
    assert snapshot["refusal"]["rate"] == pytest.approx(1 / 3)
    assert snapshot["constrained"]["total"] == 1
    assert snapshot["constrained"]["rate"] == pytest.approx(1 / 3)
    assert snapshot["friendly"]["total"] == 1
    assert snapshot["friendly"]["rate"] == pytest.approx(1 / 3)
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
    assert snapshot["document_intake"]["attempts"] == 2
    assert snapshot["document_intake"]["accepted"] == 1
    assert snapshot["document_intake"]["rejected"] == 1
    assert snapshot["document_intake"]["rejected_rate"] == pytest.approx(0.5)
    assert snapshot["document_intake"]["files_total"] == 2
    assert snapshot["document_intake"]["ocr_warning_files"] == 1
    assert snapshot["document_intake"]["ocr_warning_rate"] == pytest.approx(0.5)
    assert snapshot["document_intake"]["low_confidence_classification_files"] == 1
    assert snapshot["document_intake"]["low_confidence_classification_rate"] == pytest.approx(
        0.5
    )
    assert snapshot["document_intake"]["parser_failure_files"] == 0
    assert snapshot["document_intake"]["parser_failure_rate"] == 0.0
    assert snapshot["document_intake"]["policy_reasons"]["document_files_missing"] == 1
    assert len(snapshot["document_intake"]["audit_recent"]) == 2
    accepted_event, rejected_event = snapshot["document_intake"]["audit_recent"]
    assert accepted_event["trace_id"] == "trace-doc-1"
    assert accepted_event["client_id"] == "198.51.100.2"
    assert accepted_event["matter_id"] == "matter-doc-1"
    assert accepted_event["forum"] == "federal_court_jr"
    assert accepted_event["file_count"] == 2
    assert accepted_event["outcome"] == "accepted"
    assert accepted_event["low_confidence_classification_files"] == 1
    assert "policy_reason" not in accepted_event
    assert accepted_event["timestamp_utc"].endswith("Z")
    assert rejected_event["trace_id"] == "trace-doc-2"
    assert rejected_event["client_id"] == "198.51.100.3"
    assert rejected_event["matter_id"] == "matter-doc-2"
    assert rejected_event["forum"] == "iad"
    assert rejected_event["file_count"] == 0
    assert rejected_event["outcome"] == "rejected"
    assert rejected_event["low_confidence_classification_files"] == 0
    assert rejected_event["policy_reason"] == "document_files_missing"
    assert rejected_event["timestamp_utc"].endswith("Z")
    assert snapshot["document_classification_override"]["attempts"] == 2
    assert snapshot["document_classification_override"]["updated"] == 1
    assert snapshot["document_classification_override"]["rejected"] == 1
    assert snapshot["document_classification_override"]["rejected_rate"] == pytest.approx(
        0.5
    )
    assert (
        snapshot["document_classification_override"]["policy_reasons"][
            "document_file_not_found"
        ]
        == 1
    )
    assert len(snapshot["document_classification_override"]["audit_recent"]) == 2
    updated_override_event, rejected_override_event = snapshot[
        "document_classification_override"
    ]["audit_recent"]
    assert updated_override_event["trace_id"] == "trace-doc-override-1"
    assert updated_override_event["client_id"] == "198.51.100.2"
    assert updated_override_event["matter_id"] == "matter-doc-1"
    assert updated_override_event["forum"] == "federal_court_jr"
    assert updated_override_event["file_id"] == "file-1"
    assert updated_override_event["previous_classification"] == "unclassified"
    assert updated_override_event["new_classification"] == "notice_of_application"
    assert updated_override_event["outcome"] == "updated"
    assert updated_override_event["timestamp_utc"].endswith("Z")
    assert rejected_override_event["trace_id"] == "trace-doc-override-2"
    assert rejected_override_event["client_id"] == "198.51.100.3"
    assert rejected_override_event["matter_id"] == "matter-doc-2"
    assert rejected_override_event["forum"] == "iad"
    assert rejected_override_event["file_id"] == "missing-file"
    assert rejected_override_event["new_classification"] == "decision_under_review"
    assert rejected_override_event["outcome"] == "rejected"
    assert rejected_override_event["policy_reason"] == "document_file_not_found"
    assert rejected_override_event["timestamp_utc"].endswith("Z")
    assert snapshot["document_compilation"]["attempts"] == 2
    assert snapshot["document_compilation"]["compiled"] == 1
    assert snapshot["document_compilation"]["blocked"] == 1
    assert snapshot["document_compilation"]["block_rate"] == pytest.approx(0.5)
    assert (
        snapshot["document_compilation"]["policy_reasons"]["document_package_not_ready"]
        == 1
    )
    assert len(snapshot["document_compilation"]["audit_recent"]) == 2
    compiled_event, blocked_event = snapshot["document_compilation"]["audit_recent"]
    assert compiled_event["outcome"] == "compiled"
    assert compiled_event["trace_id"] == "trace-comp-1"
    assert compiled_event["client_id"] == "198.51.100.2"
    assert compiled_event["matter_id"] == "matter-doc-1"
    assert compiled_event["forum"] == "federal_court_jr"
    assert compiled_event["route"] == "package"
    assert compiled_event["http_status"] == 200
    assert compiled_event["timestamp_utc"].endswith("Z")
    assert blocked_event["outcome"] == "blocked"
    assert blocked_event["trace_id"] == "trace-comp-2"
    assert blocked_event["client_id"] == "198.51.100.3"
    assert blocked_event["matter_id"] == "matter-doc-2"
    assert blocked_event["forum"] == "iad"
    assert blocked_event["route"] == "package_download"
    assert blocked_event["http_status"] == 409
    assert blocked_event["policy_reason"] == "document_package_not_ready"
    assert blocked_event["timestamp_utc"].endswith("Z")
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
    assert snapshot["constrained"]["total"] == 0
    assert snapshot["constrained"]["rate"] == 0.0
    assert snapshot["friendly"]["total"] == 0
    assert snapshot["friendly"]["rate"] == 0.0
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
    assert snapshot["document_intake"]["attempts"] == 0
    assert snapshot["document_intake"]["accepted"] == 0
    assert snapshot["document_intake"]["rejected"] == 0
    assert snapshot["document_intake"]["rejected_rate"] == 0.0
    assert snapshot["document_intake"]["files_total"] == 0
    assert snapshot["document_intake"]["ocr_warning_files"] == 0
    assert snapshot["document_intake"]["ocr_warning_rate"] == 0.0
    assert snapshot["document_intake"]["low_confidence_classification_files"] == 0
    assert snapshot["document_intake"]["low_confidence_classification_rate"] == 0.0
    assert snapshot["document_intake"]["parser_failure_files"] == 0
    assert snapshot["document_intake"]["parser_failure_rate"] == 0.0
    assert snapshot["document_intake"]["policy_reasons"] == {}
    assert snapshot["document_intake"]["audit_recent"] == []
    assert snapshot["document_classification_override"]["attempts"] == 0
    assert snapshot["document_classification_override"]["updated"] == 0
    assert snapshot["document_classification_override"]["rejected"] == 0
    assert snapshot["document_classification_override"]["rejected_rate"] == 0.0
    assert snapshot["document_classification_override"]["policy_reasons"] == {}
    assert snapshot["document_classification_override"]["audit_recent"] == []
    assert snapshot["document_compilation"]["attempts"] == 0
    assert snapshot["document_compilation"]["compiled"] == 0
    assert snapshot["document_compilation"]["blocked"] == 0
    assert snapshot["document_compilation"]["block_rate"] == 0.0
    assert snapshot["document_compilation"]["policy_reasons"] == {}
    assert snapshot["document_compilation"]["audit_recent"] == []
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


def test_request_metrics_tracks_document_compilation_block_rates_and_reasons() -> None:
    metrics = RequestMetrics(time_fn=lambda: 10.0)

    metrics.record_document_compilation_outcome(outcome="compiled")
    metrics.record_document_compilation_outcome(
        outcome="blocked",
        policy_reason="document_package_not_ready",
    )
    metrics.record_document_compilation_outcome(
        outcome="blocked",
        policy_reason="document_translation_requirement_missing",
    )

    snapshot = metrics.snapshot()

    assert snapshot["document_compilation"]["attempts"] == 3
    assert snapshot["document_compilation"]["compiled"] == 1
    assert snapshot["document_compilation"]["blocked"] == 2
    assert snapshot["document_compilation"]["block_rate"] == pytest.approx(2 / 3)
    assert (
        snapshot["document_compilation"]["policy_reasons"]["document_package_not_ready"]
        == 1
    )
    assert (
        snapshot["document_compilation"]["policy_reasons"][
            "document_translation_requirement_missing"
        ]
        == 1
    )
