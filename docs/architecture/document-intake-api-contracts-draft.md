# Document Intake API Contracts (Draft)

## Table of Contents

- [Scope](#scope)
- [`POST /api/documents/intake`](#post-apidocumentsintake)
- [`GET /api/documents/matters/{matter_id}/readiness`](#get-apidocumentsmattersmatter_idreadiness)
- [`POST /api/documents/matters/{matter_id}/package`](#post-apidocumentsmattersmatter_idpackage)
- [Issue Codes](#issue-codes)
- [Error Envelope](#error-envelope)
- [Interface Rules](#interface-rules)

## Scope

Draft contract for documentation-first alignment before implementation.

All endpoints follow existing trace and error envelope conventions:
- `x-trace-id` response header required.
- error body uses shared `ErrorEnvelope` pattern.

## `POST /api/documents/intake`

Purpose:
- Accept multi-file upload for one matter and return per-file analysis results.

Request:
- Content-Type: `multipart/form-data`
- Fields:
  - `forum`: `federal_court_jr|rpd|rad|iad|id` (required)
  - `matter_id`: string (optional)
  - `files`: one or more file entries (required)

Response (`200`):

```json
{
  "matter_id": "matter-abc123",
  "forum": "federal_court_jr",
  "results": [
    {
      "file_id": "file-001",
      "original_filename": "Scan_001.pdf",
      "normalized_filename": "affidavit-client-2026-02-26-file-001.pdf",
      "classification": "affidavit",
      "quality_status": "needs_review",
      "issues": ["ocr_low_confidence"]
    }
  ],
  "blocking_issues": ["illegible_pages"],
  "warnings": ["translation_declaration_missing"]
}
```

## `GET /api/documents/matters/{matter_id}/readiness`

Purpose:
- Return deterministic readiness summary for filing package generation.

Response (`200`):

```json
{
  "matter_id": "matter-abc123",
  "forum": "federal_court_jr",
  "is_ready": false,
  "missing_required_items": [
    "memorandum",
    "affidavit"
  ],
  "blocking_issues": [
    "illegible_pages"
  ],
  "warnings": [
    "ocr_low_confidence"
  ]
}
```

## `POST /api/documents/matters/{matter_id}/package`

Purpose:
- Build package outputs (TOC/disclosure/cover-letter draft) when readiness permits.

Response (`200`):

```json
{
  "matter_id": "matter-abc123",
  "forum": "federal_court_jr",
  "table_of_contents": [
    {
      "position": 1,
      "document_type": "notice_of_application",
      "filename": "notice-of-application-001.pdf"
    }
  ],
  "disclosure_checklist": [
    {
      "item": "decision_under_review",
      "status": "present"
    },
    {
      "item": "memorandum",
      "status": "missing"
    }
  ],
  "cover_letter_draft": "Procedural draft text...",
  "is_ready": false
}
```

Blocked response (`409`):

```json
{
  "error": {
    "code": "POLICY_BLOCKED",
    "message": "Document package is not ready for generation",
    "trace_id": "trace-123",
    "policy_reason": "document_package_not_ready"
  }
}
```

## Issue Codes

Initial issue code set:
- `ocr_required`
- `ocr_low_confidence`
- `file_unreadable`
- `unsupported_file_type`
- `upload_size_exceeded`
- `duplicate_document_candidate`
- `document_order_unresolved`
- `translation_declaration_missing`
- `illegible_pages`

## Error Envelope

```json
{
  "error": {
    "code": "VALIDATION_ERROR|POLICY_BLOCKED|SOURCE_UNAVAILABLE|RATE_LIMITED|UNAUTHORIZED",
    "message": "string",
    "trace_id": "string",
    "policy_reason": "optional-string"
  }
}
```

## Interface Rules

- Multi-file upload must be supported in one request.
- Partial success is allowed: invalid files are reported individually without discarding successful files.
- `GET readiness` must be deterministic for identical document state.
- `POST package` must not proceed when blocking readiness issues exist.
- All responses must include `x-trace-id`.

