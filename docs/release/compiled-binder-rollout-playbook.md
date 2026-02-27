# Compiled Binder Rollout Playbook

Date: 2026-02-27
Owner: IMMCAD platform maintainers

## Purpose

Define production controls for enabling compiled binder output (`compiled_pdf`) with safe canary rollout and fast rollback.

## Scope

- Document compilation package route: `POST /api/documents/matters/{matter_id}/package`
- Compiled binder download route: `GET /api/documents/matters/{matter_id}/package/download`
- Feature flag: `IMMCAD_ENABLE_COMPILED_PDF`

## Guardrails

- Default state: `IMMCAD_ENABLE_COMPILED_PDF=0` in all environments.
- Enable only in canary/staging first with explicit change ticket and rollback owner.
- Keep source-sync gate mandatory before deployment:
  - `PYTHONPATH=src uv run python scripts/validate_backend_runtime_source_sync.py`
  - `PYTHONPATH=src uv run python scripts/validate_cloudflare_env_configuration.py`
- Block promotion if any of the following occur:
  - compilation-policy regressions (`document_package_not_ready` false positives)
  - `document_compiled_artifact_unavailable` spikes after enabling flag
  - non-zero compiled payload integrity mismatches in test matrix

## Canary Phases

1. Phase 0: Staging only
- Enable `IMMCAD_ENABLE_COMPILED_PDF=1` in staging.
- Run `make test-document-compilation` and smoke upload/download checks.
- Confirm compiled bookmarks and page stamps are present.

2. Phase 1: Low-volume production canary
- Enable flag for a constrained traffic window.
- Observe metrics for at least one business day.

3. Phase 2: Gradual expansion
- Expand rollout only if Phase 1 meets success thresholds.
- Keep rollback command prepared and verified.

## Canary Success Metrics

Use `/ops/metrics` snapshot values from `document_compilation`:

- `compiled_rate >= 0.95` for ready matters in canary window.
- `blocked_rate` stable relative to baseline (no unexplained increase).
- `policy_reasons.document_compiled_artifact_unavailable` does not trend upward.

Supplementary checks:

- No increase in route-level 5xx for document package/download endpoints.
- No source-sync drift between `src/immcad_api` and `backend-vercel/src/immcad_api`.

## Rollback Criteria

Rollback immediately if any condition is met:

- sustained increase in `document_compiled_artifact_unavailable` policy blocks
- repeated binder download failures for ready matters
- compiled binder integrity issues reported by smoke tests or support
- unexpected spike in document compilation errors/5xx

## Rollback Procedure

1. Set `IMMCAD_ENABLE_COMPILED_PDF=0` and redeploy.
2. Re-run quick verification:
- `make test-document-compilation`
- one intake -> readiness -> package -> download smoke flow
3. Confirm runtime is back to `metadata_plan_only` behavior.
4. Capture incident note with:
- start/end time
- error signatures/policy reasons
- affected forums/routes
- follow-up remediation owner

## Pre-Promotion Checklist

- [ ] `make test-document-compilation` passes in target environment.
- [ ] `docs/release/document-intake-security-compliance-checklist.md` operational readiness items reviewed.
- [ ] Source sync validation passes.
- [ ] Canary metrics and rollback owner assigned.
- [ ] Rollback command validated in staging.
