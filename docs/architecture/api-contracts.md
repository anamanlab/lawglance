# API Contracts

## Table of Contents

- [Table of Contents](#table-of-contents)
- [`POST /api/chat`](#`post-/api/chat`)
- [`POST /api/search/cases`](#`post-/api/search/cases`)
- [`GET /ops/metrics`](#`get-/ops/metrics`)
- [Error Envelope](#error-envelope)
- [Interface Rules](#interface-rules)

- [`POST /api/chat`](#`post-/api/chat`)
- [`POST /api/search/cases`](#`post-/api/search/cases`)
- [Error Envelope](#error-envelope)
- [Interface Rules](#interface-rules)

## `POST /api/chat`

Headers:

```text
Authorization: Bearer <token>   # required when API_BEARER_TOKEN is configured
```

Request:

```json
{
  "session_id": "uuid",
  "message": "string",
  "locale": "en-CA",
  "mode": "standard"
}
```

Response:

```json
{
  "answer": "string",
  "citations": [
    {
      "source_id": "string",
      "title": "string",
      "url": "https://...",
      "pin": "section/article/paragraph",
      "snippet": "string"
    }
  ],
  "confidence": "low|medium|high",
  "disclaimer": "string",
  "fallback_used": {
    "used": true,
    "provider": "gemini",
    "reason": "timeout|rate_limit|policy_block|provider_error"
  }
}
```

## Frontend Contract Expectations (Next.js Minimal Chat)

These rules define how the Next.js chat client must consume API envelopes without relying on provider internals.

Success path (`200` + chat payload):

- Treat `answer`, `confidence`, and `disclaimer` as required display fields.
- Always render `disclaimer` below assistant content, including refusal responses.
- Render citations from `citations[]` when present using `title` + `url` as the clickable label/target and `pin`/`snippet` as optional metadata.
- If `fallback_used.used = true`, show a non-blocking status indicator; do not expose provider exception text.

Policy refusal path (`200` + chat payload):

- Detect refusal via `fallback_used.reason = "policy_block"`.
- Show refusal copy as assistant output while keeping normal chat layout.
- Keep disclaimer visible; do not present refusal as system failure.
- Citation section may be empty for refusal responses and should not display placeholder synthetic citations.

Error path (`4xx`/`5xx` + `ErrorEnvelope`):

- Read `error.code` and map to user-safe UI states (`UNAUTHORIZED`, `RATE_LIMITED`, `VALIDATION_ERROR`, `PROVIDER_ERROR`, `POLICY_BLOCKED`).
- Surface a generic failure banner and retry affordance for recoverable failures.
- Capture `x-trace-id` from response headers for telemetry and support correlation.
- If `error.trace_id` exists in the body, it must match `x-trace-id`; frontend logs should record a mismatch as an integration defect.

Trace correlation requirements:

- Persist last seen trace ID per request lifecycle event in frontend telemetry.
- Include trace ID in client-side error events and support-copy UI.
- Prefer header `x-trace-id` as canonical value; use body `error.trace_id` only when needed for body-only consumers.


Case-law fallback behavior:

- `development` (and non-prod environments): if CanLII is unavailable, deterministic scaffold case results may be returned.
- `production`/`prod`/`ci`: if CanLII is unavailable (including missing API key), API returns `503` with `ErrorEnvelope` (`code=SOURCE_UNAVAILABLE`) and matching `x-trace-id`; synthetic scaffold cases are not returned.

Trace ID behavior for `POST /api/chat`:

- Canonical location for all responses: `x-trace-id` HTTP header.
- Error responses also duplicate the value in `error.trace_id` for body-only clients.

Examples:

```text
Success (200):
  Header: x-trace-id: 8f0b4a...
  Body: ChatResponse (no top-level trace_id field)
Policy refusal (200):
  Header: x-trace-id: 4ca2d9...
  Body: ChatResponse with fallback_used.reason = "policy_block"
Auth/rate-limit/validation/provider error (4xx/5xx):
  Header: x-trace-id: 2b77ef...
  Body: ErrorEnvelope.error.trace_id = "2b77ef..."
```

## `POST /api/search/cases`

Headers:

```text
Authorization: Bearer <token>   # required when API_BEARER_TOKEN is configured
```

Request:

```json
{
  "query": "express entry inadmissibility",
  "jurisdiction": "ca",
  "court": "fct",
  "limit": 10
}
```

Response:

```json
{
  "results": [
    {
      "case_id": "string",
      "title": "string",
      "citation": "string",
      "decision_date": "YYYY-MM-DD",
      "url": "https://canlii.org/..."
    }
  ]
}
```

CanLII compliance notes:

- The backend uses CanLII metadata endpoints only; it does not fetch or index document text from CanLII.
- Query matching is performed on returned metadata fields in IMMCAD.
- Service-level guardrails enforce CanLII plan limits: `5000/day`, `2 requests/second`, and `1 in-flight request`.

## `GET /ops/metrics`

Purpose:

- Exposes the production observability baseline for incident detection and triage.
- Intended for operations dashboards and alert evaluators.

Headers:

```text
Authorization: Bearer <token>   # always required
```

Response:

```json
{
  "request_metrics": {
    "window_seconds": 120.5,
    "requests": {
      "total": 350,
      "rate_per_minute": 174.2
    },
    "errors": {
      "total": 8,
      "rate": 0.0228
    },
    "fallback": {
      "total": 32,
      "rate": 0.0914
    },
    "refusal": {
      "total": 41,
      "rate": 0.1171
    },
    "export": {
      "attempts": 12,
      "allowed": 9,
      "blocked": 2,
      "fetch_failures": 1,
      "too_large": 0,
      "policy_reasons": {
        "source_export_allowed": 9,
        "source_export_blocked_by_policy": 2,
        "source_export_fetch_failed": 1
      }
    },
    "latency_ms": {
      "sample_count": 350,
      "p50": 840.4,
      "p95": 4120.7,
      "p99": 7110.2
    }
  },
  "provider_routing_metrics": {
    "openai": {
      "success": 300,
      "failure": 18
    },
    "gemini": {
      "success": 50,
      "fallback_success": 32
    }
  }
}
```

## Error Envelope

```json
{
  "error": {
    "code": "VALIDATION_ERROR|PROVIDER_ERROR|POLICY_BLOCKED|RATE_LIMITED|UNAUTHORIZED",
    "message": "string",
    "trace_id": "string"
  }
}
```

Error envelope contract note: `error.trace_id` is required for error responses and must match the `x-trace-id` response header.

## Interface Rules

- All responses include `x-trace-id` header for observability correlation.
- Error responses include `error.trace_id` in the body in addition to `x-trace-id`.
- `GET /ops/metrics` is the canonical endpoint for request rate, error rate, fallback rate, refusal rate, export policy outcomes, and latency percentiles.
- `POST /api/chat` must return at least one citation unless either:
  - response is a policy refusal, or
  - synthetic scaffold citations are disabled and no grounded citations are available (safe constrained response path).
- `ALLOW_SCAFFOLD_SYNTHETIC_CITATIONS` must be set to `false` in `production`/`prod`/`ci`; app startup fails otherwise.
- Provider internals are hidden behind normalized response schema.
