# 08. Architecture Debt and Improvement Plan

## Table of Contents

- [Current Debt](#current-debt)
- [Risk Assessment](#risk-assessment)
- [Improvement Backlog (Prioritized)](#improvement-backlog-(prioritized))
- [Success Criteria](#success-criteria)

## Current Debt

1. UI and orchestration are tightly coupled in `app.py`.
2. No formal API boundary for frontend/backend separation.
3. Prompt domain is still India-focused while product goal is Canada-focused.
4. No provider abstraction or fallback policy in code.
5. No formal citation validator and policy gate enforcement.
6. No architecture CI validation or ADR process in place.

## Risk Assessment

- High: legal/domain mismatch can produce incorrect jurisdictional answers.
- High: single provider dependency can degrade availability.
- Medium: missing observability slows incident response.
- Medium: loose source governance increases stale-content risk.

## Improvement Backlog (Prioritized)

1. Introduce backend API boundary and move orchestration out of Streamlit.
2. [HIGH] Migrate prompt templates and domain knowledge from India to Canada jurisdiction (addresses debt item 3 / domain mismatch). Acceptance criteria: update templates, migrate jurisdictional knowledge artifacts, run jurisdictional test suite, obtain legal review sign-off.
3. Implement provider adapter with Gemini fallback.
4. Introduce citation-required policy gate.
5. Implement observability baseline (structured logging, metrics, distributed tracing) plus dashboards/alerting and phased coverage rollout for API, provider routing, and policy paths (addresses Risk Assessment: missing observability).
6. Build ingestion metadata schema and freshness checks.
7. Deploy architecture documentation validation in CI.
8. Add benchmark-based evaluation harness.

## Success Criteria

- Every legal factual response includes citations or explicit refusal.
- Provider outage does not fully break service.
- Architecture docs and ADRs are updated with each major design change.
