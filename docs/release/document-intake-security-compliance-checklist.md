# Document Intake Security and Compliance Checklist

Use this checklist before enabling document intake in staging/production.

## Data Protection

- [ ] TLS enforced for all upload and retrieval endpoints.
- [ ] Encryption at rest configured for stored uploaded files.
- [ ] Access controls verify matter-level authorization for upload/read/package actions.
- [ ] Audit trail records upload, classification override, and package generation events.
- [ ] Data retention and deletion policy documented and implemented.

## Upload Safety Controls

- [ ] Allowed content types are enforced (`application/pdf` and approved image formats only).
- [ ] Maximum file size is configured and tested.
- [ ] Maximum files per request is configured and tested.
- [ ] Unsupported or malformed file payloads return structured validation errors.
- [ ] Upload pipeline returns deterministic issue codes for failed/partial outcomes.

## Procedural Reliability Controls

- [ ] Forum-specific required-item policy exists for `federal_court_jr`, `rpd`, `rad`, `iad`, `id`.
- [ ] Package generation is blocked when required items are missing.
- [ ] Readiness endpoint returns machine-readable missing items and blocking issues.
- [ ] Cover-letter/disclosure output is procedural (non-advisory) and includes unresolved items section.

## OCR and Quality Controls

- [ ] OCR-required and low-confidence thresholds are configured.
- [ ] Page-level legibility checks are enabled.
- [ ] Unreadable files are flagged as `failed` with user-actionable remediation guidance.
- [ ] Manual review path exists for uncertain classification or quality outcomes.

## Compliance and Legal Duties

- [ ] PIPEDA safeguards principle controls are mapped to implementation controls.
- [ ] Confidentiality obligations for legal professionals are reflected in access, logging, and support procedures.
- [ ] No uploaded client document content is reused for model training by default.
- [ ] Exported package handling policy is documented for support and operations teams.

## Operational Readiness

- [ ] Metrics include intake volume, failure rate, OCR warning rate, and package block rate.
- [ ] Alert thresholds are defined for sustained upload failures and parser errors.
- [ ] Incident runbook includes intake failure triage and rollback steps.
- [ ] Staging smoke test includes multi-file upload, readiness check, and package-block behavior.

## Sign-off

- Reviewer:
- Date:
- Notes:

