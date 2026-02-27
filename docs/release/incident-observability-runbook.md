# Incident Observability Runbook (Canada Scope)

Use this runbook when API health degrades for Canada immigration/citizenship workflows.

## 1) Pull Baseline Telemetry

```bash
curl -sS http://localhost:8000/ops/metrics | jq .
```

Key fields:

- `request_metrics.requests.rate_per_minute`
- `request_metrics.errors.rate`
- `request_metrics.fallback.rate`
- `request_metrics.refusal.rate`
- `request_metrics.latency_ms.p50`
- `request_metrics.latency_ms.p95`
- `request_metrics.latency_ms.p99`
- `request_metrics.document_intake.rejected_rate`
- `request_metrics.document_intake.parser_failure_rate`
- `request_metrics.document_classification_override.rejected_rate`

## 2) Alert Threshold Triage

Use these thresholds to classify severity:

- `request_metrics.errors.rate > 0.05` for 10 minutes: investigate provider failures and API validation/auth regressions.
- `request_metrics.fallback.rate > 0.20` for 10 minutes: primary provider instability likely; verify OpenAI health and circuit-breaker state.
- `request_metrics.refusal.rate > 0.35` for 15 minutes: potential policy matcher regression or adversarial prompt surge.
- `request_metrics.latency_ms.p95 > 8000` for 10 minutes: degraded user experience; inspect provider latency and rate-limit pressure.
- `request_metrics.document_intake.rejected_rate > 0.25` for 10 minutes (20+ requests): intake reliability degradation; inspect upload validation/client integration.
- `request_metrics.document_intake.parser_failure_rate > 0.15` for 10 minutes (20+ requests): parser/readability failure surge; inspect payload quality and extraction path.

For intake-specific triage and rollback steps, use `docs/release/document-intake-incident-runbook.md`.

## 3) Trace-ID Correlation Path

For any failing request:

1. Capture `x-trace-id` from response headers.
2. Confirm the same ID in response body `error.trace_id` for error envelopes.
3. Search structured audit logs for matching `audit_event.trace_id`.
4. Correlate timestamp window with `/ops/metrics` snapshot and provider routing counters.

This is the canonical cross-layer path:

`HTTP response header (x-trace-id)` -> `error.trace_id` (when error) -> `immcad_api.audit` log `audit_event.trace_id` -> provider routing telemetry.

## 4) Stabilization Actions

- If fallback surge + provider errors: disable unstable provider traffic via deployment config and keep ordered fallback active.
- If refusal surge without policy incident reports: inspect recent policy-regex changes and replay jurisdiction suite.
- If latency spike with low error rate: inspect upstream dependency latency and rate limiter saturation.

Operational smoke bundle for Cloudflare free-tier path:

```bash
export IMMCAD_API_BASE_URL=https://immcad-api.arkiteto.dpdns.org
export IMMCAD_FRONTEND_URL=https://immcad.arkiteto.dpdns.org
export IMMCAD_API_BEARER_TOKEN='<token>'
make free-tier-runtime-validate
```

## 5) Recovery Exit Criteria

- `errors.rate <= 0.02`
- `fallback.rate <= 0.10`
- `latency_ms.p95 <= 8000`
- No unresolved trace-linked provider errors in current on-call window.

After closure, attach the `/ops/metrics` snapshot and representative trace IDs to the incident record.
