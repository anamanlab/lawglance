# Canada Readiness Execution Plan

## Table of Contents

- [Phase 1: Prompt and Policy Migration (Now)](#phase-1:-prompt-and-policy-migration-(now))
- [Phase 2: Source Ingestion Migration](#phase-2:-source-ingestion-migration)
- [Phase 3: Evaluation and Legal Sign-Off](#phase-3:-evaluation-and-legal-sign-off)
- [Current Week Deliverables](#current-week-deliverables)

This plan executes the India -> Canada migration in measurable phases.

## Phase 1: Prompt and Policy Migration (Now)

- Replace India-specific prompt domain assumptions with Canada immigration/citizenship scope.
- Enforce citation-required behavior and refusal on ungrounded/legal-advice requests.
- Add regression tests for refusal paths and citation-required responses.

## Phase 2: Source Ingestion Migration

- Build canonical source inventory for:
  - IRPA / IRPR
  - Citizenship Act + regulations
  - IRCC operational instructions / ministerial instructions
  - CanLII immigration case metadata
- Attach metadata for jurisdiction, source type, effective/published dates, and checksum.
- Define refresh cadence: policy daily, statutes weekly, case metadata scheduled incremental sync.

## Phase 3: Evaluation and Legal Sign-Off

- Build jurisdictional eval set (at least 50 Canada immigration questions).
- Pass criteria:
  - Citation coverage >= 95% for factual legal responses.
  - Hallucination/refusal safety checks pass.
  - Domain mismatch checks pass (no India legal references in production responses).
- Obtain legal reviewer sign-off before external rollout.

## Current Week Deliverables

1. Prompt migration completed.
2. Add ingestion source registry skeleton.
3. Add jurisdictional regression checks to CI.
4. Schedule legal review checkpoint.
