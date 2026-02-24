# CanLII Compliance Runbook

Use this runbook for production key onboarding, runtime enforcement checks, and daily compliance operations.

## Canonical Constraints (from CanLII API access plan)

- Metadata access only (no document content retrieval and no full-text document search through API usage).
- `5000` queries per day.
- `2` requests per second.
- `1` request at a time.

## Technical Enforcement in IMMCAD

- `CanLIIClient` enforces usage limits before outbound calls.
- Limits are enforced as:
  - daily quota guard (`5000/day`)
  - per-second guard (`2 req/s`)
  - concurrent guard (`1 in-flight`)
- Production frontend path disables scaffold fallback responses when backend is unavailable.
- Case search in UI is explicit user-triggered action (not auto-fired per chat request).

## Key Onboarding Checklist

1. Confirm ToS acceptance and keep email approval record in release evidence.
2. Add `CANLII_API_KEY` to deployment secrets for backend environments.
3. Verify key directly:
   - `make canlii-key-verify`
4. Verify end-to-end backend behavior:
   - `IMMCAD_API_BASE_URL=https://<backend> IMMCAD_API_BEARER_TOKEN=<token> make canlii-live-smoke`
5. Confirm `/ops/metrics` contains `canlii_usage_metrics`.

## Runtime Monitoring

Use `/ops/metrics` and monitor `canlii_usage_metrics`:

- `usage.daily_count`
- `usage.daily_remaining`
- `usage.second_count`
- `usage.in_flight`
- `blocked.daily_limit`
- `blocked.per_second_limit`
- `blocked.concurrent_limit`

Alert thresholds:

- Warning at `daily_count >= 4000`.
- Critical at `daily_count >= 4750`.
- Immediate incident if `blocked.daily_limit > 0`.

## Incident Response

If CanLII limits are hit or source is unavailable:

1. Capture trace ID from failed request.
2. Confirm error code (`RATE_LIMITED` or `SOURCE_UNAVAILABLE`).
3. Check `canlii_usage_metrics` in `/ops/metrics`.
4. If daily cap is exhausted, defer case-search traffic until next UTC day.
5. Do not enable synthetic production fallback.

## Audit Evidence to Retain

- CanLII approval email and terms acceptance confirmation.
- Latest `make canlii-key-verify` output.
- Latest `make canlii-live-smoke` output with trace ID.
- Snapshot of `/ops/metrics` including `canlii_usage_metrics`.
