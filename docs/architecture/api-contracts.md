# API Contracts

## Table of Contents

- [Table of Contents](#table-of-contents)
- [`POST /api/chat`](#`post-/api/chat`)
- [`POST /api/search/cases`](#`post-/api/search/cases`)
- [`POST /api/research/lawyer-cases`](#`post-/api/research/lawyer-cases`)
- [`POST /api/export/cases`](#`post-/api/export/cases`)
- [`POST /api/documents/intake`](#`post-/api/documents/intake`)
- [`GET /api/documents/support-matrix`](#`get-/api/documents/support-matrix`)
- [`GET /api/documents/matters/{matter_id}/readiness`](#`get-/api/documents/matters/{matter_id}/readiness`)
- [`PATCH /api/documents/matters/{matter_id}/classification`](#`patch-/api/documents/matters/{matter_id}/classification`)
- [`POST /api/documents/matters/{matter_id}/package`](#`post-/api/documents/matters/{matter_id}/package`)
- [`GET /ops/metrics`](#`get-/ops/metrics`)
- [Error Envelope](#error-envelope)
- [Interface Rules](#interface-rules)

## `POST /api/chat`

Headers:

```text
Authorization: Bearer <token>   # required when IMMCAD_API_BEARER_TOKEN is configured (API_BEARER_TOKEN alias supported)
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
Authorization: Bearer <token>   # required when IMMCAD_API_BEARER_TOKEN is configured (API_BEARER_TOKEN alias supported)
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
      "url": "https://canlii.org/...",
      "source_id": "string",
      "document_url": "https://..."
    }
  ]
}
```

Case-source behavior:

- Official SCC/FC/FCA feeds are the primary search backend when enabled.
- CanLII metadata search is queried as fallback when official feeds are unavailable or return no matches.
- Each result includes `source_id` and `document_url` so `/api/export/cases` can enforce source-scoped export policy.
- `source_id` values are registry-driven (see `data/sources/canada-immigration/registry.json`), and export eligibility is determined by source policy.

CanLII compliance notes:

- The backend uses CanLII metadata endpoints only; it does not fetch or index document text from CanLII.
- Query matching is performed on returned metadata fields in IMMCAD.
- Service-level guardrails enforce CanLII plan limits: `5000/day`, `2 requests/second`, and `1 in-flight request`.

## `POST /api/research/lawyer-cases`

Headers:

```text
Authorization: Bearer <token>   # required when IMMCAD_API_BEARER_TOKEN is configured (API_BEARER_TOKEN alias supported)
```

Request:

```json
{
  "session_id": "session-123456",
  "matter_summary": "Federal Court appeal on procedural fairness and inadmissibility",
  "jurisdiction": "ca",
  "court": "fc",
  "limit": 5
}
```

Response:

```json
{
  "matter_profile": {
    "issue_tags": ["procedural_fairness", "inadmissibility"],
    "target_court": "fc"
  },
  "cases": [
    {
      "case_id": "2026-FC-101",
      "title": "Example v Canada",
      "citation": "2026 FC 101",
      "source_id": "FC_DECISIONS",
      "court": "FC",
      "decision_date": "2026-02-01",
      "url": "https://decisions.fct-cf.gc.ca/fc-cf/decisions/en/item/123456/index.do",
      "document_url": "https://decisions.fct-cf.gc.ca/fc-cf/decisions/en/item/123456/index.do",
      "pdf_status": "available",
      "pdf_reason": "document_url_trusted",
      "export_allowed": true,
      "export_policy_reason": "source_export_allowed",
      "relevance_reason": "This case aligns with the matter issues and appears relevant for FC precedent support.",
      "summary": null
    }
  ],
  "source_status": {
    "official": "ok",
    "canlii": "not_used"
  }
}
```

Notes:

- This endpoint is designed for lawyer-style research workflows and uses matter-profile extraction plus multi-query retrieval behind the scenes.
- `pdf_status` and `pdf_reason` provide explicit document availability transparency.
- If case-search features are disabled in the deployment, this route returns `503 SOURCE_UNAVAILABLE` with `policy_reason=case_search_disabled`.

## `POST /api/export/cases`

Headers:

```text
Authorization: Bearer <token>   # required when IMMCAD_API_BEARER_TOKEN is configured (API_BEARER_TOKEN alias supported)
```

Request:

```json
{
  "source_id": "SCC_DECISIONS",
  "case_id": "2024-scc-3",
  "document_url": "https://decisions.scc-csc.ca/scc-csc/scc-csc/en/item/123/index.do",
  "format": "pdf",
  "user_approved": true
}
```

Approval policy:

- `user_approved` is required for explicit per-request consent.
- Missing or `false` approval is blocked before download, with `403 POLICY_BLOCKED` and `policy_reason=source_export_user_approval_required`.
- `document_url` host must be trusted for the configured `source_id` (exact host or dot-bounded subdomain such as `www.<source-host>`) to prevent cross-domain export fetches.
- `format="pdf"` responses are validated as PDF payloads; non-PDF upstream responses are rejected with `422 VALIDATION_ERROR` and `policy_reason=source_export_non_pdf_payload`.

Missing approval example:

```json
{
  "error": {
    "code": "POLICY_BLOCKED",
    "message": "Case export requires explicit user approval before download",
    "trace_id": "7f9a4b0d18f24cbe",
    "policy_reason": "source_export_user_approval_required"
  }
}
```

Success response:

- Status: `200 OK`
- Body: binary PDF stream.
- Required headers:
  - `x-trace-id`: request trace correlation ID.
  - `x-export-policy-reason`: policy decision used for this export (for example `source_export_allowed`).
  - `content-disposition`: attachment filename.
  - `content-type`: source media type (typically `application/pdf`).

## `POST /api/documents/intake`

Headers:

```text
Authorization: Bearer <token>   # required when IMMCAD_API_BEARER_TOKEN is configured (API_BEARER_TOKEN alias supported)
Content-Type: multipart/form-data
```

Request (`multipart/form-data`):

- `forum` (required): `federal_court_jr | rpd | rad | iad | id | ircc_application`
- `matter_id` (optional): existing matter identifier; backend creates one when omitted
- `files[]` (required): one or more uploads (`application/pdf`, `image/png`, `image/jpeg`, `image/tiff`)

Response:

```json
{
  "matter_id": "matter-abc123def456",
  "forum": "federal_court_jr",
  "results": [
    {
      "file_id": "a1b2c3d4e5",
      "original_filename": "notice.pdf",
      "normalized_filename": "notice-of-application-a1b2c3d4e5.pdf",
      "classification": "notice_of_application",
      "quality_status": "processed",
      "issues": [],
      "issue_details": [],
      "used_ocr": false
    }
  ],
  "blocking_issues": [],
  "warnings": []
}
```

Document-matter scoping rules:

- Matter records are scoped by backend-resolved `request.state.client_id`.
- Follow-up readiness/package requests must resolve to the same client identity to access the matter.
- The Next.js proxy forwards stable identity headers (`x-real-ip`, `x-forwarded-for`, `cf-connecting-ip`, `true-client-ip`) to preserve this scope across proxied requests.

Validation/policy notes:

- Missing files, invalid forum, or file-count overflow return `422 VALIDATION_ERROR`.
- Per-file failures are returned in `results[]` with deterministic issue codes (`unsupported_file_type`, `upload_size_exceeded`, `file_unreadable`) instead of failing the full request.
- Failed results also include `issue_details[]` entries with `code`, `message`, `severity`, and `remediation`; deterministic upload/parser failures include actionable remediation guidance.
- When `DOCUMENT_REQUIRE_HTTPS=true`, non-HTTPS access to `/api/documents/*` is blocked with `400 VALIDATION_ERROR` and `policy_reason=document_https_required`.
- Unsupported `compilation_profile_id` values return `422 VALIDATION_ERROR` with `policy_reason=document_compilation_profile_invalid` and include supported profiles for the selected forum in the error message.

## `GET /api/documents/support-matrix`

Headers:

```text
Authorization: Bearer <token>   # required when IMMCAD_API_BEARER_TOKEN is configured (API_BEARER_TOKEN alias supported)
```

Response:

```json
{
  "supported_profiles_by_forum": {
    "federal_court_jr": ["federal_court_jr_leave", "federal_court_jr_hearing"],
    "rpd": ["rpd"],
    "rad": ["rad"],
    "id": ["id"],
    "iad": ["iad", "iad_sponsorship", "iad_residency", "iad_admissibility"],
    "ircc_application": ["ircc_pr_card_renewal"]
  },
  "unsupported_profile_families": [
    "humanitarian_and_compassionate",
    "prra",
    "work_permit",
    "study_permit",
    "citizenship_proof"
  ]
}
```

## `GET /api/documents/matters/{matter_id}/readiness`

Headers:

```text
Authorization: Bearer <token>   # required when IMMCAD_API_BEARER_TOKEN is configured (API_BEARER_TOKEN alias supported)
```

Response:

```json
{
  "matter_id": "matter-abc123def456",
  "forum": "federal_court_jr",
  "is_ready": false,
  "missing_required_items": ["memorandum"],
  "blocking_issues": ["illegible_pages"],
  "warnings": [],
  "requirement_statuses": [
    {
      "item": "memorandum",
      "status": "missing",
      "rule_scope": "base",
      "reason": "Required to set out legal argument and requested relief."
    }
  ]
}
```

Not-found behavior:

- Returns `404 SOURCE_UNAVAILABLE` with `policy_reason=document_matter_not_found` when the matter ID does not exist in the caller's client scope.

## `PATCH /api/documents/matters/{matter_id}/classification`

Headers:

```text
Authorization: Bearer <token>   # required when IMMCAD_API_BEARER_TOKEN is configured (API_BEARER_TOKEN alias supported)
Content-Type: application/json
```

Request body:

```json
{
  "file_id": "a1b2c3d4e5",
  "classification": "disclosure_package"
}
```

Response:

- Returns the same payload shape as `GET /api/documents/matters/{matter_id}/readiness` with updated readiness/checklist/package metadata based on the override.

Policy behavior:

- Returns `422 VALIDATION_ERROR` with `policy_reason=document_classification_invalid` when the override value is not a supported canonical document type.
- Returns `404 SOURCE_UNAVAILABLE` with `policy_reason=document_file_not_found` when the file ID is not present in the scoped matter.
- Returns `404 SOURCE_UNAVAILABLE` with `policy_reason=document_matter_not_found` when the scoped matter record is unavailable.

## `POST /api/documents/matters/{matter_id}/package`

Headers:

```text
Authorization: Bearer <token>   # required when IMMCAD_API_BEARER_TOKEN is configured (API_BEARER_TOKEN alias supported)
```

Response:

```json
{
  "matter_id": "matter-abc123def456",
  "forum": "federal_court_jr",
  "is_ready": true,
  "table_of_contents": [
    {
      "position": 1,
      "document_type": "notice_of_application",
      "filename": "notice-of-application-a1b2c3d4e5.pdf"
    }
  ],
  "disclosure_checklist": [
    {
      "item": "decision_under_review",
      "status": "present",
      "rule_scope": "base",
      "reason": "Required to identify the administrative decision being challenged."
    }
  ],
  "cover_letter_draft": "Procedural draft text..."
}
```

Policy behavior:

- Returns `409 POLICY_BLOCKED` with `policy_reason=document_package_not_ready` when readiness is not yet satisfied.
- Returns `404 SOURCE_UNAVAILABLE` with `policy_reason=document_matter_not_found` when the scoped matter record is unavailable.

## `GET /ops/metrics`

Purpose:

- Exposes the production observability baseline for incident detection and triage.
- Intended for operations dashboards and alert evaluators.

Headers:

```text
Authorization: Bearer <token>   # required
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
      },
      "audit_recent": [
        {
          "timestamp_utc": "2026-02-25T12:05:10Z",
          "trace_id": "5f7d...",
          "client_id": "203.0.113.10",
          "source_id": "SCC_DECISIONS",
          "case_id": "2024-scc-3",
          "document_host": "decisions.scc-csc.ca",
          "user_approved": true,
          "outcome": "allowed",
          "policy_reason": "source_export_allowed"
        }
      ]
    },
    "lawyer_research": {
      "requests": 14,
      "cases_returned_total": 36,
      "cases_per_request": 2.57,
      "pdf_available_total": 30,
      "pdf_unavailable_total": 6,
      "source_unavailable_events": 1
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
    "code": "VALIDATION_ERROR|PROVIDER_ERROR|SOURCE_UNAVAILABLE|POLICY_BLOCKED|RATE_LIMITED|UNAUTHORIZED",
    "message": "string",
    "trace_id": "string",
    "policy_reason": "string|null"
  }
}
```

Error envelope contract note: `error.trace_id` is required for error responses and must match the `x-trace-id` response header.

## Interface Rules

- All responses include `x-trace-id` header for observability correlation.
- Error responses include `error.trace_id` in the body in addition to `x-trace-id`.
- `GET /ops/metrics` is the canonical endpoint for request rate, error rate, fallback rate, refusal rate, export outcomes, lawyer-research outcomes, and latency percentiles.
- `POST /api/chat` must return at least one citation unless either:
  - response is a policy refusal, or
  - synthetic scaffold citations are disabled and no grounded citations are available (safe constrained response path).
- `ALLOW_SCAFFOLD_SYNTHETIC_CITATIONS` must be set to `false` in `production`/`prod`/`ci`; app startup fails otherwise.
- Provider internals are hidden behind normalized response schema.
