from __future__ import annotations

from collections import Counter, deque
from datetime import datetime, timezone
import math
from threading import Lock
import time
from typing import Callable


class RequestMetrics:
    def __init__(
        self,
        *,
        max_latency_samples: int = 2048,
        max_export_audit_events: int = 256,
        max_document_intake_audit_events: int = 256,
        time_fn: Callable[[], float] | None = None,
    ) -> None:
        if max_latency_samples < 1:
            raise ValueError("max_latency_samples must be >= 1")
        if max_export_audit_events < 1:
            raise ValueError("max_export_audit_events must be >= 1")
        if max_document_intake_audit_events < 1:
            raise ValueError("max_document_intake_audit_events must be >= 1")
        self._time_fn = time_fn or time.monotonic
        self._started_at = self._time_fn()
        self._lock = Lock()
        self._api_requests = 0
        self._api_errors = 0
        self._chat_requests = 0
        self._chat_fallbacks = 0
        self._chat_refusals = 0
        self._export_attempts = 0
        self._export_allowed = 0
        self._export_blocked = 0
        self._export_fetch_failures = 0
        self._export_too_large = 0
        self._export_policy_reasons: Counter[str] = Counter()
        self._export_audit_events: deque[dict[str, object]] = deque(
            maxlen=max_export_audit_events
        )
        self._document_intake_attempts = 0
        self._document_intake_accepted = 0
        self._document_intake_rejected = 0
        self._document_intake_policy_reasons: Counter[str] = Counter()
        self._document_intake_audit_events: deque[dict[str, object]] = deque(
            maxlen=max_document_intake_audit_events
        )
        self._lawyer_research_requests = 0
        self._lawyer_research_cases_returned_total = 0
        self._lawyer_research_pdf_available_total = 0
        self._lawyer_research_pdf_unavailable_total = 0
        self._lawyer_research_source_unavailable_events = 0
        self._latencies_ms: deque[float] = deque(maxlen=max_latency_samples)

    def record_api_response(self, *, status_code: int, duration_seconds: float) -> None:
        latency_ms = max(duration_seconds * 1000.0, 0.0)
        with self._lock:
            self._api_requests += 1
            if status_code >= 400:
                self._api_errors += 1
            self._latencies_ms.append(latency_ms)

    def record_chat_outcome(self, *, fallback_used: bool, refusal_used: bool) -> None:
        with self._lock:
            self._chat_requests += 1
            if fallback_used:
                self._chat_fallbacks += 1
            if refusal_used:
                self._chat_refusals += 1

    def record_export_outcome(
        self, *, outcome: str, policy_reason: str | None = None
    ) -> None:
        with self._lock:
            self._export_attempts += 1
            if outcome == "allowed":
                self._export_allowed += 1
            elif outcome == "blocked":
                self._export_blocked += 1
            elif outcome == "fetch_failed":
                self._export_fetch_failures += 1
            elif outcome == "too_large":
                self._export_too_large += 1
            if policy_reason:
                self._export_policy_reasons[policy_reason] += 1

    def record_lawyer_research_outcome(
        self,
        *,
        case_count: int,
        pdf_available_count: int,
        pdf_unavailable_count: int,
        source_status: dict[str, str] | None = None,
    ) -> None:
        with self._lock:
            self._lawyer_research_requests += 1
            self._lawyer_research_cases_returned_total += max(case_count, 0)
            self._lawyer_research_pdf_available_total += max(pdf_available_count, 0)
            self._lawyer_research_pdf_unavailable_total += max(pdf_unavailable_count, 0)
            if source_status and any(
                status == "unavailable" for status in source_status.values()
            ):
                self._lawyer_research_source_unavailable_events += 1

    def record_export_audit_event(
        self,
        *,
        trace_id: str,
        client_id: str | None,
        source_id: str,
        case_id: str,
        document_host: str | None,
        user_approved: bool,
        outcome: str,
        policy_reason: str | None = None,
    ) -> None:
        event: dict[str, object] = {
            "timestamp_utc": datetime.now(timezone.utc)
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z"),
            "trace_id": trace_id,
            "client_id": client_id,
            "source_id": source_id,
            "case_id": case_id,
            "document_host": document_host,
            "user_approved": user_approved,
            "outcome": outcome,
        }
        if policy_reason:
            event["policy_reason"] = policy_reason
        with self._lock:
            self._export_audit_events.append(event)

    def record_document_intake_event(
        self,
        *,
        trace_id: str,
        client_id: str | None,
        matter_id: str | None,
        forum: str | None,
        file_count: int,
        outcome: str,
        policy_reason: str | None = None,
    ) -> None:
        normalized_file_count = max(int(file_count), 0)
        event: dict[str, object] = {
            "timestamp_utc": datetime.now(timezone.utc)
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z"),
            "trace_id": trace_id,
            "client_id": client_id,
            "matter_id": matter_id,
            "forum": forum,
            "file_count": normalized_file_count,
            "outcome": outcome,
        }
        if policy_reason:
            event["policy_reason"] = policy_reason
        with self._lock:
            self._document_intake_attempts += 1
            if outcome == "accepted":
                self._document_intake_accepted += 1
            elif outcome == "rejected":
                self._document_intake_rejected += 1
            if policy_reason:
                self._document_intake_policy_reasons[policy_reason] += 1
            self._document_intake_audit_events.append(event)

    def snapshot(self) -> dict[str, object]:
        with self._lock:
            elapsed_seconds = max(self._time_fn() - self._started_at, 1e-9)
            api_requests = self._api_requests
            api_errors = self._api_errors
            chat_requests = self._chat_requests
            chat_fallbacks = self._chat_fallbacks
            chat_refusals = self._chat_refusals
            export_attempts = self._export_attempts
            export_allowed = self._export_allowed
            export_blocked = self._export_blocked
            export_fetch_failures = self._export_fetch_failures
            export_too_large = self._export_too_large
            export_policy_reasons = dict(self._export_policy_reasons)
            export_audit_events = list(self._export_audit_events)
            document_intake_attempts = self._document_intake_attempts
            document_intake_accepted = self._document_intake_accepted
            document_intake_rejected = self._document_intake_rejected
            document_intake_policy_reasons = dict(self._document_intake_policy_reasons)
            document_intake_audit_events = list(self._document_intake_audit_events)
            lawyer_research_requests = self._lawyer_research_requests
            lawyer_research_cases_returned_total = (
                self._lawyer_research_cases_returned_total
            )
            lawyer_research_pdf_available_total = (
                self._lawyer_research_pdf_available_total
            )
            lawyer_research_pdf_unavailable_total = (
                self._lawyer_research_pdf_unavailable_total
            )
            lawyer_research_source_unavailable_events = (
                self._lawyer_research_source_unavailable_events
            )
            latencies = list(self._latencies_ms)

        request_rate_per_minute = (api_requests / elapsed_seconds) * 60.0
        error_rate = (api_errors / api_requests) if api_requests else 0.0
        fallback_rate = (chat_fallbacks / chat_requests) if chat_requests else 0.0
        refusal_rate = (chat_refusals / chat_requests) if chat_requests else 0.0

        return {
            "window_seconds": elapsed_seconds,
            "requests": {
                "total": api_requests,
                "rate_per_minute": request_rate_per_minute,
            },
            "errors": {
                "total": api_errors,
                "rate": error_rate,
            },
            "fallback": {
                "total": chat_fallbacks,
                "rate": fallback_rate,
            },
            "refusal": {
                "total": chat_refusals,
                "rate": refusal_rate,
            },
            "export": {
                "attempts": export_attempts,
                "allowed": export_allowed,
                "blocked": export_blocked,
                "fetch_failures": export_fetch_failures,
                "too_large": export_too_large,
                "policy_reasons": export_policy_reasons,
                "audit_recent": export_audit_events,
            },
            "document_intake": {
                "attempts": document_intake_attempts,
                "accepted": document_intake_accepted,
                "rejected": document_intake_rejected,
                "policy_reasons": document_intake_policy_reasons,
                "audit_recent": document_intake_audit_events,
            },
            "lawyer_research": {
                "requests": lawyer_research_requests,
                "cases_returned_total": lawyer_research_cases_returned_total,
                "cases_per_request": (
                    lawyer_research_cases_returned_total / lawyer_research_requests
                    if lawyer_research_requests
                    else 0.0
                ),
                "pdf_available_total": lawyer_research_pdf_available_total,
                "pdf_unavailable_total": lawyer_research_pdf_unavailable_total,
                "source_unavailable_events": lawyer_research_source_unavailable_events,
            },
            "latency_ms": {
                "sample_count": len(latencies),
                "p50": self._percentile(latencies, 50.0),
                "p95": self._percentile(latencies, 95.0),
                "p99": self._percentile(latencies, 99.0),
            },
        }

    @staticmethod
    def _percentile(values: list[float], percentile: float) -> float:
        if not values:
            return 0.0
        if len(values) == 1:
            return float(values[0])

        ordered = sorted(values)
        rank = (len(ordered) - 1) * (percentile / 100.0)
        lower_index = int(math.floor(rank))
        upper_index = int(math.ceil(rank))
        lower_value = ordered[lower_index]
        upper_value = ordered[upper_index]
        if lower_index == upper_index:
            return float(lower_value)
        blend = rank - lower_index
        return float(lower_value + (upper_value - lower_value) * blend)
