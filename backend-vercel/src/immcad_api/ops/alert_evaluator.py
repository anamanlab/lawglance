from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

import httpx


VALID_COMPARISONS = {"gt", "gte"}


@dataclass(frozen=True)
class AlertRule:
    name: str
    metric_path: str
    comparison: str
    threshold: float
    duration_minutes: int
    min_request_count: int = 0


@dataclass(frozen=True)
class AlertCheckResult:
    name: str
    metric_path: str
    comparison: str
    threshold: float
    duration_minutes: int
    current_value: float | None
    status: str
    message: str


@dataclass(frozen=True)
class OpsAlertReport:
    status: str
    generated_at: str
    metrics_url: str
    total_checks: int
    failing_checks: int
    warning_checks: int
    checks: list[AlertCheckResult]

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "generated_at": self.generated_at,
            "metrics_url": self.metrics_url,
            "total_checks": self.total_checks,
            "failing_checks": self.failing_checks,
            "warning_checks": self.warning_checks,
            "checks": [asdict(check) for check in self.checks],
        }


def build_metrics_url(base_url: str) -> str:
    normalized = base_url.strip().rstrip("/")
    if normalized.endswith("/api"):
        normalized = normalized[:-4]
    if not normalized:
        raise ValueError("Base URL is required to build metrics endpoint URL")
    return f"{normalized}/ops/metrics"


def load_alert_rules(path: str | Path) -> list[AlertRule]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    rules_raw = payload.get("rules")
    if not isinstance(rules_raw, list) or not rules_raw:
        raise ValueError("Alert thresholds config must define a non-empty 'rules' list")

    rules: list[AlertRule] = []
    for raw in rules_raw:
        if not isinstance(raw, dict):
            raise ValueError("Each alert rule must be an object")
        comparison = str(raw.get("comparison", "")).strip().lower()
        if comparison not in VALID_COMPARISONS:
            raise ValueError(
                f"Invalid comparison '{comparison}'. Allowed values: {', '.join(sorted(VALID_COMPARISONS))}"
            )
        rules.append(
            AlertRule(
                name=str(raw["name"]),
                metric_path=str(raw["metric_path"]),
                comparison=comparison,
                threshold=float(raw["threshold"]),
                duration_minutes=int(raw["duration_minutes"]),
                min_request_count=max(0, int(raw.get("min_request_count", 0))),
            )
        )
    return rules


def fetch_ops_metrics(
    *,
    metrics_url: str,
    bearer_token: str | None = None,
    timeout_seconds: float = 10.0,
) -> dict[str, Any]:
    headers: dict[str, str] = {"Accept": "application/json"}
    if bearer_token:
        headers["Authorization"] = f"Bearer {bearer_token}"

    response = httpx.get(metrics_url, headers=headers, timeout=timeout_seconds)
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise ValueError("Metrics response must be a JSON object")
    return payload


def _get_numeric_value(payload: dict[str, Any], metric_path: str) -> float | None:
    current: Any = payload
    for key in metric_path.split("."):
        if not isinstance(current, dict) or key not in current:
            return None
        current = current[key]
    if isinstance(current, bool):
        return None
    if isinstance(current, (int, float)):
        return float(current)
    return None


def evaluate_alert_rules(
    *,
    metrics_payload: dict[str, Any],
    rules: list[AlertRule],
    fail_on_missing: bool = True,
) -> list[AlertCheckResult]:
    results: list[AlertCheckResult] = []
    request_total = _get_numeric_value(metrics_payload, "request_metrics.requests.total")
    for rule in rules:
        if rule.min_request_count > 0:
            if request_total is None:
                results.append(
                    AlertCheckResult(
                        name=rule.name,
                        metric_path=rule.metric_path,
                        comparison=rule.comparison,
                        threshold=rule.threshold,
                        duration_minutes=rule.duration_minutes,
                        current_value=None,
                        status="warn",
                        message=(
                            "Insufficient samples: request_metrics.requests.total missing; "
                            f"requires at least {rule.min_request_count} requests"
                        ),
                    )
                )
                continue
            if request_total < rule.min_request_count:
                results.append(
                    AlertCheckResult(
                        name=rule.name,
                        metric_path=rule.metric_path,
                        comparison=rule.comparison,
                        threshold=rule.threshold,
                        duration_minutes=rule.duration_minutes,
                        current_value=None,
                        status="warn",
                        message=(
                            "Insufficient samples: "
                            f"{request_total:.0f}/{rule.min_request_count} requests in window"
                        ),
                    )
                )
                continue

        current_value = _get_numeric_value(metrics_payload, rule.metric_path)
        if current_value is None:
            status = "fail" if fail_on_missing else "warn"
            results.append(
                AlertCheckResult(
                    name=rule.name,
                    metric_path=rule.metric_path,
                    comparison=rule.comparison,
                    threshold=rule.threshold,
                    duration_minutes=rule.duration_minutes,
                    current_value=None,
                    status=status,
                    message=f"Metric path '{rule.metric_path}' missing or non-numeric",
                )
            )
            continue

        if rule.comparison == "gt":
            breached = current_value > rule.threshold
            comparator = ">"
            healthy_relation = "at or below"
        elif rule.comparison in {"gte", ">="}:
            breached = current_value >= rule.threshold
            comparator = ">="
            healthy_relation = "below"
        else:
            raise ValueError(
                f"Unsupported comparison operator: {rule.comparison!r} for rule {rule.name!r}"
            )
        status = "fail" if breached else "pass"
        message = (
            f"Threshold breached: {current_value} {comparator} {rule.threshold}"
            if breached
            else f"Threshold healthy: {current_value} {healthy_relation} threshold {rule.threshold}"
        )
        results.append(
            AlertCheckResult(
                name=rule.name,
                metric_path=rule.metric_path,
                comparison=rule.comparison,
                threshold=rule.threshold,
                duration_minutes=rule.duration_minutes,
                current_value=current_value,
                status=status,
                message=message,
            )
        )
    return results


def build_alert_report(*, metrics_url: str, checks: list[AlertCheckResult]) -> OpsAlertReport:
    failing_checks = sum(1 for check in checks if check.status == "fail")
    warning_checks = sum(1 for check in checks if check.status == "warn")
    status = "fail" if failing_checks > 0 else "warn" if warning_checks > 0 else "pass"
    return OpsAlertReport(
        status=status,
        generated_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        metrics_url=metrics_url,
        total_checks=len(checks),
        failing_checks=failing_checks,
        warning_checks=warning_checks,
        checks=checks,
    )
