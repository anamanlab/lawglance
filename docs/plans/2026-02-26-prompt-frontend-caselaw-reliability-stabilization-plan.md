# IMMCAD Prompt + Frontend + Case Law Reliability Stabilization Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Improve answer correctness, frontend production readiness, latency transparency, and case-law research reliability without weakening policy/grounding guardrails.

**Architecture:** Keep the existing policy-first architecture (FastAPI + provider router + guardrails) but tighten the runtime contract between prompting, grounding, and UI state management. The plan introduces explicit request-phase state separation in the frontend, honest/persistent chat context handling, stronger retrieval-to-citation contracts, and more resilient case-law fallback behavior.

**Tech Stack:** Next.js 14 (frontend-web), TypeScript/React, FastAPI/Python, pytest, vitest, existing IMMCAD provider/router + policy modules.

---

## Scope and Success Criteria

- Chat UI no longer feels "stuck" during slow case search/export requests.
- Users can see when a request is slow and get actionable retry/cancel guidance.
- Prompting/runtime no longer claims chat history unless history is actually injected.
- Answer citations reflect actual grounding inputs and do not create false confidence.
- Case-law research path degrades gracefully across official/CanLII failures and broad user summaries.
- Regression tests cover new behavior (frontend async-state UX, backend prompt/runtime contract, case-law fallback/validation).

## Non-Goals (for this plan)

- Full retrieval engine redesign beyond the adapter contract and integration path.
- New ranking model for case-law relevance (we will stabilize current heuristics first).
- Visual rebrand from scratch (this is structure/clarity/operability work first).

## Baseline Verification (Before Code Changes)

### Task 1: Capture Current Failures and Latency Baseline

**Files:**
- Review: `frontend-web/components/chat/use-chat-logic.ts`
- Review: `frontend-web/components/chat/message-list.tsx`
- Review: `src/immcad_api/services/chat_service.py`
- Review: `src/immcad_api/services/case_search_service.py`
- Test: `tests/test_chat_service.py`
- Test: `tests/test_lawyer_case_research_service.py`

**Step 1: Reproduce current frontend degraded behavior**

Run:
```bash
npm run dev --prefix frontend-web -- --port 3001
```

Expected:
- Incident banner dominates on backend outage
- Composer disabled during any submit phase
- No elapsed timer / no slow-request hint

**Step 2: Capture backend response characteristics**

Run (with backend if available):
```bash
curl -sS -X POST http://127.0.0.1:8000/api/chat \
  -H 'Content-Type: application/json' \
  -d '{"session_id":"session-123456","message":"Summarize IRPA s.11","locale":"en-CA","mode":"standard"}'
```

Expected:
- Confirm whether response is scaffold/fallback/empty-grounding constrained

**Step 3: Record latency and fallback observations**

Output to note in PR/issue:
- chat response time
- case-law research response time
- whether `fallback_used` is returned but hidden in UI

**Step 4: Commit**

```bash
# No commit in this task (observation-only)
```

## Prompt + Answer Correctness

### Task 2: Fix Prompt/Runtime Contract (History Claim vs Stateless Runtime)

**Files:**
- Modify: `src/immcad_api/policy/prompts.py`
- Modify: `src/immcad_api/providers/prompt_builder.py`
- Modify: `src/immcad_api/services/chat_service.py`
- Modify: `src/immcad_api/schemas.py`
- Test: `tests/test_prompt_jurisdiction.py`
- Test: `tests/test_openai_provider.py`
- Test: `tests/test_gemini_provider.py`
- Add: `tests/test_prompt_runtime_contract.py`

**Step 1: Write failing tests for prompt/runtime honesty**

Add tests asserting either:
- system prompt does **not** claim full history when no history is passed, or
- runtime prompt includes history when the claim is retained.

**Step 2: Choose one contract and implement minimally**

Recommended phase-1 choice:
- Remove the "full chat history" claim from `SYSTEM_PROMPT`
- Keep runtime stateless until session memory is implemented

**Step 3: Add follow-up task marker for session memory**

Document in code comment/TODO (small, explicit) where `session_id`-backed memory will be injected later.

**Step 4: Run focused tests**

Run:
```bash
PYTHONPATH=.:src uv run pytest -q \
  tests/test_prompt_jurisdiction.py \
  tests/test_openai_provider.py \
  tests/test_gemini_provider.py \
  tests/test_prompt_runtime_contract.py
```

Expected: PASS

**Step 5: Commit**

```bash
git add src/immcad_api/policy/prompts.py src/immcad_api/providers/prompt_builder.py src/immcad_api/services/chat_service.py src/immcad_api/schemas.py tests/test_prompt_jurisdiction.py tests/test_openai_provider.py tests/test_gemini_provider.py tests/test_prompt_runtime_contract.py
git commit -m "fix(prompt): align system prompt with stateless runtime contract"
```

### Task 3: Correct Citation Semantics (Avoid False Confidence)

**Files:**
- Modify: `src/immcad_api/providers/openai_provider.py`
- Modify: `src/immcad_api/providers/gemini_provider.py`
- Modify: `src/immcad_api/services/chat_service.py`
- Modify: `src/immcad_api/policy/compliance.py`
- Test: `tests/test_chat_service.py`
- Add: `tests/test_policy_citation_enforcement.py`

**Step 1: Write failing tests for provider citation passthrough**

Add tests proving the current behavior is unsafe:
- provider returns input citations unchanged even if answer text cites different sources
- UI can display trusted citations that the model did not actually reference

**Step 2: Introduce explicit citation mode**

Minimal safe phase-1 implementation:
- Mark provider-returned citations as `[]` unless the provider explicitly emits structured citations
- Let `ChatService` downgrade to safe constrained response unless grounded citations are intentionally attached by policy-compliant logic

Alternative (phase-1.5 if time):
- extract citation markers from answer and match against grounding set

**Step 3: Tighten compliance tests**

Add dedicated tests for:
- exact-match verification
- trusted-domain rejection
- mismatch downgrades
- duplicate citation normalization

**Step 4: Run focused tests**

Run:
```bash
PYTHONPATH=.:src uv run pytest -q \
  tests/test_chat_service.py \
  tests/test_policy_citation_enforcement.py \
  tests/test_openai_provider.py \
  tests/test_gemini_provider.py
```

Expected: PASS

**Step 5: Commit**

```bash
git add src/immcad_api/providers/openai_provider.py src/immcad_api/providers/gemini_provider.py src/immcad_api/services/chat_service.py src/immcad_api/policy/compliance.py tests/test_chat_service.py tests/test_policy_citation_enforcement.py
git commit -m "fix(citations): remove unsafe provider citation passthrough"
```

### Task 4: Replace/Extend Static Grounding With Real Retrieval Adapter Contract

**Files:**
- Modify: `src/immcad_api/services/grounding.py`
- Modify: `src/immcad_api/main.py`
- Modify: `src/immcad_api/services/chat_service.py`
- Add: `src/immcad_api/services/retrieval_grounding_adapter.py` (if needed)
- Test: `tests/test_grounding.py`
- Add: `tests/test_retrieval_grounding_adapter.py`

**Step 1: Write adapter contract tests**

Cover:
- returns query-relevant citations
- returns no citations on miss
- never fabricates URLs

**Step 2: Implement pluggable retrieval-backed adapter**

Phase-1 safe fallback behavior:
- preserve keyword adapter as fallback
- prefer retrieval hits when available

**Step 3: Wire into `create_app()`**

Keep hardened env behavior deterministic and configurable.

**Step 4: Run focused tests**

Run:
```bash
PYTHONPATH=.:src uv run pytest -q \
  tests/test_grounding.py \
  tests/test_retrieval_grounding_adapter.py \
  tests/test_chat_service.py
```

Expected: PASS

**Step 5: Commit**

```bash
git add src/immcad_api/services/grounding.py src/immcad_api/main.py src/immcad_api/services/chat_service.py src/immcad_api/services/retrieval_grounding_adapter.py tests/test_grounding.py tests/test_retrieval_grounding_adapter.py
git commit -m "feat(grounding): prefer retrieval-backed grounding adapter"
```

## Frontend Structure + Slow Response UX

### Task 5: Split Frontend Async State by Workflow (Chat vs Cases vs Export)

**Files:**
- Modify: `frontend-web/components/chat/use-chat-logic.ts`
- Modify: `frontend-web/components/chat/types.ts`
- Modify: `frontend-web/components/chat/message-composer.tsx`
- Modify: `frontend-web/components/chat/related-case-panel.tsx`
- Test: `frontend-web/tests/chat-shell.contract.test.tsx`
- Add: `frontend-web/tests/use-chat-logic.state.contract.test.ts`

**Step 1: Write failing tests for independent pending states**

Scenarios:
- case search running does not disable chat composer typing
- export running only disables export button for selected case
- quick prompts remain usable unless chat submit is in flight

**Step 2: Replace monolithic `isSubmitting` with per-action flags**

Suggested state shape:
```ts
chatPending: boolean
caseSearchPending: boolean
exportPendingCaseId: string | null
```

**Step 3: Update button/input disable rules**

Examples:
- Composer disabled only when `chatPending`
- Case search input/button disabled only when `caseSearchPending`
- Export button disabled only for the active export case

**Step 4: Run frontend focused tests**

Run:
```bash
npm run test --prefix frontend-web -- --run \
  tests/chat-shell.contract.test.tsx \
  tests/use-chat-logic.state.contract.test.ts
```

Expected: PASS

**Step 5: Commit**

```bash
git add frontend-web/components/chat/use-chat-logic.ts frontend-web/components/chat/types.ts frontend-web/components/chat/message-composer.tsx frontend-web/components/chat/related-case-panel.tsx frontend-web/tests/chat-shell.contract.test.tsx frontend-web/tests/use-chat-logic.state.contract.test.ts
git commit -m "fix(frontend): split pending state by workflow"
```

### Task 6: Add Slow-Response Detection, Elapsed Time, and Retry/Cancel UX

**Files:**
- Modify: `frontend-web/lib/api-client.ts`
- Modify: `frontend-web/components/chat/use-chat-logic.ts`
- Modify: `frontend-web/components/chat/message-list.tsx`
- Modify: `frontend-web/components/chat/status-banner.tsx`
- Modify: `frontend-web/components/chat/types.ts`
- Test: `frontend-web/tests/api-client.contract.test.ts`
- Add: `frontend-web/tests/slow-response-ui.contract.test.tsx`

**Step 1: Write failing tests for latency metadata**

Add API client contract tests to assert response objects expose duration (e.g., `durationMs`) on success and failure.

**Step 2: Add request timing to API client**

Measure around fetch calls using `performance.now()` (browser-safe fallback if unavailable).

**Step 3: Add UI slow-response thresholds**

Suggested thresholds:
- >5s: show “Taking longer than usual…”
- >10s: show trace ID + retry guidance
- >20s: show hard “service degraded” banner copy

**Step 4: Add cancel/retry affordance**

If implementing cancellation now, use `AbortController`; otherwise add explicit retry and “keep waiting” options.

**Step 5: Run frontend focused tests**

Run:
```bash
npm run test --prefix frontend-web -- --run \
  tests/api-client.contract.test.ts \
  tests/slow-response-ui.contract.test.tsx
```

Expected: PASS

**Step 6: Commit**

```bash
git add frontend-web/lib/api-client.ts frontend-web/components/chat/use-chat-logic.ts frontend-web/components/chat/message-list.tsx frontend-web/components/chat/status-banner.tsx frontend-web/components/chat/types.ts frontend-web/tests/api-client.contract.test.ts frontend-web/tests/slow-response-ui.contract.test.tsx
git commit -m "feat(frontend): add slow-response detection and latency UX"
```

### Task 7: Rebalance Frontend Information Hierarchy (Error Banner, Disclaimers, Diagnostics)

**Files:**
- Modify: `frontend-web/app/page.tsx`
- Modify: `frontend-web/components/chat/chat-header.tsx`
- Modify: `frontend-web/components/chat/chat-shell-container.tsx`
- Modify: `frontend-web/components/chat/status-banner.tsx`
- Modify: `frontend-web/components/chat/support-context-panel.tsx`
- Test: `frontend-web/tests/chat-shell.contract.test.tsx`

**Step 1: Write failing UI structure checks**

Cover:
- disclaimer shown once at primary location
- incident banner shown for relevant endpoint failures (not chat only)
- diagnostics panel mount is controlled but actually renderable

**Step 2: Reduce duplicate safety labels**

Keep:
- one concise disclaimer near the header
- one “Informational only” badge max

**Step 3: Promote incident/degraded state to shell-level**

Drive banner from a generic endpoint status object (chat + case research + export), not only `chatError`.

**Step 4: Mount `SupportContextPanel` when diagnostics are enabled**

Use `showOperationalPanels` and `supportContext`.

**Step 5: Run frontend tests and manual smoke**

Run:
```bash
npm run test --prefix frontend-web -- --run tests/chat-shell.contract.test.tsx
npm run dev --prefix frontend-web -- --port 3001
```

Expected:
- clearer hierarchy
- non-chat incidents visible

**Step 6: Commit**

```bash
git add frontend-web/app/page.tsx frontend-web/components/chat/chat-header.tsx frontend-web/components/chat/chat-shell-container.tsx frontend-web/components/chat/status-banner.tsx frontend-web/components/chat/support-context-panel.tsx frontend-web/tests/chat-shell.contract.test.tsx
git commit -m "refactor(frontend): simplify hierarchy and unify incident states"
```

## Backend Responsiveness and Reliability

### Task 8: Prevent Chat Route Event-Loop Blocking

**Files:**
- Modify: `src/immcad_api/api/routes/chat.py`
- Review: `src/immcad_api/api/routes/lawyer_research.py`
- Test: `tests/test_api_scaffold.py`
- Add: `tests/test_chat_route_threadpool.py`

**Step 1: Write failing test for threadpool dispatch (or route behavior under stubbed delay)**

Goal:
- prove `/api/chat` executes blocking `chat_service.handle_chat` via `run_in_threadpool`

**Step 2: Mirror `lawyer_research` route pattern**

Use:
- `starlette.concurrency.run_in_threadpool`

**Step 3: Run focused tests**

Run:
```bash
PYTHONPATH=.:src uv run pytest -q tests/test_api_scaffold.py tests/test_chat_route_threadpool.py
```

Expected: PASS

**Step 4: Commit**

```bash
git add src/immcad_api/api/routes/chat.py tests/test_api_scaffold.py tests/test_chat_route_threadpool.py
git commit -m "perf(api): run chat service in threadpool"
```

### Task 9: Harden Case Search Fallback and Query Validation

**Files:**
- Modify: `src/immcad_api/services/case_search_service.py`
- Modify: `src/immcad_api/api/routes/case_query_validation.py`
- Modify: `src/immcad_api/services/lawyer_research_planner.py`
- Test: `tests/test_case_search_service.py`
- Test: `tests/test_lawyer_research_planner.py`
- Test: `tests/test_lawyer_case_research_service.py`
- Test: `tests/test_case_query_validation.py`

**Step 1: Write failing tests for official-client non-SourceUnavailable errors**

Case:
- official client raises `ApiError`
- CanLII client returns healthy results
- service should still fallback and return CanLII response

**Step 2: Implement resilient fallback behavior**

Catch and classify official errors without immediately aborting fallback.

**Step 3: Relax broad-query validation (carefully)**

Keep abuse protection, but allow longer natural-language matter summaries with clear legal/case context.

**Step 4: Add planner coverage for real summaries**

Assert generated queries remain usable and non-empty across representative matter summaries.

**Step 5: Run focused tests**

Run:
```bash
PYTHONPATH=.:src uv run pytest -q \
  tests/test_case_search_service.py \
  tests/test_lawyer_research_planner.py \
  tests/test_lawyer_case_research_service.py \
  tests/test_case_query_validation.py
```

Expected: PASS

**Step 6: Commit**

```bash
git add src/immcad_api/services/case_search_service.py src/immcad_api/api/routes/case_query_validation.py src/immcad_api/services/lawyer_research_planner.py tests/test_case_search_service.py tests/test_lawyer_research_planner.py tests/test_lawyer_case_research_service.py tests/test_case_query_validation.py
git commit -m "fix(caselaw): improve fallback resilience and query validation"
```

### Task 10: Revisit Lawyer Research Export Metadata Handling (Don’t Make Results Look Broken)

**Files:**
- Modify: `src/immcad_api/services/lawyer_case_research_service.py`
- Modify: `frontend-web/components/chat/related-case-panel.tsx`
- Test: `tests/test_lawyer_case_research_service.py`
- Test: `frontend-web/tests/chat-shell.contract.test.tsx`

**Step 1: Write failing tests for “unverified but viewable” case results**

Desired behavior:
- case can be shown as a valid related result even if export metadata is incomplete
- export action can remain disabled with a clear reason

**Step 2: Adjust service semantics**

Separate:
- `result visibility/relevance`
- `export eligibility`

Avoid converting missing registry metadata into an experience that looks like search failure.

**Step 3: Improve panel copy**

Make reasons user-facing and actionable:
- “View case online”
- “Export unavailable in this environment/source”

**Step 4: Run focused tests**

Run:
```bash
PYTHONPATH=.:src uv run pytest -q tests/test_lawyer_case_research_service.py
npm run test --prefix frontend-web -- --run tests/chat-shell.contract.test.tsx
```

Expected: PASS

**Step 5: Commit**

```bash
git add src/immcad_api/services/lawyer_case_research_service.py frontend-web/components/chat/related-case-panel.tsx tests/test_lawyer_case_research_service.py frontend-web/tests/chat-shell.contract.test.tsx
git commit -m "fix(caselaw): separate result relevance from export eligibility"
```

## Evaluation and Regression Safety

### Task 11: Expand Evals for Answer Quality and Case-Law Reliability

**Files:**
- Modify: `src/immcad_api/evaluation/jurisdiction_suite.py`
- Modify: `tests/test_jurisdiction_suite.py`
- Add: `tests/test_prompt_answer_quality_contract.py`
- Add: `tests/test_case_law_research_integration.py` (fixture-backed)

**Step 1: Add more jurisdiction suite cases**

Include:
- follow-up phrasing
- case-law prompts
- refusal edge cases
- weak-grounding prompts

**Step 2: Add fixture-backed case-law integration test**

Use deterministic fixtures (not live network) to validate:
- case search -> lawyer research -> UI-ready support fields

**Step 3: Run focused eval tests**

Run:
```bash
PYTHONPATH=.:src uv run pytest -q \
  tests/test_jurisdiction_suite.py \
  tests/test_prompt_answer_quality_contract.py \
  tests/test_case_law_research_integration.py
```

Expected: PASS

**Step 4: Commit**

```bash
git add src/immcad_api/evaluation/jurisdiction_suite.py tests/test_jurisdiction_suite.py tests/test_prompt_answer_quality_contract.py tests/test_case_law_research_integration.py
git commit -m "test(evals): expand answer quality and caselaw reliability coverage"
```

## Final Verification and Rollout

### Task 12: Full Verification, UX Review, and Release Notes

**Files:**
- Modify: `tasks/todo.md`
- Modify: `docs/release/known-issues.md` (if any residual gaps remain)
- Optional: `tasks/lessons.md` (if new user-facing pitfalls are discovered)

**Step 1: Run backend quality gates**

Run:
```bash
make quality
```

Expected: PASS

**Step 2: Run frontend verification**

Run:
```bash
npm run test --prefix frontend-web
npm run typecheck --prefix frontend-web
```

Expected: PASS

**Step 3: Manual UX smoke (desktop + mobile)**

Check:
- backend offline incident state
- slow request state
- chat success with sources
- case-law search success/empty/error
- export-disabled reason clarity

**Step 4: Update tracking docs**

Record:
- what improved
- residual risks
- follow-up work (session memory, richer retrieval)

**Step 5: Commit**

```bash
git add tasks/todo.md docs/release/known-issues.md tasks/lessons.md
git commit -m "docs: record stabilization verification and follow-ups"
```

## Implementation Order (Recommended)

1. Task 2 (prompt/runtime contract)
2. Task 3 (citation semantics correctness)
3. Task 8 (chat route threadpool responsiveness)
4. Task 5 (frontend per-workflow async state)
5. Task 6 (slow-response latency UX)
6. Task 9 (case-search fallback + validation)
7. Task 10 (lawyer research result/export semantics)
8. Task 7 (frontend hierarchy cleanup)
9. Task 4 (retrieval-backed grounding adapter)
10. Task 11-12 (eval expansion + full verification)

## Risks and Rollback Notes

- Tightening citation semantics may initially increase safe-fallback responses until retrieval quality improves.
- Query-validation loosening may increase noisy case searches; track rate-limit metrics after rollout.
- Frontend async-state split touches many interactions; keep regression coverage on composer/search/export actions before merging.

