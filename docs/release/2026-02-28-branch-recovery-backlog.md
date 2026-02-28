# Branch Recovery Backlog (Post-Archive Triage, 2026-02-28)

## Purpose

Track optional, low-risk follow-ups discovered during archive branch triage. These are not blockers for current `main` correctness.

## Candidates

1. Additive release-runtime flag validator script parity
- Source: `origin/archive/archive-ralph-canada-hardening-next-loop-20260224-20260224-195431`
- Rationale: intent overlaps with current guards; may still add explicit preflight diagnostics.
- Risk: low-medium if implemented additively (do not replace current release gates).
- Status: backlog.

2. Docs-only reconciliation pass for architecture/research narrative deltas
- Source: `origin/archive/archive-reconcile-production-readiness-20260224-20260224-195431`
- Rationale: possible useful wording/context in docs without runtime impact.
- Risk: low if restricted to docs-only.
- Status: backlog.

3. Targeted review of `tests/test_doc_maintenance.py` WIP delta
- Source: `origin/archive/wip-local-dirty-carryforward-20260224-20260224-195431`
- Rationale: one of few low-risk files that may contain test hardening value.
- Risk: low.
- Status: backlog.

## Explicitly Not Scheduled

- Wholesale merge/cherry-pick replay of any archive branch.
- Runtime/workflow config replay from stale archive branches.

These remain archive-only due conflict density and regression risk.
