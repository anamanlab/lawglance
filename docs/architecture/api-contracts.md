# API Contracts

## Table of Contents

- [Table of Contents](#table-of-contents)
- [`POST /api/chat`](#`post-/api/chat`)
- [`POST /api/search/cases`](#`post-/api/search/cases`)
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

Case-law fallback behavior:

- `development` (and non-prod environments): if CanLII is unavailable, deterministic scaffold case results may be returned.
- `production`/`prod`/`ci`: if CanLII is unavailable (including missing API key), API returns `502` with `ErrorEnvelope` (`code=PROVIDER_ERROR`) and matching `x-trace-id`; synthetic scaffold cases are not returned.

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
- `POST /api/chat` must return at least one citation unless either:
  - response is a policy refusal, or
  - synthetic scaffold citations are disabled and no grounded citations are available (safe constrained response path).
- `ALLOW_SCAFFOLD_SYNTHETIC_CITATIONS` must be set to `false` in `production`/`prod`/`ci`; app startup fails otherwise.
- Provider internals are hidden behind normalized response schema.
