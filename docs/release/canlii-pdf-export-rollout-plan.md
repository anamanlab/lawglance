# CanLII PDF Export Rollout Plan

This plan defines how to safely enable CanLII case PDF export in IMMCAD only after explicit legal/compliance approval.

## Current State (as of 2026-02-25)

- CanLII is treated as metadata-first fallback for case search.
- CanLII export is policy-blocked by default:
  - `CANLII_CASE_BROWSE.export_fulltext_allowed=false`
  - `CANLII_CASE_CITATOR.export_fulltext_allowed=false`
- Strict export host checks are source-registry driven.
- Result: CanLII search results can be shown, but export is intentionally unavailable.

## Prerequisites (Hard Gate)

Complete all before any code switch:

1. Legal confirms terms allow PDF export/download for our usage.
2. Compliance signs off source-policy changes (owner + review date updated).
3. Release manager approves staged rollout and rollback criteria.

If any item is missing, keep CanLII export disabled.

## Technical Workstream

1. Source policy update

- Update `config/source_policy.yaml`:
  - `CANLII_CASE_BROWSE.export_fulltext_allowed=true` (if approved)
  - optionally `CANLII_CASE_CITATOR.export_fulltext_allowed=true` (if approved)
- Mirror policy changes to deployment mirror:
  - `backend-vercel/config/source_policy.yaml`

2. Source registry host alignment

- Ensure CanLII source URL host reflects export host validation behavior.
- If export URLs are under `www.canlii.org`, the registry source URL must align so host checks pass.
- Update:
  - `data/sources/canada-immigration/registry.json`

3. Route/test coverage

- Add/adjust tests in `tests/test_export_policy_gate.py` for:
  - allowed CanLII export path when gate enabled
  - redirect-host validation still enforced
  - non-PDF rejection still enforced
  - metrics audit outcome for allowed CanLII export
- Keep existing deny tests for disallowed CanLII paths until policy flip is complete.

4. Frontend UX

- Verify `export_allowed` + `export_policy_reason` reflect new policy state from `/api/search/cases`.
- Ensure blocked/allowed button states remain accurate for mixed result sets.
- Update contract tests in:
  - `frontend-web/tests/chat-shell.contract.test.tsx`

## Rollout Strategy

1. Stage

- Deploy policy + registry updates to staging first.
- Run:
  - `make quality`
  - `npm run typecheck --prefix frontend-web`
  - `npm run test --prefix frontend-web`
- Execute controlled staging export checks with trace IDs.

2. Observe

- Confirm `/ops/metrics` export counters:
  - expected rise in `source_export_allowed` for CanLII source IDs
  - no increase in `export_url_not_allowed_for_source` due to host mismatch regressions
  - no increase in `source_export_non_pdf_payload`

3. Production

- Release behind explicit legal/compliance approval evidence.
- Keep `EXPORT_POLICY_GATE_ENABLED=true`.
- Keep hardened environment constraints unchanged.

## Rollback Plan

If regressions or legal concern appears:

1. Revert CanLII export policy flags to `false`.
2. Re-deploy mirrored policy files.
3. Re-run export-policy tests and staging smoke.
4. Confirm metrics return to expected blocked state for CanLII exports.

## Evidence Checklist

- Signed legal/compliance approval artifact.
- Diff of policy + registry changes.
- Test outputs (backend + frontend).
- Staging trace IDs for successful and blocked export scenarios.
- `/ops/metrics` snapshot before and after rollout.
