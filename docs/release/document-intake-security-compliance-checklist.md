# Document Intake Security and Compliance Checklist

Use this checklist before enabling document intake in staging/production.

## Data Protection

- [ ] TLS enforced for all upload and retrieval endpoints. (Runtime gate now available via `DOCUMENT_REQUIRE_HTTPS`; deployment-side HTTPS termination verification still pending.)
- [ ] Encryption at rest configured for stored uploaded files. (Deployment/storage control; pending verification.)
- [ ] Access controls verify matter-level authorization for upload/read/package actions. (Client-scope isolation exists; full auth policy still pending.)
- [x] Audit trail records upload, classification override, and package generation events. (Upload intake, classification override, and package-generation audit streams are now emitted via `/ops/metrics` audit fields.)
- [ ] Data retention and deletion policy documented and implemented.

## Upload Safety Controls

- [x] Allowed content types are enforced (`application/pdf` and approved image formats only).
- [x] Maximum file size is configured and tested.
- [x] Maximum files per request is configured and tested.
- [x] Unsupported or malformed file payloads return structured validation errors.
- [x] Upload pipeline returns deterministic issue codes for failed/partial outcomes.

## Procedural Reliability Controls

- [x] Forum-specific required-item policy exists for `federal_court_jr`, `rpd`, `rad`, `iad`, `id`.
- [x] Package generation is blocked when required items are missing.
- [x] Readiness endpoint returns machine-readable missing items and blocking issues.
- [x] Cover-letter/disclosure output is procedural (non-advisory) and includes unresolved items section.

## OCR and Quality Controls

- [x] OCR-required and low-confidence thresholds are configured.
- [x] Page-level legibility checks are enabled.
- [x] Unreadable files are flagged as `failed` with user-actionable remediation guidance. (`DocumentIntakeResult.issue_details[]` now returns `code/message/severity/remediation` for unreadable/type/size deterministic failures.)
- [x] Manual review path exists for uncertain classification or quality outcomes.

## Compliance and Legal Duties

- [ ] PIPEDA safeguards principle controls are mapped to implementation controls.
- [ ] Confidentiality obligations for legal professionals are reflected in access, logging, and support procedures.
- [ ] No uploaded client document content is reused for model training by default.
- [ ] Exported package handling policy is documented for support and operations teams.

## Operational Readiness

- [x] Metrics include intake volume, failure rate, OCR warning rate, and package block rate. (`/ops/metrics` now includes intake rejected/ocr-warning rates and route-level compilation audit events.)
- [x] Alert thresholds are defined for sustained upload failures and parser errors. (`document_intake_rejected_rate` + `document_intake_parser_failure_rate` rules in `config/ops_alert_thresholds.json`.)
- [x] Incident runbook includes intake failure triage and rollback steps. (See `docs/release/document-intake-incident-runbook.md`.)
- [x] Staging smoke test includes multi-file upload, readiness check, and package-block behavior.

## Sign-off

- Reviewer:
- Date:
- Notes:
