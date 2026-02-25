from __future__ import annotations

import json
from pathlib import Path

import pytest

from immcad_api.ops import (
    AlertRule,
    build_alert_report,
    build_metrics_url,
    evaluate_alert_rules,
    load_alert_rules,
)

THRESHOLDS_PATH = Path(__file__).resolve().parent.parent / "config" / "ops_alert_thresholds.json"


def test_build_metrics_url_strips_api_suffix() -> None:
    assert (
        build_metrics_url("https://immcad.example/api")
        == "https://immcad.example/ops/metrics"
    )
    assert (
        build_metrics_url("https://immcad.example/api/")
        == "https://immcad.example/ops/metrics"
    )
    assert (
        build_metrics_url("https://immcad.example")
        == "https://immcad.example/ops/metrics"
    )


def test_evaluate_alert_rules_marks_threshold_breaches() -> None:
    rules = load_alert_rules(THRESHOLDS_PATH)
    metrics_payload = {
            "request_metrics": {
            "requests": {"total": 100, "rate_per_minute": 10},
            "errors": {"rate": 0.06},
            "fallback": {"rate": 0.01},
            "refusal": {"rate": 0.1},
            "latency_ms": {"p95": 9000},
        }
    }
    checks = evaluate_alert_rules(metrics_payload=metrics_payload, rules=rules)
    report = build_alert_report(metrics_url="https://immcad.example/ops/metrics", checks=checks)

    assert report.status == "fail"
    assert report.failing_checks == 2
    failing_names = {check.name for check in report.checks if check.status == "fail"}
    assert failing_names == {"error_rate", "latency_p95_ms"}


def test_evaluate_alert_rules_handles_missing_metric_paths_as_failures() -> None:
    rules = load_alert_rules(THRESHOLDS_PATH)
    checks = evaluate_alert_rules(
        metrics_payload={"request_metrics": {"requests": {"total": 100}}},
        rules=rules,
    )
    report = build_alert_report(metrics_url="https://immcad.example/ops/metrics", checks=checks)

    assert report.status == "fail"
    assert report.failing_checks == len(rules)


def test_evaluate_alert_rules_treats_boolean_metrics_as_missing() -> None:
    checks = evaluate_alert_rules(
        metrics_payload={"request_metrics": {"requests": {"total": 100}, "errors": {"rate": False}}},
        rules=[load_alert_rules(THRESHOLDS_PATH)[0]],
    )
    assert checks[0].current_value is None
    assert checks[0].status == "fail"


def test_evaluate_alert_rules_raises_for_invalid_comparison_operator() -> None:
    bad_rule = AlertRule(
        name="bad_rule",
        metric_path="request_metrics.errors.rate",
        comparison="bad-op",
        threshold=0.05,
        duration_minutes=10,
    )
    with pytest.raises(ValueError):
        evaluate_alert_rules(
            metrics_payload={"request_metrics": {"errors": {"rate": 0.01}}},
            rules=[bad_rule],
        )


def test_build_alert_report_returns_warn_when_only_warnings_present() -> None:
    rules = load_alert_rules(THRESHOLDS_PATH)
    checks = evaluate_alert_rules(
        metrics_payload={"request_metrics": {}},
        rules=rules,
        fail_on_missing=False,
    )
    report = build_alert_report(metrics_url="https://immcad.example/ops/metrics", checks=checks)
    assert report.status == "warn"
    assert report.failing_checks == 0
    assert report.warning_checks == len(rules)


def test_evaluate_alert_rules_warns_when_request_volume_is_below_minimum() -> None:
    rules = load_alert_rules(THRESHOLDS_PATH)
    checks = evaluate_alert_rules(
        metrics_payload={
            "request_metrics": {
                "requests": {"total": 6},
                "errors": {"rate": 0.5},
                "fallback": {"rate": 0.5},
                "refusal": {"rate": 0.5},
                "latency_ms": {"p95": 25_000},
            }
        },
        rules=rules,
    )
    report = build_alert_report(metrics_url="https://immcad.example/ops/metrics", checks=checks)

    assert report.status == "warn"
    assert report.failing_checks == 0
    assert report.warning_checks == len(rules)
    assert all(check.status == "warn" for check in checks)


def test_load_alert_rules_supports_warn_breach_status_and_derived_cloudflare_rule() -> None:
    rules = load_alert_rules(THRESHOLDS_PATH)
    warn_rules = [rule for rule in rules if rule.breach_status == "warn"]
    assert warn_rules
    assert any(
        rule.metric_path
        == "derived.cloudflare_free_plan.api_projected_requests_per_day_utilization"
        for rule in warn_rules
    )


def test_evaluate_alert_rules_can_emit_warn_on_breach_for_warn_rule() -> None:
    rule = AlertRule(
        name="cloudflare_budget_warn",
        metric_path="derived.cloudflare_free_plan.api_projected_requests_per_day_utilization",
        comparison="gt",
        threshold=0.7,
        duration_minutes=15,
        breach_status="warn",
    )
    checks = evaluate_alert_rules(
        metrics_payload={"request_metrics": {"requests": {"rate_per_minute": 60.0}}},
        rules=[rule],
    )

    assert len(checks) == 1
    assert checks[0].status == "warn"
    assert checks[0].current_value is not None
    assert checks[0].current_value > 0.7
    assert "Threshold breached (warn)" in checks[0].message


def test_load_alert_rules_rejects_invalid_breach_status(tmp_path: Path) -> None:
    thresholds_path = tmp_path / "ops-alert-thresholds.json"
    thresholds_path.write_text(
        json.dumps(
            {
                "rules": [
                    {
                        "name": "bad_status",
                        "metric_path": "request_metrics.errors.rate",
                        "comparison": "gt",
                        "threshold": 0.05,
                        "duration_minutes": 10,
                        "breach_status": "page-me",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Invalid breach_status"):
        load_alert_rules(thresholds_path)


def test_build_metrics_url_rejects_empty_base_after_normalization() -> None:
    with pytest.raises(ValueError, match="Base URL is required"):
        build_metrics_url(" /api/ ")
