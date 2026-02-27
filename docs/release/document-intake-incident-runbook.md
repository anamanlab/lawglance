# Document Intake Incident Runbook (Triage + Rollback)

Use this runbook when document upload/readiness/package reliability degrades in staging or production.

Scope:
- `POST /api/documents/intake`
- `GET /api/documents/matters/{matter_id}/readiness`
- `PATCH /api/documents/matters/{matter_id}/classification`
- `POST /api/documents/matters/{matter_id}/package`
- `GET /api/documents/matters/{matter_id}/package/download`

## 1) Detection Triggers

Treat this as an active intake incident when either threshold is breached for at least 10 minutes with at least 20 requests in the metrics window:

- `request_metrics.document_intake.rejected_rate > 0.25`
- `request_metrics.document_intake.parser_failure_rate > 0.15`

Threshold source: `config/ops_alert_thresholds.json`.

## 2) Immediate Evidence Capture

Set auth context and capture a metrics snapshot:

```bash
export IMMCAD_API_BASE_URL=https://immcad-api.arkiteto.dpdns.org
export IMMCAD_API_BEARER_TOKEN='<ops-token>'

curl -sS "${IMMCAD_API_BASE_URL}/ops/metrics" \
  -H "Authorization: Bearer ${IMMCAD_API_BEARER_TOKEN}" \
  | jq '.request_metrics.document_intake, .request_metrics.document_compilation'
```

Run threshold evaluation and persist report:

```bash
make ops-alert-eval
cat artifacts/ops/ops-alert-eval.json
```

Capture these fields in the incident record:
- `request_metrics.document_intake.rejected_rate`
- `request_metrics.document_intake.parser_failure_rate`
- `request_metrics.document_intake.policy_reasons`
- `request_metrics.document_intake.audit_recent`
- `request_metrics.document_classification_override.policy_reasons`
- `request_metrics.document_classification_override.audit_recent`
- `request_metrics.document_compilation.policy_reasons`
- `request_metrics.document_compilation.audit_recent`

## 3) Triage Decision Matrix

1. Parser failure dominant:
   - Signal: high `parser_failure_rate` and frequent `file_unreadable` in intake audit events.
   - Likely causes: malformed payload surge, parser/OCR regressions, corrupted upstream files.

2. Validation rejection dominant:
   - Signal: high `rejected_rate` with policy reasons like `document_files_missing`, `document_file_count_exceeded`, `document_forum_invalid`.
   - Likely causes: client integration drift or abusive request patterns.

3. Compilation-path degradation:
   - Signal: spikes in `document_package_not_ready`, `document_compiled_artifact_unavailable`, or `document_matter_not_found` in compilation audit events.
   - Likely causes: matter-scope identity mismatch, incomplete intake payload quality, binder path instability.

## 4) Stabilization Actions

Apply least-disruptive controls first:

1. Reduce intake pressure:
   - lower `DOCUMENT_UPLOAD_MAX_FILES`
   - lower `DOCUMENT_UPLOAD_MAX_BYTES`
2. Narrow accepted content types temporarily:
   - set `DOCUMENT_ALLOWED_CONTENT_TYPES=application/pdf`
3. Redeploy with constrained settings and re-check metrics.
4. If still breaching after two consecutive 10-minute windows, trigger rollback.

## 5) Rollback Procedure

1. Freeze promotion and announce incident in release channel.
2. Roll back frontend/backend workers to last known-good versions (see `docs/release/pre-deploy-command-sheet-2026-02-25.md`, rollback section).
3. Re-run staging smoke and document-intake sanity path:
   - intake -> readiness -> package (and download when compiled mode is enabled).
4. Confirm post-rollback alert status is `pass`/approved `warn`.
5. Keep incident open until two consecutive healthy windows are observed.

## 6) Exit Criteria

- `document_intake.rejected_rate <= 0.10`
- `document_intake.parser_failure_rate <= 0.05`
- No sustained growth in compilation blocked outcomes tied to intake regressions.
- Latest `make ops-alert-eval` report shows no fail status for intake rules.

## 7) Post-Incident Follow-Up

1. Add timeline + trace IDs from `audit_recent` fields.
2. Attach `artifacts/ops/ops-alert-eval.json`.
3. Record root cause and preventive action.
4. Update `docs/release/known-issues.md` if residual risk remains.
