# Feature: Canada Document Intake + Filing Readiness

## Table of Contents

- [Goal](#goal)
- [Who This Is For](#who-this-is-for)
- [Client Experience (Minimal Friction)](#client-experience-minimal-friction)
- [Backend Workflow (System Behavior)](#backend-workflow-system-behavior)
- [Required Outputs](#required-outputs)
- [Failure and Recovery Behavior](#failure-and-recovery-behavior)
- [Security and Compliance Requirements](#security-and-compliance-requirements)
- [Differentiation vs Existing Tools](#differentiation-vs-existing-tools)
- [Acceptance Criteria](#acceptance-criteria)
- [Out of Scope (V1)](#out-of-scope-v1)

## Goal

Provide a secure, client-friendly workflow where users can drag-and-drop multiple documents and receive a rule-aware filing readiness package for Canada immigration litigation contexts (Federal Court JR + IRB divisions).

## Who This Is For

- Immigration lawyers and legal staff preparing litigation records and disclosure packages.
- Clients who need a low-friction upload experience without legal-tech complexity.

## Client Experience (Minimal Friction)

1. User selects a matter forum (`federal_court_jr`, `rpd`, `rad`, `iad`, `id`) and optional matter reference.
2. User drags and drops many PDFs/images in one action.
3. Platform starts processing automatically with no per-file required form fields.
4. User sees per-file status:
   - `processed`
   - `needs_review`
   - `failed`
5. User reviews generated outputs and unresolved issues.
6. User exports filing package only when blocking readiness issues are resolved.

Minimal required fields for upload:
- `forum`
- `files[]`

Optional fields:
- `matter_id`
- `language`
- `client_reference`

## Backend Workflow (System Behavior)

For each uploaded file:

1. File safety checks
- extension/content-type allowlist
- max-size guardrail
- upload integrity checks

2. Extraction/OCR stage
- extract embedded text when available
- compute OCR need and confidence signals
- detect page-level legibility warnings

3. Understanding stage
- classify document type (e.g., decision, notice, affidavit, exhibit, translation, identity document)
- normalize filename using deterministic pattern
- detect duplicates and possible ordering issues

4. Readiness policy stage
- evaluate forum-specific required items
- compute blocking issues and missing required elements
- output readiness summary (`ready` / `not_ready`)

5. Package stage
- build ordered table of contents/index
- generate disclosure checklist
- produce procedural cover-letter draft

## Required Outputs

- **Document results list** (per file):
  - original filename
  - normalized filename
  - classification
  - quality status
  - issue codes
- **Readiness summary** (per matter):
  - `is_ready`
  - missing required items
  - blocking issues
  - non-blocking warnings
- **Package preview**:
  - table of contents entries
  - disclosure checklist
  - cover-letter draft

## Failure and Recovery Behavior

- `ocr_required`: image-only or low-text documents are flagged for OCR review.
- `ocr_low_confidence`: extraction succeeded but confidence is low; document remains usable with warning.
- `file_unreadable`: file cannot be parsed; mark as failed and request re-upload.
- `unsupported_file_type`: reject at intake with validation error.
- `upload_size_exceeded`: reject with explicit max-size message.
- `document_package_not_ready`: package export blocked when required items or blocking issues remain.

System behavior principles:
- Never silently drop files.
- Return deterministic machine-readable issue codes.
- Keep partial progress (successful files remain available when one file fails).

## Security and Compliance Requirements

Data handling baseline (Canada-oriented):
- Encrypt in transit (`TLS`) and at rest.
- Role-based access controls for matter/document access.
- Audit logs for upload, review, package generation, and export events.
- Explicit retention/deletion policy per matter.
- No model-training reuse of client-uploaded documents by default.

Compliance anchors:
- PIPEDA safeguards requirements.
- Legal professional confidentiality duties.

## Differentiation vs Existing Tools

This feature is intentionally not a generic legal CRM, bundler, or OCR utility.

Differentiators:
- Canada immigration litigation-specific readiness rules.
- Integrated flow from intake -> quality checks -> rule checks -> package outputs.
- Blocking preflight gates before final package generation.
- Single bulk-upload UX with minimal required fields.

## Acceptance Criteria

- Users can upload 10+ files in one action with one required configuration (`forum`).
- Every file returns deterministic status + issue codes.
- Readiness response explains exactly why matter is not ready.
- Table of contents and disclosure checklist are generated from processed document set.
- Package generation is blocked with explicit reason when blocking issues remain.
- Trace IDs and audit events are emitted for intake and package actions.

## Out of Scope (V1)

- Direct filing submission to courts/tribunals.
- Legal advice generation.
- Fully automated acceptance with no human review path.
- Advanced multilingual translation workflows.

