from __future__ import annotations

from pathlib import Path

from immcad_api.ops import (
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
        build_metrics_url("https://immcad.example")
        == "https://immcad.example/ops/metrics"
    )


def test_evaluate_alert_rules_marks_threshold_breaches() -> None:
    rules = load_alert_rules(THRESHOLDS_PATH)
    metrics_payload = {
        "request_metrics": {
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
    checks = evaluate_alert_rules(metrics_payload={"request_metrics": {}}, rules=rules)
    report = build_alert_report(metrics_url="https://immcad.example/ops/metrics", checks=checks)

    assert report.status == "fail"
    assert report.failing_checks == len(rules)


def test_evaluate_alert_rules_treats_boolean_metrics_as_missing() -> None:
    checks = evaluate_alert_rules(
        metrics_payload={"request_metrics": {"errors": {"rate": False}}},
        rules=[load_alert_rules(THRESHOLDS_PATH)[0]],
    )
    assert checks[0].current_value is None
    assert checks[0].status == "fail"
