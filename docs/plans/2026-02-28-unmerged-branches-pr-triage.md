# Unmerged Archive Branches PR Triage Plan (2026-02-28)

> Scope: branch governance after merging PR #37 to `main` on 2026-02-28.

## Goal

Decide a safe, lossless disposition for each remaining `origin/archive/*` branch and recover only deltas that are still valid against current `main`.

## Steps

- [x] Sync remote refs and enumerate unmerged branches against `origin/main`.
- [x] Confirm PR linkage for each unmerged archive branch.
- [x] Perform branch-by-branch commit and file delta review.
- [x] Perform independent triage (parallel agent audits) for each archive branch.
- [x] Classify each branch: recover now / optional follow-up / archive-only.
- [x] Generate immutable patch backups for each branch delta.
- [x] Implement the single approved recovery delta (`insufficient_context` fallback reason) in current architecture.
- [ ] Run targeted tests and lint in a fully provisioned environment.

## Branch Disposition Summary

- `origin/archive/archive-dirty-root-reconcile-v4-20260224-170035-20260224-195431`
  - Decision: `archive-only`.
  - Why: snapshot commit is stale/regressive and conflicts with current conformance workflow/doc contracts.
- `origin/archive/archive-ralph-canada-hardening-next-loop-20260224-20260224-195431`
  - Decision: `archive-only` with one surgical recovery.
  - Recovery applied: explicit `fallback_used.reason = "insufficient_context"` for constrained no-grounding responses.
- `origin/archive/archive-reconcile-production-readiness-20260224-20260224-195431`
  - Decision: `archive-only`.
  - Why: heavily stale vs main, high conflict density, high regression risk if replayed.
- `origin/archive/wip-local-dirty-carryforward-20260224-20260224-195431`
  - Decision: `archive-only`.
  - Why: mixed-scope WIP snapshot; no mandatory unsuperseded runtime fix identified.

## Backup Artifacts

- Patch series: `backups/branch-safety/20260228-branch-archive-audit/`
- Manifest: `backups/branch-safety/20260228-branch-archive-audit/manifest.tsv`

## Verification Status

- Local environment in this session lacks `uv` and `pytest`, so execution verification is pending CI/full dev environment.
