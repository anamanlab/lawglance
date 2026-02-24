# PRD: IMMCAD Phase 2 - Frontend Launch and Authoritative Runtime

## 1. Overview

Phase 1 hardening is complete. Phase 2 ships a production chat frontend and removes remaining scaffold behavior that can produce non-authoritative legal outputs.

## 2. Goals

- Launch a minimal Next.js + Tailwind chat UI wired to IMMCAD API.
- Enforce authoritative-only behavior for case-law and citations in production/CI.
- Preserve Canada-only legal scope with explicit legal disclaimers and traceable errors.
- Add release evidence for frontend + runtime contract integrity.

## 3. User Stories

1. Correct authoritative source links for tribunal/compliance references.
2. Disable synthetic CanLII fallback in production and return structured source-unavailable response.
3. Enforce `ALLOW_SCAFFOLD_SYNTHETIC_CITATIONS` at runtime with production startup guard.
4. Replace default synthetic citation behavior with grounded citation adapter contract.
5. Expand policy refusal coverage with additional blocked/allowed examples.
6. Scaffold Next.js + Tailwind app with minimalist chat layout.
7. Implement frontend API client for `/api/chat` and `/api/search/cases` with `x-trace-id` handling.
8. Render citation chips, disclaimer banner, refusal/error states, and loading states.
9. Add frontend tests (unit + contract) for chat success/error/refusal flows.
10. Add CI frontend quality gates and artifact upload.
11. Update docs/runbooks to mark Streamlit as legacy and Next.js as production UI.
12. Add staging smoke script covering frontend-to-backend critical path.

## 4. Functional Requirements

- FR-1: Production/CI must not emit synthetic case results or synthetic citations.
- FR-2: Non-refusal legal responses require grounded citations.
- FR-3: Frontend must display disclaimer and citations for legal responses.
- FR-4: Frontend must surface trace ID for support/incident workflows.
- FR-5: Release gates must validate frontend build/test and runtime safety toggles.

## 5. Non-Goals

- Full multilingual UX (French) in this phase.
- New legal domains beyond Canadian immigration/citizenship.
- Full APM platform rollout.

## 6. Success Metrics

- Frontend chat success flow works in staging with trace IDs visible.
- 0 synthetic outputs in production/CI modes.
- Citation coverage for grounded responses >= 98%.
- CI passes backend + frontend quality suites on every PR.
