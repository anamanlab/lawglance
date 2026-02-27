# Task Plan Tracking Log

## Task Plan - 2026-02-27 - Prompt Capability Audit + Friendly Behavior + Eval Suite

### Current Focus
- Systematically audit prompt/runtime capability coverage (including tool orchestration), fix missed issues from prior prompt pass, and add a production-safe prompt behavior eval suite with friendly greeting support.

### Plan
- [ ] Audit current prompt/runtime capability coverage and document concrete gaps from the first prompt pass.
- [ ] Add failing tests for friendly greeting behavior and prompt capability/tool-awareness content.
- [ ] Implement chat + prompt changes to support friendly non-legal greetings without weakening grounding policy.
- [ ] Add a prompt behavior eval suite (data + evaluator + tests) to track greeting/policy/grounding/injection expectations.
- [ ] Run targeted lint/tests and record verification evidence.
- [ ] Update lessons with this user-correction pattern.

### Review
- Pending implementation.

## Task Plan - 2026-02-27 - Gemini Prompt Review + Hardening

### Current Focus
- Review current Gemini prompt stack and improve instruction quality, grounding robustness, and injection resistance without breaking existing behavior contracts.

### Plan
- [x] Audit active prompt text and prompt-builder formatting for ambiguity and failure risks.
- [x] Rewrite prompt instructions with explicit output contract, citation discipline, and prompt-injection defenses.
- [x] Update/extend prompt-focused tests to lock in revised behavior.
- [x] Run targeted lint/tests and record verification evidence.

### Review
- Updated canonical runtime prompt text in `src/immcad_api/policy/prompts.py`:
  - Added explicit instruction-priority hierarchy and context-boundary language.
  - Added prompt-injection defense guidance (treat user/context text as untrusted; ignore conflicting embedded instructions).
  - Strengthened grounding rules (no invented citations/statutes/case details; explicit handling when context is missing).
  - Switched QA prompt to deterministic response sections (`Summary`, `Grounded Rules`, `Next Steps`, `Confidence and Escalation`).
- Synced legacy compatibility prompt config in `config/prompts.yaml` with the same hardening updates.
- Extended prompt regression tests in `tests/test_prompt_jurisdiction.py` to lock in:
  - Instruction-priority + untrusted-context rules in system prompt.
  - Deterministic QA sections + injection-guard rule in QA prompt.
- Verification evidence:
  - `PYTHONPATH=src uv run pytest -q tests/test_prompt_jurisdiction.py tests/test_prompt_compatibility.py tests/test_gemini_provider.py tests/test_openai_provider.py` -> `10 passed`
  - `PYTHONPATH=src uv run ruff check src/immcad_api/policy/prompts.py tests/test_prompt_jurisdiction.py` -> `All checks passed!`
  - `PYTHONPATH=src uv run python - <<'PY' ... yaml.safe_load(config/prompts.yaml) ... PY` -> `ok ['human prompt', 'qaprompt', 'system prompt']`

## Task Plan - 2026-02-27 - Court-Source Storage/Persistence Runtime Audit

### Current Focus
- Audit court-source data lifecycle across registry, policy, checkpoints, caches, and document stores, then trace AI chat/research runtime usage and MVP risks.

### Plan
- [ ] Inventory court-source storage surfaces and infer retention/TTL behavior.
- [ ] Trace how chat and lawyer-research services consume source data at runtime.
- [ ] Enumerate current observability surfaces for source freshness, ingestion health, and runtime behavior.
- [ ] Summarize top MVP risks with exact file+line evidence and remediation direction.

### Review
- Pending audit synthesis.

## Task Plan - 2026-02-27 - Chat Thinking Transparency (Frontend)

### Current Focus
- Execute the approved chat-thinking transparency plan in `docs/plans/2026-02-27-chat-thinking-transparency-implementation-plan.md` using subagent-driven development with spec + quality review gates.

### Plan
- [x] Task 1: Add feature flag contract/plumbing for `NEXT_PUBLIC_IMMCAD_ENABLE_AGENT_THINKING_TIMELINE`.
- [x] Task 2: Add activity timeline domain types/helpers.
- [x] Task 3: Integrate timeline state in `use-chat-logic`.
- [x] Task 4: Build inline activity strip UI.
- [x] Task 5: Build expandable thinking drawer UI.
- [x] Task 6: Gate timeline rendering with runtime feature flag.
- [x] Task 7: Add timeline motion/reduced-motion/accessibility styling.
- [x] Task 8: Final docs + verification (`test`, `lint`, `typecheck`).

### Review
- Task 1 complete:
  - Implemented runtime flag plumbing + page wiring in `frontend-web/lib/runtime-config.ts` and `frontend-web/app/page.tsx`.
  - Tightened `ChatShellProps` contract (`enableAgentThinkingTimeline` required) and updated affected tests.
  - Added production invalid-input fallback test coverage for timeline flag.
  - Verified with targeted frontend test runs + typecheck.
- Task 2 complete:
  - Added `AgentActivityStage`, `AgentActivityStatus`, `AgentActivityEvent`, and `AgentActivityMeta` in chat types.
  - Added immutable activity helper module in `frontend-web/components/chat/agent-activity.ts`.
  - Added contract tests in `frontend-web/tests/agent-activity.contract.test.ts`.
- Task 3 complete:
  - Added per-turn activity lifecycle state in `use-chat-logic` and mapped submit/success/error/policy/fallback transitions.
  - Propagated activity turn ids into assistant messages and message-list payload diagnostics.
  - Verified with `frontend-web` contract/UI tests for pending + latest timeline payload behavior.
- Task 4 complete:
  - Added `frontend-web/components/chat/activity-strip.tsx` for compact stage/status chips.
  - Integrated strip rendering into assistant bubbles and pending processing state.
  - Added UI assertion coverage for inline activity visibility while pending.
- Task 5 complete:
  - Added `frontend-web/components/chat/thinking-drawer.tsx` with per-turn Show/Hide details toggle.
  - Wired drawer into assistant message rendering beneath inline activity chips.
  - Added UI test coverage for toggle behavior and timeline-details visibility.
- Task 6 complete:
  - Confirmed timeline affordances are shown only when `enableAgentThinkingTimeline` is enabled.
  - Added regression test covering disabled-flag behavior (`Show agent thinking` + inline activity hidden).
- Task 7 complete:
  - Added timeline animation class + running-state pulse with reduced-motion overrides in `app/globals.css`.
  - Added `aria-live`/`aria-label` semantics for activity chips and timeline list entries.
  - Added UI test assertion for status-labelled timeline entries.
- Task 8 complete:
  - Documented `NEXT_PUBLIC_IMMCAD_ENABLE_AGENT_THINKING_TIMELINE` in `.env.example` and `frontend-web/README.md`.
  - Verification evidence:
    - `cd frontend-web && npm run test` -> 119 passed.
    - `cd frontend-web && npm run test -- tests/runtime-config.test.ts tests/chat-shell.ui.test.tsx tests/chat-shell.contract.test.tsx tests/home-page.rollout.test.tsx tests/agent-activity.contract.test.ts` -> 47 passed.
    - `cd frontend-web && npm run lint` -> no warnings/errors.
    - `cd frontend-web && npm run typecheck` -> pass.

## Task Plan - 2026-02-27 - SCC/FC Official Search Integration Hardening

### Current Focus
- Improve SCC/FC immigration case retrieval quality and citation trust by using official search endpoints with safe fallback to existing feeds.

### Plan
- [x] Normalize Decisia mirror links (`norma.lexum.com`) to official court domains during parsing.
- [x] Add parser support for Decisia search-result HTML list pages.
- [x] Wire SCC/FC query-time retrieval to official `d/s/index.do` endpoints with feed fallback on errors.
- [x] Add regression tests for URL canonicalization, search-result parsing, query-search preference, and fallback behavior.
- [x] Re-run targeted lint/tests for parser and official client integration.

### Review
- Implemented host canonicalization + query-safe PDF URL derivation in `src/immcad_api/sources/canada_courts.py`.
- Added `parse_decisia_search_results_html(...)` and integrated it into runtime retrieval for SCC/FC query searches in `src/immcad_api/sources/official_case_law_client.py`.
- Runtime behavior now:
  - SCC/FC: attempt official query endpoint first.
  - Any SCC/FC query endpoint failure: fallback to existing registry feed path.
  - FCA: unchanged fallback/feed behavior.
- Regression coverage added in:
  - `tests/test_canada_courts.py`
  - `tests/test_official_case_law_client.py`
- Verification evidence:
  - `PYTHONPATH=src uv run ruff check src/immcad_api/sources/canada_courts.py src/immcad_api/sources/official_case_law_client.py tests/test_canada_courts.py tests/test_official_case_law_client.py` -> `All checks passed!`
  - `PYTHONPATH=src uv run pytest -q tests/test_canada_courts.py tests/test_official_case_law_client.py` -> `36 passed`
  - `PYTHONPATH=src uv run pytest -q tests/test_case_search_service.py` -> `5 passed`

## Task Plan - 2026-02-27 - Official Court Ingestion Persistence Audit

### Current Focus
- Audit official court ingestion persistence behavior for MVP readiness: storage layers, retention, crawl model, and operational risk.

### Plan
- [x] Trace official court runtime data path and classify persistence (memory/cache/db/filesystem).
- [x] Trace ingestion job persistence paths and retention semantics (checkpoint/cache lifecycle).
- [x] Determine whether official court data supports historical crawl/backfill or only on-demand retrieval.
- [x] Produce MVP readiness risks and recommendations with file-backed evidence.

### Review
- Runtime official-court retrieval (`OfficialCaseLawClient`) uses in-process memory cache only (fresh/stale TTL) and fetches source URLs directly on-demand; no DB/filesystem persistence for case records.
- Ingestion jobs persist only checkpoint metadata (etag/last-modified/checksum/last_success_at) to state JSON and emit per-run report artifacts; decision payloads are not persisted for official court sources.
- Historical crawl/backfill for official courts is not implemented; both ingestion and runtime operate on current feed snapshots. By contrast, federal-laws ingestion has dedicated JSONL materialization + per-act cache/checkpoints.
- Key MVP risks captured: no durable historical corpus for official courts, runtime/ingestion decoupling, checkpoint path inconsistency between API defaults and workflow cache paths, and strict validation behavior that can fail entire source runs on partial record issues.

## Task Plan - 2026-02-27 - SCC + FC Priority MVP Finalization

### Current Focus
- Finalize MVP around the two priority official court sources: `SCC_DECISIONS` and `FC_DECISIONS`.
- Treat `FCA_DECISIONS` as non-blocking for MVP launch readiness unless it regresses SCC/FC paths.

### Scope Lock (Decision)
- [ ] Lock MVP acceptance criteria to SCC + FC production reliability and user transparency.
- [ ] Keep FCA ingestion/search enabled but classify FCA issues as P1 only when they impact shared parser/runtime behavior.

### Plan
- [ ] Source reliability hardening (SCC/FC):
  - [x] Add SCC/FC-specific smoke script assertions in CI (`/api/search/cases` + `/api/research/lawyer-cases`), including immigration-focused queries.
  - [ ] Add regression tests for SCC/FC citation extraction/date handling edge cases from real feed shapes.
  - [ ] Add explicit SCC/FC freshness SLO status mapping (`fresh`/`stale`/`missing`) with thresholds documented in runbook.
- [ ] UX/source transparency completion:
  - [x] Add an explicit navigation entry from main chat shell to `/sources`.
  - [ ] Highlight SCC/FC as "priority courts" on `/sources` and in related-case status cards.
  - [x] Surface checkpoint freshness timestamp and stale warning copy in user-visible UI.
- [ ] AI-agent effectiveness improvements:
  - [ ] Add SCC/FC-focused query refinement hints (court + issue + citation anchors) in research panel.
  - [ ] Add failure-mode messaging that distinguishes `official unavailable` vs `no_match` for SCC/FC.
  - [ ] Verify chat research-preview behavior stays grounded when SCC/FC is available.
- [ ] Storage and observability:
  - [ ] Persist/validate ingestion checkpoint path in all runtimes (`INGESTION_CHECKPOINT_STATE_PATH`) and document defaults.
  - [x] Add ops log/metric slice for SCC/FC success rate and last-success age.
  - [ ] Add release checklist item that blocks deploy when SCC/FC freshness is `missing`/`stale`.
- [ ] Release gate and verification:
  - [ ] Run targeted backend tests for official client, ingestion scheduling, source transparency, and lawyer research status mapping.
  - [ ] Run frontend tests for `/sources` page, proxy mapping, and case sidebar source-status rendering.
  - [ ] Run lint/typecheck and capture exact command evidence in this section before marking done.

### Exit Criteria
- [ ] SCC + FC both report `fresh` in `/api/sources/transparency` on production-like runtime.
- [ ] SCC + FC case-law retrieval works in both manual research and chat-triggered preview flows.
- [ ] Users can clearly see available priority sources and freshness state from main product navigation.
- [ ] CI contains SCC/FC smoke coverage and fails on regression of source availability or grounding behavior.

### Review
- Pending implementation.

## Task Plan - 2026-02-27 - MVP Case-Law Hardening + Source Transparency

### Current Focus
- Execute the MVP audit remediation for official case-law reliability (FC/FCA/SCC), ingestion freshness, and user-visible source transparency.

### Plan
- [x] Patch runtime official case-law client for redirect-safe fetches and null-safe decision-date filtering.
- [x] Add regression tests for official runtime redirect handling and missing-decision-date filtering behavior.
- [x] Include FCA in hourly Cloudflare ingestion schedule and update schedule tests/contracts.
- [x] Add API source-coverage/status endpoint exposing courts/sources and checkpoint freshness metadata.
- [x] Add frontend source-coverage page with clear court coverage and freshness visibility for end users.
- [x] Run targeted backend + frontend tests/lint/typecheck and document verification evidence.

### Review
- Runtime reliability:
  - Official runtime fetch now follows redirects in `OfficialCaseLawClient`.
  - Decision-date filtering is null-safe when feed records are missing dates.
  - Regression tests added in `tests/test_official_case_law_client.py`.
- Ingestion freshness:
  - FCA is now included in hourly Cloudflare ingestion scheduling.
  - Schedule tests updated in `tests/test_cloudflare_ingestion_hourly_script.py`.
- Source transparency:
  - Added backend endpoint: `GET /api/sources/transparency`.
  - Wired endpoint via app router and added checkpoint-path override (`INGESTION_CHECKPOINT_STATE_PATH`).
  - Added frontend proxy route: `frontend-web/app/api/sources/transparency/route.ts`.
  - Added user-facing page: `frontend-web/app/sources/page.tsx`.
  - Added backend/frontend contract tests for new endpoint and page rendering.
- Verification evidence:
  - `PYTHONPATH=src uv run pytest -q tests/test_official_case_law_client.py tests/test_cloudflare_ingestion_hourly_script.py tests/test_ingestion_jobs_workflow.py tests/test_source_transparency_api.py` -> `27 passed`
  - `PYTHONPATH=src uv run ruff check src/immcad_api/sources/official_case_law_client.py src/immcad_api/api/routes/source_transparency.py src/immcad_api/main.py src/immcad_api/api/routes/__init__.py src/immcad_api/schemas.py scripts/run_cloudflare_ingestion_hourly.py tests/test_official_case_law_client.py tests/test_cloudflare_ingestion_hourly_script.py tests/test_source_transparency_api.py` -> `All checks passed!`
  - `cd frontend-web && npm run test -- --run tests/source-transparency-route.contract.test.ts tests/source-transparency-page.contract.test.tsx tests/backend-proxy.contract.test.ts` -> `25 passed`
  - `cd frontend-web && npx eslint app/api/sources/transparency/route.ts app/sources/page.tsx lib/backend-proxy.ts tests/source-transparency-route.contract.test.ts tests/source-transparency-page.contract.test.tsx tests/backend-proxy.contract.test.ts` -> pass
  - `cd frontend-web && npm run typecheck` -> pass
  - `PYTHONPATH=src uv run mypy src/immcad_api/sources/official_case_law_client.py src/immcad_api/api/routes/source_transparency.py src/immcad_api/main.py src/immcad_api/schemas.py .` -> fails due existing workspace module shadowing (`backend-cloudflare/python_modules/typing_extensions.py`), not introduced by these changes.

## Task Plan - 2026-02-27 - Cloud-Only Deployment Baseline

### Current Focus
- Replace VPS/temp-machine dependency with a Cloudflare-native deployment baseline so any repo-authorized teammate can deploy from code + CI only.

### Plan
- [x] Validate architecture choices against current Cloudflare official docs (limits, secrets, CI/CD, configuration).
- [x] Harden backend native deploy workflow to be repo-driven (`push` + `workflow_dispatch`) with secret-sync and required-secret checks.
- [x] Add deterministic hardened backend runtime vars to `backend-cloudflare/wrangler.toml`.
- [x] Switch frontend Cloudflare runtime upstream to backend native Worker URL and remove legacy fallback default.
- [x] Add validator guardrails/tests to enforce cloud-only production wrangler baseline.
- [x] Update developer/release docs with canonical cloud-only deployment path.
- [ ] Deploy backend native + frontend and run live production smoke checks.

### Review
- In progress.

## Task Plan - 2026-02-27 - Frontend Wiring Audit + Reliability Hardening

### Current Focus
- Verify that the frontend is wired end-to-end for case-law/document workflows and harden failure handling paths that can silently degrade UX.

### Plan
- [x] Audit frontend wiring across `use-chat-logic`, API client contracts, and related-case/document panels.
- [x] Add regression test for support-matrix retry after transient failure.
- [x] Fix support-matrix loader to avoid one-failure lockout and permit retry.
- [x] Harden API error-envelope parsing for root-level `trace_id` / `policy_reason` fallback.
- [x] Re-run targeted frontend contract tests, lint, and typecheck.

### Review
- Wiring status: confirmed connected (`ChatShell` -> `useChatLogic` -> `api-client` -> related-case/doc panels), including metadata rendering and document support matrix usage.
- Issues found + fixed:
  - `frontend-web/components/chat/use-chat-logic.ts`
    - Replaced sticky support-matrix loaded flag with in-flight request guard.
    - Result: transient `GET /api/documents/support-matrix` failures no longer permanently lock the session into fallback defaults.
  - `frontend-web/lib/api-client.ts`
    - Improved `parseErrorEnvelope(...)` to fall back to root-level `trace_id` and `policy_reason` when nested `error` object omits them.
    - Result: better trace/policy diagnostics for mixed backend/proxy envelope shapes.
- Test updates:
  - `frontend-web/tests/chat-shell.contract.test.tsx`
    - Added `retries support matrix fetch after a transient failure`.
  - `frontend-web/tests/api-client.contract.test.ts`
    - Added root envelope trace/policy fallback parser contract.

### Verification evidence
- `cd frontend-web && npm run test -- tests/chat-shell.contract.test.tsx tests/api-client.contract.test.ts` -> `39 passed`
- `cd frontend-web && npx eslint components/chat/use-chat-logic.ts lib/api-client.ts tests/chat-shell.contract.test.tsx tests/api-client.contract.test.ts` -> pass
- `cd frontend-web && npm run typecheck` -> pass

## Task Plan - 2026-02-27 - Cloudflare Hourly Ingestion Checkpoint Optimization

### Current Focus
- Implement per-act federal-laws materialization checkpoints for hourly orchestration, wire safe workflow scheduling, and add regression coverage for both script behavior and workflow contract.

### Plan
- [x] Add/adjust script unit tests that prove unchanged federal-law acts are skipped across runs and full-sync windows force refresh.
- [x] Add workflow contract test coverage for Cloudflare-hourly scheduler wiring and schedule-safety guards.
- [x] Implement `scripts/run_cloudflare_ingestion_hourly.py` changes for per-act checkpoint persistence + cache-backed materialization reuse.
- [x] Update `.github/workflows/ingestion-jobs.yml` to run the Cloudflare-hourly scheduler with safe schedule gating and persisted checkpoint/cache paths.
- [x] Run targeted pytest + Ruff checks for touched files and record exact command outputs.

### Review
- Script updates (`scripts/run_cloudflare_ingestion_hourly.py`):
  - Added per-act federal-laws materialization checkpoints (`--federal-laws-checkpoint-path`), cache-backed section reuse (`--federal-laws-cache-dir`), and full-sync override wiring (`force_full_sync` from schedule window).
  - Added deterministic checkpoint revision hashing per index entry and cache fallback behavior that preserves full output coverage while skipping unchanged act fetch/parse work.
  - Extended materialization report payload with `acts_skipped_checkpoint`, `full_sync_forced`, and materialization state paths.
- Workflow updates (`.github/workflows/ingestion-jobs.yml`):
  - Added Cloudflare-hourly schedule trigger and a schedule-safe matrix gate using `matrix.run_on_schedule` + `matrix.schedule_cron`.
  - Added `cloudflare_hourly` matrix row running `scripts/run_cloudflare_ingestion_hourly.py`.
  - Persisted federal-laws materialization checkpoint + cache paths through pinned `actions/cache`.
- Test updates:
  - Extended `tests/test_cloudflare_ingestion_hourly_script.py` with per-act skip + full-sync refresh regression coverage.
  - Added `tests/test_ingestion_jobs_workflow.py` for Cloudflare-hourly workflow contract assertions.
- Verification evidence:
  - `PYTHONPATH=src uv run pytest -q tests/test_cloudflare_ingestion_hourly_script.py tests/test_ingestion_jobs_workflow.py` -> `8 passed in 1.87s`
  - `PYTHONPATH=src uv run ruff check scripts/run_cloudflare_ingestion_hourly.py tests/test_cloudflare_ingestion_hourly_script.py tests/test_ingestion_jobs_workflow.py` -> `All checks passed!`

## Task Plan - 2026-02-27 - Official Case Metadata Surfacing (Backend + Frontend)

### Current Focus
- Propagate SCC/FC metadata (`docket_numbers`, `source_event_type`) through backend response contracts and render it in the related-cases panel without regressing existing chat/search behavior.

### Plan
- [x] Add optional metadata fields to backend case-search/research schemas.
- [x] Map parsed court metadata in official case client and lawyer research support transformer.
- [x] Expose metadata in frontend API types and related-case UI badges/chips.
- [x] Add backend/frontend regression tests for metadata propagation and rendering.
- [x] Run integrated lint/tests/typecheck plus backend-vercel source sync validation.

### Review
- Backend updates:
  - `src/immcad_api/schemas.py`
    - Added optional `docket_numbers` and `source_event_type` on `CaseSearchResult` and `LawyerCaseSupport`.
    - Added `SourceEventType` literal union.
  - `src/immcad_api/sources/official_case_law_client.py`
    - `_to_result(...)` now maps `record.docket_numbers` and `record.source_event_type`.
  - `src/immcad_api/services/lawyer_case_research_service.py`
    - `_to_support(...)` now propagates `docket_numbers` and `source_event_type`.
  - Synced backend mirror:
    - `backend-vercel/src/immcad_api/schemas.py`
    - `backend-vercel/src/immcad_api/sources/official_case_law_client.py`
    - `backend-vercel/src/immcad_api/services/lawyer_case_research_service.py`
- Frontend updates:
  - `frontend-web/lib/api-client.ts`
    - Added optional `docket_numbers` and `source_event_type` to `CaseSearchResult` and `LawyerCaseSupport` payload types.
  - `frontend-web/components/chat/related-case-panel.tsx`
    - Render source badge, source event badge, and normalized docket chips when metadata is present.
- Test updates:
  - `tests/test_official_case_law_client.py` (`test_official_case_law_client_maps_court_metadata_fields`)
  - `tests/test_lawyer_case_research_service.py` (`test_orchestrator_propagates_case_metadata_fields`)
  - `frontend-web/tests/api-client.contract.test.ts` metadata passthrough assertions
  - `frontend-web/tests/chat-shell.contract.test.tsx` metadata badge/chip rendering assertion

### Verification evidence
- `uv run ruff check scripts/run_cloudflare_ingestion_hourly.py src/immcad_api/schemas.py src/immcad_api/sources/official_case_law_client.py src/immcad_api/services/lawyer_case_research_service.py tests/test_cloudflare_ingestion_hourly_script.py tests/test_ingestion_jobs_workflow.py tests/test_official_case_law_client.py tests/test_lawyer_case_research_service.py` -> `All checks passed!`
- `PYTHONPATH=src uv run pytest -q tests/test_cloudflare_ingestion_hourly_script.py tests/test_ingestion_jobs_workflow.py tests/test_official_case_law_client.py tests/test_lawyer_case_research_service.py tests/test_case_search_service.py tests/test_lawyer_research_schemas.py` -> `44 passed`
- `cd frontend-web && npm run test -- tests/chat-shell.contract.test.tsx tests/api-client.contract.test.ts` -> `37 passed`
- `cd frontend-web && npx eslint components/chat/related-case-panel.tsx lib/api-client.ts tests/chat-shell.contract.test.tsx tests/api-client.contract.test.ts tests/fixtures/chat-contract-fixtures.ts` -> pass
- `cd frontend-web && npm run typecheck` -> pass
- `uv run python scripts/validate_backend_vercel_source_sync.py` -> pass

## Task Plan - 2026-02-27 - Production Incident: `/api/chat` 530 Tunnel Failure

### Current Focus
- Eliminate opaque frontend `530` failures by mapping Cloudflare Tunnel `1033` outages to deterministic API error envelopes, and capture operational recovery steps.

### Plan
- [x] Reproduce production failure on both frontend proxy route and backend API domain.
- [x] Confirm root cause from response payload/headers (Cloudflare Tunnel `1033`, unresolved origin tunnel host).
- [x] Implement proxy mapping from upstream `530` tunnel outage HTML/plaintext to structured `503` JSON error with trace id.
- [x] Implement chat-origin fallback routing (`IMMCAD_API_BASE_URL_FALLBACK`) for automatic retry when primary chat origin is unreachable/tunnel-down.
- [x] Expand fallback-origin retry to critical JSON routes (search/research/export) with replay-safe request buffering.
- [x] Add frontend backend-proxy contract tests for chat/search outage mapping.
- [ ] Complete operational tunnel recovery (requires runtime tunnel token/secrets not present in this workspace).

### Review
- Root cause evidence:
  - `POST https://immcad.arkiteto.dpdns.org/api/chat` -> `530` with body `error code: 1033`
  - `GET https://immcad-api.arkiteto.dpdns.org/healthz` -> Cloudflare Tunnel error page (`host ... configured as a Cloudflare Tunnel ... unable to resolve it`)
  - Local runtime health command fails due missing runtime state: `make backend-cf-codespace-runtime-health` -> missing `/tmp/immcad-codespace-named-origin/state.env`
- Code updates:
  - `frontend-web/lib/backend-proxy.ts`
    - Added `mapCloudflareTunnelOutageResponse(...)` and wired it into upstream response mapping path.
    - Tunnel `1033` responses now become structured `503` proxy errors with preserved trace id.
    - Added chat fallback-origin retry path using `backendFallbackBaseUrl` from runtime config.
    - Expanded fallback-origin retry eligibility to `chat/search/research/export` routes and ensured replay-safe request buffering for those route bodies.
    - Added response header marker `x-immcad-origin-fallback: used` when fallback origin serves the request.
  - `frontend-web/lib/server-runtime-config.ts`
    - Added optional `IMMCAD_API_BASE_URL_FALLBACK` parsing and hardened-mode HTTPS validation.
  - `frontend-web/wrangler.jsonc`
    - Added production fallback origin var for emergency chat failover.
  - `frontend-web/.dev.vars.example`
    - Added optional fallback origin variable example.
- `frontend-web/tests/backend-proxy.contract.test.ts`
  - Added chat-route contract test for `530` -> `503 PROVIDER_ERROR`.
  - Added case-search contract test for `530` -> `503 SOURCE_UNAVAILABLE`.
  - Added fallback-origin retry tests (primary tunnel outage and primary network failure).
  - Added case-search fallback retry test for primary tunnel outage.
- `frontend-web/tests/server-runtime-config.contract.test.ts`
  - Added fallback var parsing + hardened validation coverage.
- `docs/development-environment.md`
  - Documented optional fallback var usage in Cloudflare env config section.
- Verification:
  - `npm run test --prefix frontend-web -- --run tests/backend-proxy.contract.test.ts tests/server-runtime-config.contract.test.ts` -> `38 passed`
  - `npm run lint --prefix frontend-web -- --file lib/backend-proxy.ts --file tests/backend-proxy.contract.test.ts` -> pass
  - `npm run lint --prefix frontend-web -- --file lib/server-runtime-config.ts --file tests/server-runtime-config.contract.test.ts` -> pass
  - `npm run typecheck --prefix frontend-web` -> pass
  - Deployed `frontend-web` worker via `wrangler deploy` -> `Current Version ID: d39fe567-1024-4190-a15f-505766585119`
  - Live probes:
    - `POST /api/chat` -> `200` with `x-immcad-origin-fallback: used`
    - `POST /api/search/cases` -> `200` with `x-immcad-origin-fallback: used`
    - `POST /api/research/lawyer-cases` -> `503 SOURCE_UNAVAILABLE` with `x-immcad-origin-fallback: used` (expected if fallback backend route itself unavailable)

## Task Plan - 2026-02-27 - Cloudflare Environment Variable Migration Hardening

### Current Focus
- Complete Cloudflare-first environment variable migration so runtime, CI, and operations no longer depend on Vercel env artifacts for primary paths.

### Plan
- [x] Add Cloudflare env configuration validation script and wire it into `make quality`.
- [x] Add runtime-neutral backend source-sync validation target/script and update quality/release workflows.
- [x] Move Cloudflare runtime script/systemd default env path to `ops/runtime/.env.backend-origin`.
- [x] Add backend-origin env materialization helper (`prepare_backend_origin_env.sh`) with transitional Vercel import mode.
- [x] Update deploy/runbook docs and contract tests for Cloudflare env assumptions.
- [x] Reconcile backend mirror drift reported by source-sync validator (`api/routes/documents.py`, `ingestion/jobs.py`, `services/document_package_service.py`, `sources/canada_courts.py`) and re-run parity gate.

### Review
- Added:
  - `scripts/validate_cloudflare_env_configuration.py`
  - `scripts/validate_backend_runtime_source_sync.py`
  - `scripts/prepare_backend_origin_env.sh`
  - `tests/test_validate_cloudflare_env_configuration.py`
- Updated:
  - `Makefile` (`cloudflare-env-sync`, `cloudflare-env-validate`, `backend-origin-env-prepare`, `backend-runtime-sync-validate`, `quality`)
  - `.github/workflows/quality-gates.yml`
  - `.github/workflows/release-gates.yml`
  - `tests/test_quality_gates_workflow.py`
  - `tests/test_release_gates_workflow.py`
  - `scripts/run_cloudflare_quick_tunnel_bridge.sh`
  - `scripts/run_cloudflare_named_tunnel_codespace_runtime.sh`
  - `scripts/install_cloudflare_named_tunnel_systemd_stack.sh`
  - `scripts/check_cloudflare_named_tunnel_codespace_runtime_health.sh`
  - `ops/systemd/immcad-backend-local.service`
  - `frontend-web/wrangler.jsonc`
  - `backend-cloudflare/wrangler.toml`
  - `frontend-web/.dev.vars.example`
  - `tests/test_settings.py`
  - `frontend-web/tests/server-runtime-config.contract.test.ts`
  - `docs/development-environment.md`
  - `docs/release/pre-deploy-command-sheet-2026-02-25.md`
  - `docs/release/compiled-binder-rollout-playbook.md`
- Verification evidence:
  - `./scripts/venv_exec.sh pytest -q tests/test_quality_gates_workflow.py tests/test_release_gates_workflow.py tests/test_validate_cloudflare_env_configuration.py tests/test_settings.py` -> `118 passed`
  - `npm run test --prefix frontend-web -- --run tests/server-runtime-config.contract.test.ts` -> `15 passed`
  - `./scripts/venv_exec.sh ruff check scripts/validate_cloudflare_env_configuration.py scripts/validate_backend_runtime_source_sync.py tests/test_validate_cloudflare_env_configuration.py tests/test_quality_gates_workflow.py tests/test_release_gates_workflow.py tests/test_settings.py` -> pass
  - `./scripts/venv_exec.sh python scripts/validate_cloudflare_env_configuration.py` -> pass
- `./scripts/venv_exec.sh python scripts/validate_backend_runtime_source_sync.py` -> pass

## Task Plan - 2026-02-27 - Step 7: HTTPS Enforcement Guardrails for Document Endpoints

### Current Focus
- Execute Priority 1 by adding enforceable HTTPS checks for document upload/retrieval paths, while keeping proxy-compatible operation and explicit policy errors.

### Plan
- [x] Add runtime setting for document-route HTTPS enforcement with hardened-environment defaults.
- [x] Add middleware check for `/api/documents/*` that accepts trusted proxy HTTPS signals and rejects plain HTTP.
- [x] Add settings + API scaffold tests for blocked/non-blocked behavior.
- [x] Update API contract + checklist notes to reflect the runtime control and remaining deployment verification.
- [x] Sync backend-vercel mirror and verify lint/tests/parity.

### Review
- Runtime/settings:
  - `src/immcad_api/settings.py`
    - Added `document_require_https` setting.
    - Added `DOCUMENT_REQUIRE_HTTPS` parsing with hardened default (`true` in `production/prod/ci`).
    - Added hardened-environment validation: rejects `DOCUMENT_REQUIRE_HTTPS=false`.
  - `src/immcad_api/main.py`
    - Added HTTPS detection helper supporting:
      - request scheme
      - `x-forwarded-proto` / `x-forwarded-protocol`
      - Cloudflare `cf-visitor` JSON scheme
    - Added middleware gate for `/api/documents/*`:
      - returns `400 VALIDATION_ERROR`
      - `policy_reason=document_https_required`
      - message: `HTTPS is required for document upload and retrieval endpoints`
- Tests:
  - `tests/test_settings.py`
    - Added defaults/validation coverage for `DOCUMENT_REQUIRE_HTTPS`.
  - `tests/test_api_scaffold.py`
    - Added blocked path test when HTTPS enforcement is enabled.
    - Added allowed path test with `x-forwarded-proto: https`.
- Docs:
  - `docs/architecture/api-contracts.md`
    - Added policy note for `document_https_required`.
  - `docs/release/document-intake-security-compliance-checklist.md`
    - Updated TLS line to reflect runtime gate availability and pending deployment verification.
- Verification evidence:
  - `PYTHONPATH=src uv run pytest -q tests/test_settings.py tests/test_api_scaffold.py` -> `140 passed`
  - `PYTHONPATH=src uv run ruff check src/immcad_api/main.py src/immcad_api/settings.py tests/test_settings.py tests/test_api_scaffold.py` -> pass
  - `PYTHONPATH=src uv run ruff check backend-vercel/src/immcad_api/main.py backend-vercel/src/immcad_api/settings.py` -> pass
  - `PYTHONPATH=src uv run python scripts/validate_backend_vercel_source_sync.py` -> pass

## Task Plan - 2026-02-27 - Cloudflare Free Optimization (SCC/FC/Laws Ingestion)

### Current Focus
- Execute official-source ingestion (SCC JSON, FC RSS, federal laws XML) with Cloudflare Free-safe scheduling and compute usage, while preserving legal-research freshness and correctness.

### Plan
- [ ] Phase 0 - Lock operating targets (no code changes)
  - Define freshness SLOs:
    - FC: `<= 2h` lag
    - SCC: `<= 6h` lag
    - Laws XML: `<= 7d` lag
  - Confirm Cloudflare Free envelope assumptions from current docs:
    - Workers Free: `100,000` requests/day, `5` Cron Triggers/account, low per-invocation CPU budget.
  - Freeze source cadences for MVP:
    - FC hourly or every 2h (default: every 2h)
    - SCC every 6h
    - Laws index check daily, full sync twice weekly

- [x] Phase 1 - Correctness-first parser hardening
  - [x] Fix FC RSS date parsing to consume namespaced `decision:date` (not only `pubDate`).
  - [x] Normalize FC/SCC event type classification (`new`, `updated`, `translated`, `corrected`).
  - [x] Surface SCC docket metadata from `_docket_numbers` into internal record/result path.
  - [x] Add fixture-based tests for live payload shapes and regression assertions.

- [ ] Phase 2 - Cloudflare-safe scheduler design
  - [x] Implement a single hourly scheduler entrypoint with modulo-gated source runs:
    - every hour: FC
    - every 6th hour: SCC
    - [x] specific UTC hours/days: laws checks (`daily` + `Tue/Fri full-sync window flag`)
  - [x] Add per-source checkpoints (separate state keys/files) to avoid race/collision across runs.
  - [x] Add `source_id`-scoped execution mode in ingestion runner to avoid unnecessary cross-source runs.

- [ ] Phase 3 - Bandwidth and CPU minimization
  - SCC/FC:
    - fetch feed, fingerprint items by `(source_id, case_id, modified/event, url)`, process deltas only.
    - [x] short-circuit unchanged payloads via checkpoint checksum to `not_modified` on HTTP `200`.
  - Laws XML:
    - [x] use `HEAD` on `Legis.xml` to read `Last-Modified`/`ETag`;
    - [x] only `GET` + parse full index when changed;
    - [x] fetch per-Act XML for targeted Acts during laws materialization runs.
  - Ensure each scheduled invocation does bounded work (chunked batches) with continuation checkpoints.

- [ ] Phase 4 - Ingestion materialization path
  - Add normalized ingestion outputs for:
    - FC/SCC decisions (metadata + source event type + document URL)
    - [x] federal laws sections (`Act -> Part/Heading -> Section`) with version fields (`CurrentToDate`, content hash)
  - Ensure outputs are consumable by existing citation/export policy gates.

- [ ] Phase 5 - Ops guardrails and rollback
  - Emit per-source metrics: poll success, delta count, parse failures, lag minutes.
  - Add alert thresholds for:
    - sustained fetch failures
    - parser failure spike
    - lag SLO breach
  - Document rollback toggles:
    - disable laws full sync
    - widen SCC cadence
    - FC metadata-only fallback mode

- [ ] Phase 6 - Verification and release
  - [x] Run targeted tests for parsers, ingestion runner, and policy gating.
  - Run conformance check against live SCC/FC feeds and capture report artifact.
  - Validate Cloudflare schedule matrix in staging for 48h and confirm no quota/CPU breaches.
  - Update docs (`docs/research`, `docs/release`) with final cadence, limits, and runbook links.

### Acceptance Criteria
- FC records use correct decision dates from live RSS payloads.
- SCC records include dockets for anchor matching.
- Hourly scheduler stays within Cloudflare Free limits with zero quota alerts over 48h.
- Feed delta processing prevents duplicate re-processing for unchanged items.
- Laws sync does not download `Legis.xml` when `Last-Modified/ETag` unchanged.
- All new tests and conformance checks pass.

### Review
- Implemented in this iteration:
  - `src/immcad_api/sources/canada_courts.py`
    - Added FC namespaced `decision:date` parsing fallback before `pubDate`.
    - Added SCC docket extraction (`_docket_numbers` and related fields) and normalized source event classification.
    - Added source-event classification for Decisia RSS records.
  - `src/immcad_api/ingestion/jobs.py`
    - Added `source_ids`-scoped execution filter to `run_ingestion_jobs(...)`.
    - Added checksum-aware `not_modified` short-circuit on unchanged HTTP `200` payloads.
  - `scripts/run_ingestion_jobs.py`
    - Added repeatable CLI flag `--source-id` and wired it to ingestion runner filtering.
  - `scripts/run_cloudflare_ingestion_hourly.py`
    - Added Cloudflare-hourly scheduler wrapper that computes UTC window source sets:
      - FC hourly
      - SCC every 6 hours
      - Federal laws daily check + Tue/Fri full-sync window flag
    - Added dry-run and ingestion-execution modes with JSON report output.
  - `src/immcad_api/ingestion/jobs.py`
    - Added source-aware `HEAD` probe for `FEDERAL_LAWS_BULK_XML` to avoid downloading `Legis.xml` when `ETag`/`Last-Modified` is unchanged.
  - `src/immcad_api/sources/federal_laws_bulk_xml.py`
    - Added federal laws bulk index parser (`Legis.xml`) and section chunk parser (`Statute/Regulation XML`).
    - Added registry target-source mapping for laws-backed statute/regulation sources.
  - `scripts/run_cloudflare_ingestion_hourly.py`
    - Added federal laws materialization step when laws source ingestion is successful.
    - Writes JSONL section chunks artifact (`--federal-laws-output`) and includes materialization summary in scheduler report JSON.
  - `data/sources/canada-immigration/registry.json` + `config/source_policy.yaml`
    - Added `FEDERAL_LAWS_BULK_XML` official source registration/policy.
  - Tests:
    - Extended parser tests for FC namespaced date/event and SCC docket/event parsing.
    - Added ingestion tests for `source_ids` filtering and checksum unchanged behavior.
    - Added CLI parse test for repeated `--source-id`.
    - Added laws `HEAD`-probe ingestion test and hourly scheduler script tests.
    - Added federal laws parser/materialization tests (`tests/test_federal_laws_bulk_xml.py`).
- Verification evidence:
  - `uv run pytest -q tests/test_canada_courts.py tests/test_ingestion_jobs.py tests/test_run_ingestion_jobs_script.py tests/test_official_case_law_client.py` -> `50 passed`.
  - `uv run ruff check src/immcad_api/sources/canada_courts.py src/immcad_api/ingestion/jobs.py scripts/run_ingestion_jobs.py tests/test_canada_courts.py tests/test_ingestion_jobs.py tests/test_run_ingestion_jobs_script.py` -> pass.
  - `uv run pytest -q tests/test_canada_courts.py tests/test_official_case_law_client.py tests/test_ingestion_jobs.py tests/test_run_ingestion_jobs_script.py tests/test_cloudflare_ingestion_hourly_script.py tests/test_canada_registry.py tests/test_validate_source_registry.py` -> `62 passed`.
  - `uv run pytest -q tests/test_canada_courts.py tests/test_official_case_law_client.py tests/test_ingestion_jobs.py tests/test_run_ingestion_jobs_script.py tests/test_cloudflare_ingestion_hourly_script.py tests/test_federal_laws_bulk_xml.py tests/test_canada_registry.py tests/test_validate_source_registry.py tests/test_source_policy.py` -> `86 passed`.

## Task Plan - 2026-02-27 - Step 6: Unreadable-File Remediation Guidance (API + UI)

### Current Focus
- Close the remaining checklist gap by returning user-actionable remediation guidance for unreadable/failed uploads and rendering that guidance directly in the document workflow UI.

### Plan
- [x] Extend intake result schema with structured issue details (`code`, `message`, `severity`, `remediation`) while preserving legacy `issues[]`.
- [x] Populate deterministic remediation guidance for unreadable/type/size intake failures.
- [x] Update frontend intake types/mapping and render remediation guidance on upload cards.
- [x] Add backend/frontend regression tests for remediation payload + UI rendering.
- [x] Sync backend-vercel mirror and run targeted verification/lint/parity checks.

### Review
- Backend:
  - `src/immcad_api/schemas.py`
    - Added `remediation` to `DocumentIssue`.
    - Added `issue_details` to `DocumentIntakeResult`.
  - `src/immcad_api/services/document_intake_service.py`
    - Added deterministic failure templates and `issue_detail_for_failed_result(...)`.
    - `build_failed_result(...)` now emits structured `issue_details`.
  - `src/immcad_api/api/routes/documents.py`
    - Ensured route-built failed results include structured `issue_details`, including fallback patching for custom intake stubs that omit details.
- Frontend:
  - `frontend-web/lib/api-client.ts`
    - Added intake `issue_details` payload typing.
  - `frontend-web/components/chat/types.ts`
    - Added `DocumentUploadIssueDetail` and `DocumentUploadItem.issueDetails`.
  - `frontend-web/components/chat/use-chat-logic.ts`
    - Mapped `issue_details` into UI state with dedupe + fallback issue-code handling.
  - `frontend-web/components/chat/related-case-panel.tsx`
    - Added upload-card guidance line: `Next step: <remediation>`.
- Tests/docs:
  - Added/updated backend tests:
    - `tests/test_document_intake_schemas.py`
    - `tests/test_document_intake_service.py`
    - `tests/test_document_routes.py`
    - `tests/test_document_upload_security.py`
  - Added frontend contract coverage:
    - `frontend-web/tests/chat-shell.contract.test.tsx` (`renders remediation guidance for unreadable failed uploads`)
  - Updated docs:
    - `docs/architecture/api-contracts.md` (`issue_details[]` contract note)
    - `docs/release/document-intake-security-compliance-checklist.md` (marked unreadable remediation control complete)
- Verification evidence:
  - `PYTHONPATH=src uv run pytest -q tests/test_document_intake_schemas.py tests/test_document_intake_service.py tests/test_document_routes.py tests/test_document_upload_security.py` -> `82 passed`
  - `PYTHONPATH=src uv run ruff check src/immcad_api/schemas.py src/immcad_api/services/document_intake_service.py src/immcad_api/api/routes/documents.py tests/test_document_intake_schemas.py tests/test_document_intake_service.py tests/test_document_routes.py tests/test_document_upload_security.py` -> pass
  - `npm --prefix frontend-web run test -- --run tests/chat-shell.contract.test.tsx tests/document-compilation.contract.test.tsx` -> `24 passed`
  - `npm --prefix frontend-web run typecheck` -> pass
  - `npm --prefix frontend-web run lint -- --file components/chat/related-case-panel.tsx --file components/chat/types.ts --file components/chat/use-chat-logic.ts --file lib/api-client.ts --file tests/chat-shell.contract.test.tsx` -> pass
  - `PYTHONPATH=src uv run python scripts/validate_backend_vercel_source_sync.py` -> pass

## Task Plan - 2026-02-27 - Step 5: Classification Override Audit Trail + Deadline/Channel Guardrail Restoration

### Current Focus
- Close the remaining checklist gap for classification-override audit coverage and restore intake deadline/submission-channel enforcement paths so document readiness/package behavior remains policy-safe.

### Plan
- [x] Add a dedicated classification-override API route and record override audit events in request metrics.
- [x] Extend `/ops/metrics` telemetry with `document_classification_override` counters/policy reasons/audit stream.
- [x] Preserve filing-context metadata across classification overrides and enforce deadline blocks in package/download routes.
- [x] Re-verify submission-channel constraints and deadline regression behavior in document route tests.
- [x] Sync backend-vercel mirror, update checklist/docs, and run verification.

### Review
- API/route updates:
  - `src/immcad_api/api/routes/documents.py`
    - Added `PATCH /api/documents/matters/{matter_id}/classification`.
    - Added classification-override audit recording (`updated`/`rejected`) with policy reasons.
    - Preserved `filing_context` in matter updates after override.
    - Restored package/package-download deadline blocking checks via `_evaluate_filing_deadline_for_matter(...)`.
    - Preserved submission-channel + filing-context validation behavior and near-limit warnings in intake flow.
- Telemetry updates:
  - `src/immcad_api/telemetry/request_metrics.py`
    - Added `record_document_classification_override_event(...)`.
    - Added `request_metrics.document_classification_override` snapshot block:
      - `attempts`, `updated`, `rejected`, `rejected_rate`, `policy_reasons`, `audit_recent`.
- Schema updates:
  - `src/immcad_api/schemas.py`
    - Added `DocumentClassificationOverrideRequest`.
- Mirror sync:
  - Synced `backend-vercel/src/immcad_api/` from `src/immcad_api/` and validated parity.
- Docs/checklist updates:
  - `docs/release/document-intake-security-compliance-checklist.md`
    - Marked classification-override audit-trail control complete.
  - `docs/architecture/api-contracts.md`
    - Added contract section for `PATCH /api/documents/matters/{matter_id}/classification`.
  - `docs/release/document-intake-incident-runbook.md`
    - Added override route scope + classification-override audit fields for incident evidence capture.
  - `docs/release/incident-observability-runbook.md`
    - Added `document_classification_override.rejected_rate` to baseline telemetry fields.
- Verification evidence:
  - `PYTHONPATH=src uv run pytest -q tests/test_document_routes.py tests/test_request_metrics.py tests/test_document_matter_store.py` -> `44 passed`
  - `PYTHONPATH=src uv run ruff check src/immcad_api/api/routes/documents.py src/immcad_api/telemetry/request_metrics.py src/immcad_api/schemas.py src/immcad_api/services/document_matter_store.py tests/test_document_routes.py tests/test_request_metrics.py tests/test_document_matter_store.py` -> pass
  - `PYTHONPATH=src uv run python scripts/validate_backend_vercel_source_sync.py` -> pass
  - `make docs-audit` -> pass (`[docs-maintenance] audited files: 80`)
  - `PYTHONPATH=src uv run pytest -q tests/test_doc_maintenance.py` -> `13 passed`

## Task Plan - 2026-02-27 - Frontend/API Court-Source Visibility Audit

### Current Focus
- Audit how users can discover available court sources (SCC/FC/FCA/superior court), which controls exist in frontend workflows, and which API endpoints expose source metadata.

### Plan
- [x] Locate frontend visibility surfaces for source/court availability.
- [x] Trace frontend controls to backend request payloads and response fields.
- [x] Enumerate source-metadata endpoints and fields exposed through API and proxy layers.
- [x] Identify MVP UX gaps for source discoverability and court coverage clarity.

### Review
- Frontend visibility and control surfaces were mapped across:
  - `/sources` transparency page.
  - Case-law research sidebar controls in chat workflow.
  - Per-result source/court badges and source-status summary chips.
- API integration mapping confirmed:
  - Dedicated source transparency endpoint (`GET /api/sources/transparency`) with policy + freshness metadata.
  - Case search/research endpoints expose per-case source metadata and aggregate source-status.
  - Next.js proxy routes forward all source-related endpoints to backend.
- MVP gaps captured for user-facing clarity:
  - No discoverable nav path to `/sources` from the main shell.
  - No explicit superior-court coverage representation in controls or transparency payload/UI.
  - Transparency UI omits several available metadata fields (policy flags, URLs, freshness seconds).

## Task Plan - 2026-02-27 - MVP Case-Law Storage/Retrieval Audit

### Current Focus
- Audit where MVP case-law data lives, how runtime retrieval works, and whether SCC/FC/FCA data survives process restarts.

### Plan
- [ ] Inventory storage surfaces for ingested case-law data (filesystem artifacts, source registry, in-process cache, Chroma/legacy paths).
- [ ] Trace runtime retrieval flow and citation/index behavior from API routes through source clients.
- [ ] Assess restart persistence guarantees for FC/FCA/SCC and identify policy gates that shape storage/output behavior.
- [ ] Map current tests to these flows and call out concrete coverage gaps.
- [ ] Deliver findings with exact file/function references.

### Review
- In progress.

## Task Plan - 2026-02-27 - Step 4: Contract Regression Closure (Record Sections + Generate Gating)

### Current Focus
- Close the active regression where `record_sections` completeness fields were dropped from backend package outputs and the frontend blocked package-generation diagnostics when readiness was false.

### Plan
- [x] Restore backend package `record_sections` contract fields (`section_status`, `slot_statuses`, `missing_document_types`, `missing_reasons`) in both source trees.
- [x] Update frontend generate-button gating so users can request package diagnostics even when readiness is not yet satisfied.
- [x] Re-run failing backend/frontend regression suites and confirm green.

### Review
- Backend:
  - `src/immcad_api/services/document_package_service.py`
    - `build_package(...)` now returns hydrated `record_sections` with completeness metadata via `_build_record_sections(...)` + `_hydrate_record_sections(...)`.
  - `backend-vercel/src/immcad_api/services/document_package_service.py`
    - Mirrored the same contract-restoring changes.
- Frontend:
  - `frontend-web/components/chat/related-case-panel.tsx`
    - Removed readiness-based disable condition from Generate Package (`disableGeneratePackage` now only depends on in-flight controls + `matter_id` presence).
- Verification evidence:
  - `PYTHONPATH=src uv run pytest -q tests/test_document_package_service.py tests/test_document_compilation_routes.py` -> `28 passed`
  - `npm --prefix frontend-web run test -- --run tests/document-compilation.contract.test.tsx` -> `4 passed`
  - `PYTHONPATH=src uv run pytest -q tests/test_document_package_service.py tests/test_document_compilation_routes.py tests/test_document_compilation_e2e.py tests/test_request_metrics.py tests/test_document_routes.py` -> `66 passed`
  - `npm --prefix frontend-web run test -- --run tests/document-compilation.contract.test.tsx tests/chat-shell.contract.test.tsx tests/chat-shell.ui.test.tsx` -> `31 passed`

## Task Plan - 2026-02-27 - Step 3: Intake Incident Runbook (Triage + Rollback)

### Current Focus
- Close the remaining operational-readiness gap by publishing an explicit document-intake incident runbook with triage and rollback steps, then link it into release checklists.

### Plan
- [x] Add a dedicated release runbook for document-intake incidents with alert triggers, evidence capture, triage matrix, stabilization controls, rollback actions, and exit criteria.
- [x] Link runbook into `document-intake-security-compliance-checklist.md` and mark incident-runbook control complete.
- [x] Align `incident-observability-runbook.md` threshold guidance with intake-specific alert rules.
- [x] Run documentation quality verification and record evidence.

### Review
- Added:
  - `docs/release/document-intake-incident-runbook.md`
    - Includes detection thresholds (`document_intake_rejected_rate`, `document_intake_parser_failure_rate`), `make ops-alert-eval` evidence capture, triage decision matrix, stabilization controls (`DOCUMENT_UPLOAD_MAX_*`, `DOCUMENT_ALLOWED_CONTENT_TYPES`), rollback flow, and closure criteria.
- Updated:
  - `docs/release/document-intake-security-compliance-checklist.md`
    - Marked incident runbook requirement complete with direct file reference.
  - `docs/release/incident-observability-runbook.md`
    - Added intake metrics to baseline telemetry and intake-threshold bullets in triage guidance.
- Verification evidence:
  - `make docs-audit` -> pass (`[docs-maintenance] audited files: 80`)
  - `PYTHONPATH=src uv run pytest -q tests/test_doc_maintenance.py` -> `13 passed`

## Task Plan - 2026-02-27 - Step 2: Intake Failure Alert Thresholds (Upload + Parser)

### Current Focus
- Define and enforce operational alert thresholds for sustained document-upload failures and parser-error spikes using `/ops/metrics` + ops alert evaluator rules.

### Plan
- [x] Extend intake telemetry with parser-failure aggregation fields in `RequestMetrics`.
- [x] Wire documents intake route to emit parser-failure counts from deterministic issue codes.
- [x] Add alert rules for `document_intake_rejected_rate` and `document_intake_parser_failure_rate`.
- [x] Add/adjust tests for telemetry fields and alert-evaluator behavior with new rules.
- [x] Sync backend-vercel mirror and verify parity/tests/lint.

### Review
- Telemetry:
  - `src/immcad_api/telemetry/request_metrics.py`
    - Added `parser_failure_files` + `parser_failure_rate` to `document_intake` snapshot payload.
    - Extended intake event recording to accept and store `parser_failure_files`.
  - `backend-vercel/src/immcad_api/telemetry/request_metrics.py`
    - Synced mirrored telemetry implementation.
- Route wiring:
  - `src/immcad_api/api/routes/documents.py`
    - Added generalized issue-code counting helper and now records parser-failure file counts (`file_unreadable`) on intake telemetry events.
  - `backend-vercel/src/immcad_api/api/routes/documents.py`
    - Synced mirrored route instrumentation.
- Ops alert thresholds:
  - `config/ops_alert_thresholds.json`
    - Added `document_intake_rejected_rate` rule.
    - Added `document_intake_parser_failure_rate` rule.
    - Bumped config version to `2026-02-27`.
- Tests:
  - `tests/test_request_metrics.py`
    - Added assertions for parser-failure fields in populated and empty snapshots.
    - Extended compilation/intake telemetry assertions to include new payload shape.
  - `tests/test_document_routes.py`
    - Added parser-failure intake telemetry regression (`_UnreadableStubIntakeService` path).
    - Extended intake telemetry assertions with parser-failure fields.
  - `tests/test_ops_alert_evaluator.py`
    - Added explicit breach-case coverage for new intake-failure rules.
- Checklist update:
  - `docs/release/document-intake-security-compliance-checklist.md`
    - Marked alert-threshold item complete for upload/parser failure coverage.
    - Clarified audit-trail note: package-generation audit exists; classification-override audit remains pending.
- Verification evidence:
  - `PYTHONPATH=src uv run pytest -q tests/test_request_metrics.py tests/test_document_routes.py tests/test_ops_alert_evaluator.py tests/test_document_compilation_routes.py tests/test_document_compilation_e2e.py` -> `54 passed`
  - `PYTHONPATH=src uv run ruff check src/immcad_api/telemetry/request_metrics.py src/immcad_api/api/routes/documents.py tests/test_request_metrics.py tests/test_document_routes.py tests/test_ops_alert_evaluator.py backend-vercel/src/immcad_api/telemetry/request_metrics.py backend-vercel/src/immcad_api/api/routes/documents.py` -> pass
  - `PYTHONPATH=src uv run python scripts/validate_backend_vercel_source_sync.py` -> pass

## Task Plan - 2026-02-27 - Step 1: Document Telemetry Hardening (Audit + OCR Warning Aggregation)

### Current Focus
- Close one production-readiness gap from the security/compliance checklist by hardening document telemetry: full compilation-route audit events and OCR-warning aggregation in `/ops/metrics`.

### Plan
- [x] Extend `RequestMetrics` document telemetry shape:
  - add OCR-warning aggregation fields/rates under `document_intake`
  - add `audit_recent` event stream under `document_compilation`
- [x] Wire documents routes to emit compilation events for all package/package-download outcomes, including `404 document_matter_not_found`.
- [x] Include request/matter context in compilation audit events (`trace_id`, `client_id`, `matter_id`, `forum`, `route`, `http_status`).
- [x] Add/adjust backend tests for telemetry snapshot shape and route instrumentation.
- [x] Sync mirrored `backend-vercel` source and run targeted verification.

### Review
- Telemetry model changes:
  - `src/immcad_api/telemetry/request_metrics.py`
    - Added document-intake OCR warning aggregation (`files_total`, `ocr_warning_files`, `ocr_warning_rate`) and `rejected_rate`.
    - Added document-compilation `audit_recent` event stream with optional context (`trace_id`, `client_id`, `matter_id`, `forum`, `route`, `http_status`, `policy_reason`).
  - `backend-vercel/src/immcad_api/telemetry/request_metrics.py`
    - Synced mirror with identical telemetry shape.
- Route instrumentation:
  - `src/immcad_api/api/routes/documents.py`
    - Added OCR warning aggregation per intake request via `_count_ocr_warning_results(...)`.
    - Added compilation telemetry recording across package and package-download success/error paths, including `404 document_matter_not_found`.
  - `backend-vercel/src/immcad_api/api/routes/documents.py`
    - Synced mirror with identical instrumentation.
- Test coverage updates:
  - `tests/test_request_metrics.py`
    - Extended telemetry assertions for new intake rates and compilation `audit_recent` event context.
  - `tests/test_document_routes.py`
    - Added route-level compilation telemetry assertions for package/package-download `404/409` outcomes.
    - Added OCR-warning aggregation assertions for warning intake flow.
- Checklist update:
  - `docs/release/document-intake-security-compliance-checklist.md`
    - Marked operational metrics line as complete now that OCR warning rate and route-level compilation telemetry are exposed.
- Verification evidence:
  - `PYTHONPATH=src uv run pytest -q tests/test_request_metrics.py tests/test_document_routes.py tests/test_document_compilation_routes.py tests/test_document_compilation_e2e.py` -> `41 passed`
  - `PYTHONPATH=src uv run python scripts/validate_backend_vercel_source_sync.py` -> pass
  - `PYTHONPATH=src uv run ruff check src/immcad_api/telemetry/request_metrics.py src/immcad_api/api/routes/documents.py tests/test_request_metrics.py tests/test_document_routes.py backend-vercel/src/immcad_api/telemetry/request_metrics.py backend-vercel/src/immcad_api/api/routes/documents.py` -> pass

## Task Plan - 2026-02-27 - Review Follow-Up: Compilation Readiness + Frontend Payload Contract

### Current Focus
- Resolve review findings around profile-specific package readiness and frontend document-compilation payload handling (pagination object safety + violation key mapping compatibility).

### Plan
- [x] Fix backend package readiness evaluation to use selected compilation profile requirements.
- [x] Sync mirrored backend-vercel package service implementation for profile-aware readiness.
- [x] Ensure frontend compilation rendering safely formats object-shaped `pagination_summary` values.
- [x] Ensure frontend violation mapping supports backend keys (`violation_code`, `rule_source_url`) and legacy aliases.
- [x] Run targeted backend/frontend verification and record evidence.

### Review
- Backend:
  - `src/immcad_api/services/document_package_service.py`
    - `build_package(...)` now evaluates readiness with `_evaluate_readiness_for_profile(...)` against the resolved compilation profile.
    - Added helper logic for required-doc derivation from profile required + conditional rules.
  - `tests/test_document_package_service.py`
    - Added regression test `test_package_builder_uses_selected_profile_requirements_for_readiness`.
  - `backend-vercel/src/immcad_api/services/document_package_service.py`
    - Synced profile-aware readiness path and helper imports.
- Frontend:
  - `frontend-web/components/chat/use-chat-logic.ts`
    - `toDocumentCompilationState(...)` maps rule-violation fields with backend-first keys and legacy fallback.
  - `frontend-web/components/chat/related-case-panel.tsx`
    - Pagination summary display uses a formatter that safely handles object/string payloads.
  - `frontend-web/lib/api-client.ts`
    - `MatterPackageResponsePayload.pagination_summary` now typed for object-or-string payloads.
  - `frontend-web/components/chat/types.ts`
    - `DocumentCompilationState.paginationSummary` now typed for object-or-string payloads.
- Verification evidence:
  - `PYTHONPATH=src uv run pytest -q tests/test_document_package_service.py::test_package_builder_uses_selected_profile_requirements_for_readiness` -> `1 passed`
  - `npm --prefix frontend-web run test -- tests/document-compilation.contract.test.tsx` -> `3 passed`
  - `npm --prefix frontend-web run typecheck` -> pass
  - `npm --prefix frontend-web run lint -- --file components/chat/use-chat-logic.ts --file components/chat/related-case-panel.tsx --file components/chat/types.ts --file lib/api-client.ts` -> pass
  - `PYTHONPATH=src uv run pytest -q tests/test_document_package_service.py tests/test_document_compilation_routes.py tests/test_document_compilation_e2e.py tests/test_document_intake_schemas.py` -> `57 passed`
  - `PYTHONPATH=src uv run python scripts/validate_backend_vercel_source_sync.py` -> pass
  - `npm --prefix frontend-web run test -- tests/document-compilation.contract.test.tsx tests/chat-shell.contract.test.tsx` -> `21 passed`

## Task Plan - 2026-02-27 - Frontend Fix #3 Rule-Violation Field Mapping

### Current Focus
- Fix frontend document-compilation violation mapping so backend payload keys (`violation_code`, `rule_source_url`) populate UI rule codes/source links and blocked-reason messaging.

### Plan
- [x] Add RED frontend test coverage for backend violation keys in document compilation payload handling.
- [x] Implement minimal typed frontend mapping support for backend keys (plus legacy aliases).
- [x] Run targeted frontend verification and record command output.

### Review
- Updated `frontend-web/tests/document-compilation.contract.test.tsx` so the blocking violation uses backend keys (`violation_code`, `rule_source_url`) while warning violation keeps legacy keys (`code`, `source_url`) to preserve alias coverage.
- Updated frontend mapping in `frontend-web/components/chat/use-chat-logic.ts` to read backend keys first and fall back to legacy aliases.
- Updated `frontend-web/lib/api-client.ts` `MatterPackageRuleViolation` typing to include backend and legacy field names as optional fields.
- Verification evidence:
  - `npm --prefix /workspaces/lawglance/frontend-web run test -- tests/document-compilation.contract.test.tsx` -> `2 passed`
  - `npm --prefix /workspaces/lawglance/frontend-web run typecheck` -> pass

## Progress Note - 2026-02-27 - Document Compilation Capability Gap Doc
- Updated `docs/research/2026-02-27-document-compilation-capability-gap-assessment.md` to mark the compiled binder path as partially implemented behind a feature flag and to document residual limitations.
- Verification evidence:
  - `PYTHONPATH=src uv run pytest -q tests/test_document_package_service.py tests/test_document_matter_store.py tests/test_document_compilation_e2e.py tests/test_document_compilation_routes.py tests/test_document_intake_schemas.py` -> `61 passed in 4.23s`
  - `PYTHONPATH=src uv run ruff check src/immcad_api/schemas.py src/immcad_api/services/document_package_service.py src/immcad_api/services/document_matter_store.py src/immcad_api/api/routes/documents.py tests/test_document_package_service.py tests/test_document_matter_store.py tests/test_document_compilation_e2e.py tests/test_document_compilation_routes.py tests/test_document_intake_schemas.py backend-vercel/src/immcad_api/schemas.py backend-vercel/src/immcad_api/services/document_package_service.py backend-vercel/src/immcad_api/services/document_matter_store.py backend-vercel/src/immcad_api/api/routes/documents.py` -> pass
  - `PYTHONPATH=src uv run python scripts/validate_backend_vercel_source_sync.py` -> pass
  - `make test-document-compilation` -> `115 passed in 4.72s`

# Task Plan - 2026-02-27 - Frontend UX Priority Execution (Step-by-Step)

## Current Focus
- Execute the prioritized UX remediation sequence for the production Next.js shell: reduce workflow overload, harden mobile accessibility, improve first-run guidance, simplify intake controls, strengthen export confirmation UX, unify status feedback, and scaffold locale-ready UI behavior.

## Plan
- [x] P0.1 Add explicit workflow modes in the sidebar (`Research` vs `Documents`) to reduce cognitive load.
- [x] P0.2 Harden mobile drawer accessibility (focus trap, focus return, and dialog semantics).
- [x] P0.3 Add first-run guided flow cues with recommended next action.
- [x] P1.1 Apply progressive disclosure for advanced intake/search fields.
- [x] P1.2 Replace native `window.confirm` export approval with accessible in-app confirmation modal.
- [x] P1.3 Consolidate workflow status messaging into one consistent, actionable status surface.
- [x] P2.1 Add locale-ready frontend scaffolding (user-selectable locale + locale-aware API payloads).
- [x] Update/extend frontend tests for new UX behavior.
- [x] Run frontend verification (`npm run test`, `npm run typecheck`, `npm run lint`) and record evidence.

## Review
- Implemented UX priority stack in production frontend (`frontend-web`) with no backend contract changes.
- P0 delivery:
  - Added explicit sidebar workflow tabs (`Research`, `Documents`) with tab semantics in `frontend-web/components/chat/related-case-panel.tsx`.
  - Hardened mobile drawer accessibility (focus trap, Escape close, focus return, dialog labeling) in `frontend-web/components/chat/chat-shell-container.tsx`.
  - Added first-run guided action card in composer (`frontend-web/components/chat/message-composer.tsx`).
- P1 delivery:
  - Added progressive disclosure for advanced research intake filters in `frontend-web/components/chat/related-case-panel.tsx`.
  - Replaced native browser export confirmation with an in-app accessible modal in `frontend-web/components/chat/related-case-panel.tsx` and removed `window.confirm` dependency from `frontend-web/components/chat/use-chat-logic.ts`.
  - Consolidated workflow update messaging via `frontend-web/components/chat/status-banner.tsx` + `frontend-web/components/chat/chat-shell-container.tsx`.
- P2 delivery:
  - Added locale-ready UI scaffolding (`en-CA`, `fr-CA`) with persisted selection in `frontend-web/components/chat/chat-header.tsx` and `frontend-web/components/chat/use-chat-logic.ts`.
  - Wired locale into chat API payload in `frontend-web/components/chat/use-chat-logic.ts`.
- Test updates:
  - Updated UX contract/UI tests for tabbed workflows, advanced filter disclosure, and modal export confirmation:
    - `frontend-web/tests/chat-shell.contract.test.tsx`
    - `frontend-web/tests/chat-shell.ui.test.tsx`
- Verification evidence:
  - `npm --prefix frontend-web run test -- tests/chat-shell.ui.test.tsx tests/chat-shell.contract.test.tsx tests/document-compilation.contract.test.tsx` -> `28 passed`
  - `npm --prefix frontend-web run test` -> `86 passed`
  - `npm --prefix frontend-web run typecheck` -> pass
  - `npm --prefix frontend-web run lint` -> pass
# Task Plan - 2026-02-27 - Docs Sync for Document Intake + Matter Scoping

## Current Focus
- Align public docs with the shipped document intake/readiness/package API behavior, client-scoped matter lookup, and proxy header forwarding.

## Plan
- [x] Update canonical API contract docs with `/api/documents/*` request/response details and policy/error behavior.
- [x] Update frontend README with document proxy route and header-forwarding notes.
- [x] Update feature/development/root docs for requirement metadata + Redis-backed matter-state notes.
- [x] Run docs quality verification and record evidence.

## Review
- Updated:
  - `docs/architecture/api-contracts.md`
  - `frontend-web/README.md`
  - `docs/features/document-intake-filing-readiness.md`
  - `docs/development-environment.md`
  - `README.md`
- Incremental progress (2026-02-27):
  - Updated `docs/research/2026-02-27-document-compilation-capability-gap-assessment.md` to mark `compilation_output_mode` ambiguity mitigation as implemented and explicitly note current runtime mode is `metadata_plan_only`.
  - Confirmed `docs/research/README.md` references remain correct for current research filenames.
  - Verification evidence (incremental doc update):
    - `make docs-audit` -> pass (`[docs-maintenance] audited files: 78`)
- Verification evidence:
  - `make docs-audit` -> pass (`[docs-maintenance] audited files: 75`)

---

# Task Plan - 2026-02-27 - Review Follow-Up: Proxy Client Identity + Redis Decode Guard

## Current Focus
- Resolve review findings on document matter scoping stability through the frontend proxy and Redis decode hardening.

## Plan
- [x] Add frontend proxy coverage for forwarding stable client-identity headers to backend document routes.
- [x] Update proxy request-header builder to forward the identity headers used by backend client-id resolution.
- [x] Add Redis regression coverage for non-UTF8 stored payloads.
- [x] Guard Redis payload UTF-8 decode in the existing decode error handling path (source + mirrored backend-vercel file).
- [x] Run targeted backend/frontend tests and lint checks.

## Review
- Frontend proxy fix:
  - `frontend-web/lib/backend-proxy.ts`
    - Added forwarding of `x-real-ip`, `x-forwarded-for`, `cf-connecting-ip`, and `true-client-ip` in upstream request headers.
  - `frontend-web/tests/backend-proxy.contract.test.ts`
    - Added regression test validating those client-identity headers are forwarded on document-readiness proxy requests.
- Backend Redis decode hardening:
  - `src/immcad_api/services/document_matter_store.py`
    - Moved UTF-8 byte decode into the guarded decode/parse block so `UnicodeDecodeError` safely returns `None`.
  - `backend-vercel/src/immcad_api/services/document_matter_store.py`
    - Synced the same decode hardening change.
  - `tests/test_document_matter_store.py`
    - Added regression test ensuring non-UTF8 Redis payloads are treated as unreadable (`None`) instead of raising.
- Verification evidence:
  - `PYTHONPATH=src uv run pytest -q tests/test_document_matter_store.py` -> `5 passed`
  - `npm --prefix frontend-web run test -- tests/backend-proxy.contract.test.ts` -> `15 passed`
  - `PYTHONPATH=src uv run ruff check src/immcad_api/services/document_matter_store.py tests/test_document_matter_store.py backend-vercel/src/immcad_api/services/document_matter_store.py` -> pass
  - `npm --prefix frontend-web run lint -- --file lib/backend-proxy.ts --file tests/backend-proxy.contract.test.ts` -> pass
  - `PYTHONPATH=src uv run pytest -q tests/test_document_routes.py tests/test_document_upload_security.py tests/test_document_intake_service.py tests/test_document_package_service.py tests/test_document_requirements.py tests/test_document_intake_schemas.py tests/test_document_matter_store.py` -> `42 passed`
  - `npm --prefix frontend-web run test -- tests/backend-proxy.contract.test.ts tests/document-intake-route.contract.test.ts tests/document-readiness-route.contract.test.ts tests/document-package-route.contract.test.ts` -> `18 passed`
  - `PYTHONPATH=src uv run python scripts/validate_backend_vercel_source_sync.py` -> pass

---

# Task Plan - 2026-02-27 - Disclosure Rule Metadata + Policy Matrix Hardening

## Current Focus
- Improve disclosure/readiness outputs for court/tribunal-specific rules by adding requirement-level metadata and locking expected forum behavior with a policy-matrix test suite.

## Plan
- [x] Add RED tests for readiness/package metadata fields (rule scope + reason) and route-level readiness metadata exposure.
- [x] Add RED policy-matrix tests that assert expected missing requirements for each supported forum.
- [x] Extend policy layer with structured requirement evaluation outputs and forum-specific rationale text.
- [x] Wire readiness and package responses to include requirement metadata while preserving existing fields/contracts.
- [x] Update frontend API/type contracts to accept metadata fields without regressions.
- [x] Run targeted + broader verification and record evidence.

## Review
- Added RED-first coverage for requirement metadata and policy matrix behavior:
  - `tests/test_document_requirements.py`
    - `requirement_statuses` output includes `status`, `rule_scope`, and rationale text.
  - `tests/test_document_package_service.py`
    - Disclosure checklist entries include `rule_scope` and `reason`.
  - `tests/test_document_routes.py`
    - `/api/documents/matters/{matter_id}/readiness` includes `requirement_statuses`.
  - `tests/test_document_intake_schemas.py`
    - Readiness/package schema accepts and exposes requirement metadata.
  - `tests/test_document_policy_matrix.py`
    - Parametrized forum matrix asserts expected readiness/missing items for `federal_court_jr`, `rpd`, `rad`, `iad`, and `id`.
- Extended policy layer with structured requirement outputs:
  - `src/immcad_api/policy/document_requirements.py`
    - Added `RequirementRule`/`RequirementStatus` models.
    - Added `requirement_rules_for_forum(...)` and expanded per-forum rationale text.
    - `evaluate_readiness(...)` now returns `requirement_statuses`.
- Wired metadata through runtime responses:
  - `src/immcad_api/schemas.py`
    - Added `DocumentRequirementStatus`.
    - Added `requirement_statuses` to `DocumentReadinessResponse`.
    - Extended `DocumentDisclosureChecklistEntry` with `rule_scope` and `reason`.
  - `src/immcad_api/api/routes/documents.py`
    - Readiness response now serializes requirement metadata.
  - `src/immcad_api/services/document_package_service.py`
    - Checklist generation now carries per-rule scope/reason metadata.
- Updated frontend contracts/UX to consume rule metadata safely:
  - `frontend-web/lib/api-client.ts`
  - `frontend-web/components/chat/types.ts`
  - `frontend-web/components/chat/use-chat-logic.ts`
  - `frontend-web/components/chat/related-case-panel.tsx`
  - Added optional metadata parsing and a “Rule guidance” section for unresolved requirement rules.
- Synced mirrored backend runtime files:
  - `backend-vercel/src/immcad_api/policy/document_requirements.py`
  - `backend-vercel/src/immcad_api/services/document_package_service.py`
  - `backend-vercel/src/immcad_api/api/routes/documents.py`
  - `backend-vercel/src/immcad_api/schemas.py`
- Verification evidence:
  - RED phase:
    - `PYTHONPATH=src uv run pytest -q tests/test_document_requirements.py tests/test_document_package_service.py tests/test_document_routes.py tests/test_document_policy_matrix.py tests/test_document_intake_schemas.py` -> `7 failed` (expected).
  - Green + targeted:
    - `PYTHONPATH=src uv run pytest -q tests/test_document_requirements.py tests/test_document_package_service.py tests/test_document_routes.py tests/test_document_policy_matrix.py tests/test_document_intake_schemas.py` -> `37 passed`
    - `PYTHONPATH=src uv run ruff check src/immcad_api/policy/document_requirements.py src/immcad_api/services/document_package_service.py src/immcad_api/api/routes/documents.py src/immcad_api/schemas.py tests/test_document_requirements.py tests/test_document_package_service.py tests/test_document_routes.py tests/test_document_policy_matrix.py tests/test_document_intake_schemas.py` -> pass
    - `npm --prefix frontend-web run test -- tests/chat-shell.contract.test.tsx tests/chat-shell.ui.test.tsx tests/backend-proxy.contract.test.ts` -> `40 passed`
    - `npm --prefix frontend-web run typecheck` -> pass
    - `npm --prefix frontend-web run lint -- --file components/chat/related-case-panel.tsx --file components/chat/types.ts --file components/chat/use-chat-logic.ts --file lib/api-client.ts` -> pass
  - Broader closeout:
    - `PYTHONPATH=src uv run pytest -q tests/test_document_routes.py tests/test_document_upload_security.py tests/test_document_intake_service.py tests/test_document_package_service.py tests/test_document_requirements.py tests/test_document_intake_schemas.py tests/test_document_matter_store.py tests/test_document_extraction.py tests/test_document_policy_matrix.py tests/test_api_scaffold.py` -> `96 passed`
    - `PYTHONPATH=src uv run python scripts/validate_backend_vercel_source_sync.py` -> pass

---

# Task Plan - 2026-02-27 - Document Intake Regression Recovery + Tribunal Rule Depth

## Current Focus
- Fix newly identified intake/storage regressions with root-cause coverage first, then improve disclosure-readiness handling for court/tribunal-specific rule differences.

## Plan
- [x] Add RED tests for: JPEG signature handling, Redis store transient failures, invalid OCR env limits, and unexpected intake-service errors.
- [x] Add RED tests for expanded forum/tribunal disclosure rules and checklist alignment.
- [x] Implement minimal extraction/store/router hardening to satisfy regression tests.
- [x] Implement forum-rule profile helpers so readiness + disclosure checklist share deterministic conditional requirements.
- [x] Sync mirrored backend-vercel source files and run targeted backend/frontend verification.

## Review
- Added RED-first regression coverage:
  - `tests/test_document_extraction.py`
    - JPEG payload signature acceptance.
    - Defensive fallback when OCR limit env vars are invalid.
  - `tests/test_document_matter_store.py`
    - Redis write/read transient failure handling.
  - `tests/test_document_routes.py`
    - Unexpected intake-service exceptions now surface as server errors.
- Added RED-first forum-specific disclosure/readiness coverage:
  - `tests/test_document_requirements.py`
    - RAD requires `decision_under_review`.
    - FC JR translation upload requires `translator_declaration`.
  - `tests/test_document_package_service.py`
    - Disclosure checklist includes conditional required items from policy rules.
- Implemented hardening fixes:
  - `src/immcad_api/services/document_extraction.py`
    - Fixed signature normalization to preserve JPEG magic bytes.
    - Added safe integer env parsing with defaults for OCR limits.
    - Removed duplicate dataclass fields.
  - `src/immcad_api/services/document_matter_store.py`
    - Guarded Redis `setex/get` with warning logs and safe fallback behavior.
  - `src/immcad_api/api/routes/documents.py`
    - Narrowed per-file fallback exception handling to `ValueError` only.
- Implemented tribunal/court disclosure rule depth improvements:
  - `src/immcad_api/policy/document_requirements.py`
    - Added `required_doc_types_for_forum(...)` helper shared by policy consumers.
    - Expanded RAD/IAD required set to include `decision_under_review`.
    - Applied translation -> `translator_declaration` conditional requirement consistently.
  - `src/immcad_api/services/document_package_service.py`
    - Checklist generation now derives from shared required-rule helper.
    - Updated TOC priority maps for improved forum-specific ordering.
- Synced mirrored runtime files:
  - `backend-vercel/src/immcad_api/services/document_extraction.py`
  - `backend-vercel/src/immcad_api/services/document_matter_store.py`
  - `backend-vercel/src/immcad_api/api/routes/documents.py`
  - `backend-vercel/src/immcad_api/policy/document_requirements.py`
  - `backend-vercel/src/immcad_api/services/document_package_service.py`
- Verification evidence:
  - RED phase:
    - `PYTHONPATH=src uv run pytest -q tests/test_document_extraction.py tests/test_document_matter_store.py tests/test_document_routes.py tests/test_document_requirements.py tests/test_document_package_service.py` -> `9 failed` (expected for red).
  - Green verification:
    - `PYTHONPATH=src uv run pytest -q tests/test_document_extraction.py tests/test_document_matter_store.py tests/test_document_routes.py tests/test_document_requirements.py tests/test_document_package_service.py` -> `32 passed`
    - `PYTHONPATH=src uv run ruff check src/immcad_api/services/document_extraction.py src/immcad_api/services/document_matter_store.py src/immcad_api/api/routes/documents.py src/immcad_api/policy/document_requirements.py src/immcad_api/services/document_package_service.py tests/test_document_extraction.py tests/test_document_matter_store.py tests/test_document_routes.py tests/test_document_requirements.py tests/test_document_package_service.py` -> pass
    - `PYTHONPATH=src uv run pytest -q tests/test_document_routes.py tests/test_document_upload_security.py tests/test_document_intake_service.py tests/test_document_package_service.py tests/test_document_requirements.py tests/test_document_intake_schemas.py tests/test_document_matter_store.py tests/test_document_extraction.py tests/test_api_scaffold.py` -> `84 passed`
    - `PYTHONPATH=src uv run python scripts/validate_backend_vercel_source_sync.py` -> pass
    - `npm --prefix frontend-web run test -- tests/backend-proxy.contract.test.ts tests/document-intake-route.contract.test.ts tests/document-readiness-route.contract.test.ts tests/document-package-route.contract.test.ts` -> `17 passed`

---

# Task Plan - 2026-02-27 - Scoped Persistent Document Matter Storage

## Current Focus
- Replace in-route in-memory document matter storage with client-scoped store abstraction backed by Redis when configured, with safe in-memory fallback.

## Plan
- [x] Add RED tests for scoped matter access and new store behavior.
- [x] Implement `DocumentMatterStore` abstraction (in-memory + Redis backends + builder).
- [x] Wire documents router to use the new store and scope reads/writes by client ID.
- [x] Wire app bootstrap to construct Redis-backed store via existing `REDIS_URL`.
- [x] Sync mirrored backend-vercel source files and run targeted verification.

## Review
- Added client-scoped matter storage abstraction in:
  - `src/immcad_api/services/document_matter_store.py`
    - `InMemoryDocumentMatterStore`
    - `RedisDocumentMatterStore`
    - `build_document_matter_store(redis_url=...)` with Redis ping/fallback behavior.
- Updated documents API router to use the store abstraction instead of local per-process dict:
  - `src/immcad_api/api/routes/documents.py`
  - Matter writes/reads now scoped by resolved `request.state.client_id` (fallback `"anonymous"`).
- Wired app bootstrap to inject Redis-backed matter store when configured:
  - `src/immcad_api/main.py`
  - `build_documents_router(..., matter_store=build_document_matter_store(redis_url=settings.redis_url), ...)`
- Exported store types/builders for internal use:
  - `src/immcad_api/services/__init__.py`
- Added regression tests:
  - `tests/test_document_matter_store.py` (in-memory scope + Redis round-trip)
  - `tests/test_document_routes.py::test_documents_matter_access_is_scoped_to_client_id`
- Synced backend-vercel mirrored runtime sources:
  - `backend-vercel/src/immcad_api/main.py`
  - `backend-vercel/src/immcad_api/api/routes/documents.py`
  - `backend-vercel/src/immcad_api/services/__init__.py`
  - `backend-vercel/src/immcad_api/services/document_matter_store.py`
- Verification evidence:
  - `PYTHONPATH=src uv run pytest -q tests/test_document_routes.py::test_documents_matter_access_is_scoped_to_client_id tests/test_document_matter_store.py` -> `3 passed`
  - `PYTHONPATH=src uv run pytest -q tests/test_document_routes.py tests/test_document_upload_security.py tests/test_document_intake_service.py tests/test_document_package_service.py tests/test_document_requirements.py tests/test_document_intake_schemas.py tests/test_document_matter_store.py tests/test_api_scaffold.py` -> `64 passed`
  - `PYTHONPATH=src uv run ruff check src/immcad_api/main.py src/immcad_api/api/routes/documents.py src/immcad_api/services/__init__.py src/immcad_api/services/document_matter_store.py tests/test_document_routes.py tests/test_document_matter_store.py` -> pass
  - `PYTHONPATH=src uv run python scripts/validate_backend_vercel_source_sync.py` -> pass

---

# Task Plan - 2026-02-27 - Document Upload + Disclosure Service Hardening

## Current Focus
- Execute prioritized hardening for document upload/disclosure flow step-by-step: reduce upload memory amplification, align image intake behavior with allowlist policy, and then close telemetry/source-transparency follow-ups.

## Plan
- [x] Step 1: Reduce upload-path memory amplification (chunked backend file reads with max-size cap + avoid proxy fallback text-decoding on non-chat multipart requests).
- [x] Step 2: Align extraction behavior with allowed image formats (deterministic filetype detection and parse fallback for approved image uploads).
- [x] Step 3: Tighten all-failed intake semantics (telemetry/reporting distinction for full-request failure outcomes).
- [x] Step 4: Remove frontend hardcoded source-bucket assumptions and rely on backend-provided source status/classification.
- [x] Run verification for this step (backend pytest + ruff, frontend proxy contract tests + lint, backend/vercel source sync check).

## Review
- Backend behavior changes:
  - Parser edge cases now return `file_unreadable` per-file instead of bubbling as 500.
  - Intake now supports partial outcomes in one request (`unsupported_file_type` / `upload_size_exceeded` become per-file `failed` results).
  - Intake now reads uploads in bounded chunks with early oversize stop, reducing request-time memory spikes.
  - Extraction now supports approved image payload signatures (`png`/`jpeg`/`tiff`) in addition to PDF.
- Frontend/proxy changes:
  - Added document proxy routes:
    - `frontend-web/app/api/documents/intake/route.ts`
    - `frontend-web/app/api/documents/matters/[matterId]/readiness/route.ts`
    - `frontend-web/app/api/documents/matters/[matterId]/package/route.ts`
  - `frontend-web/lib/backend-proxy.ts` now supports:
    - byte-safe POST body forwarding (no text-decoding corruption),
    - explicit `forwardGetRequest` for readiness calls.
    - fallback body text decoding only for `/api/chat`, avoiding unnecessary binary multipart decode on document routes.
- Verification evidence:
  - `PYTHONPATH=src uv run pytest -q tests/test_document_routes.py tests/test_document_upload_security.py tests/test_document_intake_service.py tests/test_document_package_service.py tests/test_document_requirements.py tests/test_document_intake_schemas.py` -> `21 passed`
  - `npm --prefix frontend-web run test -- tests/chat-shell.contract.test.tsx tests/backend-proxy.contract.test.ts tests/document-intake-route.contract.test.ts tests/document-readiness-route.contract.test.ts tests/document-package-route.contract.test.ts` -> `33 passed`
  - `PYTHONPATH=src uv run ruff check src/immcad_api/api/routes/documents.py src/immcad_api/services/document_extraction.py src/immcad_api/services/document_intake_service.py tests/test_document_routes.py tests/test_document_upload_security.py` -> pass
  - `npm --prefix frontend-web run typecheck` -> pass
  - `npm --prefix frontend-web run lint` -> pass
  - `PYTHONPATH=src uv run python scripts/validate_backend_vercel_source_sync.py` -> pass
  - `PYTHONPATH=src uv run pytest -q tests/test_document_routes.py tests/test_document_upload_security.py tests/test_document_intake_service.py` -> `15 passed`
  - `PYTHONPATH=src uv run ruff check src/immcad_api/api/routes/documents.py src/immcad_api/services/document_extraction.py tests/test_document_upload_security.py` -> pass
  - `npm --prefix frontend-web run test -- tests/backend-proxy.contract.test.ts tests/document-intake-route.contract.test.ts tests/document-readiness-route.contract.test.ts tests/document-package-route.contract.test.ts` -> `16 passed`
  - `npm --prefix frontend-web run lint -- --file lib/backend-proxy.ts --file tests/backend-proxy.contract.test.ts` -> pass
  - `PYTHONPATH=src uv run pytest -q tests/test_document_routes.py tests/test_document_upload_security.py tests/test_document_intake_service.py tests/test_request_metrics.py` -> `21 passed`
  - `npm --prefix frontend-web run test -- tests/chat-shell.contract.test.tsx tests/chat-shell.ui.test.tsx` -> `26 passed`
  - `npm --prefix frontend-web run typecheck` -> pass

---

# Task Plan - 2026-02-26 - Canada Document Intake + Filing Readiness

## Current Focus
- Plan and execute a secure, client-friendly bulk document upload workflow with OCR/quality checks, rule-aware organization, and filing package readiness outputs for Federal Court + IRB matters.

## Plan
- [x] Publish documentation-first package (feature spec, API contract draft, security/compliance checklist) before implementation.
- [x] Finalize V1 forum/rule matrix and implement deterministic readiness policy checks.
- [x] Add backend intake schemas/contracts for multi-file upload, document issues, readiness, and package generation.
- [x] Implement intake pipeline (text extraction/OCR signals, classification, normalized naming, issue detection).
- [x] Implement package builder (TOC/index ordering, disclosure checklist, cover-letter draft, readiness summary).
- [x] Add `/api/documents/*` routes with multipart handling, traceability, and consistent error envelopes.
- [x] Add upload security controls (file type/size/count limits).
- [x] Add intake audit events for document-intake requests.
- [x] Add frontend drag/drop intake panel with per-document status and readiness UX.
- [x] Run targeted backend/frontend verification and record evidence.

## Review
- Documentation-first deliverables completed:
  - `docs/features/document-intake-filing-readiness.md` (user workflow, failure handling, acceptance criteria)
  - `docs/architecture/document-intake-api-contracts-draft.md` (draft API contracts and issue/error codes)
  - `docs/release/document-intake-security-compliance-checklist.md` (security/compliance and go-live readiness checks)
- Detailed execution plan: `docs/plans/2026-02-26-document-intake-filing-readiness-implementation-plan.md`
- Implementation completion update (2026-02-26):
  - Added document-intake audit telemetry (`document_intake` counters + recent audit events) in `src/immcad_api/telemetry/request_metrics.py` and wired intake route event recording in `src/immcad_api/api/routes/documents.py`.
  - Added frontend document-intake UX in the case-law sidebar with drag/drop + picker upload, per-document status, readiness refresh, and package generation actions via:
    - `frontend-web/components/chat/related-case-panel.tsx`
    - `frontend-web/components/chat/use-chat-logic.ts`
    - `frontend-web/components/chat/types.ts`
    - `frontend-web/components/chat/chat-shell-container.tsx`
    - `frontend-web/lib/api-client.ts`
  - Extended regression coverage:
    - `tests/test_request_metrics.py`
    - `tests/test_document_routes.py`
    - `frontend-web/tests/chat-shell.contract.test.tsx`
    - `frontend-web/tests/chat-shell.ui.test.tsx`
- Verification evidence:
  - `PYTHONPATH=src uv run pytest -q tests/test_request_metrics.py tests/test_document_routes.py tests/test_document_requirements.py tests/test_document_intake_schemas.py tests/test_document_intake_service.py tests/test_document_package_service.py tests/test_document_upload_security.py` -> `23 passed`
  - `PYTHONPATH=src uv run ruff check src/immcad_api/telemetry/request_metrics.py src/immcad_api/api/routes/documents.py tests/test_request_metrics.py tests/test_document_routes.py tests/test_document_requirements.py tests/test_document_intake_schemas.py tests/test_document_intake_service.py tests/test_document_package_service.py tests/test_document_upload_security.py` -> pass
  - `cd frontend-web && npm run test -- --run tests/chat-shell.contract.test.tsx tests/chat-shell.ui.test.tsx` -> `24 passed`
  - `cd frontend-web && npm run typecheck` -> pass
  - `make quality` -> pass

---

# Task Plan - 2026-02-26 - Retrieval Decision-Date Window Enforcement

## Current Focus
- Make date windows enforceable across case search and lawyer research orchestration so returned precedents align with requested decision-date bounds.

## Plan
- [x] Add failing tests for CanLII and official-court clients to enforce `decision_date_from`/`decision_date_to`.
- [x] Add failing orchestration tests to ensure intake date range is forwarded and defensively filtered.
- [x] Extend `CaseSearchRequest` contract with optional decision-date window and validation.
- [x] Implement decision-date filtering in source clients and lawyer research orchestration.
- [x] Run targeted and broader backend/frontend verification and capture evidence.

## Review
- Backend contract updated:
  - Added optional `decision_date_from` and `decision_date_to` to `CaseSearchRequest` with range validation (`decision_date_from <= decision_date_to`).
- Retrieval path updates:
  - `CanLIIClient` now filters candidate results by request decision-date window before limit truncation.
  - `OfficialCaseLawClient` now filters parsed court records by request decision-date window before ranking.
  - `LawyerCaseResearchService` now forwards intake date windows into internal `CaseSearchRequest` calls and applies a defensive post-search date-range filter before dedupe/ranking.
- Verification evidence:
  - `uv run pytest -q tests/test_canlii_client.py tests/test_official_case_law_client.py tests/test_lawyer_case_research_service.py` -> `36 passed`
  - `uv run pytest -q tests/test_lawyer_research_schemas.py tests/test_lawyer_research_planner.py tests/test_lawyer_case_research_service.py tests/test_lawyer_research_api.py tests/test_chat_service.py tests/test_api_scaffold.py` -> `84 passed`
  - `cd frontend-web && npm run test -- --run` -> `69 passed`
  - `cd frontend-web && npm run lint` -> pass
  - `cd frontend-web && npm run typecheck` -> pass

---

# Task Plan - 2026-02-26 - Frontend Intake Gate For Broad Case-Law Queries

## Current Focus
- Improve reliability by requiring minimal structured intake before running broad manual lawyer-research queries in the frontend.

## Plan
- [x] Add a shared case-query specificity helper so hook and panel use one low-specificity definition.
- [x] Enforce a frontend intake gate in manual case search for low-specificity queries when intake coverage is too sparse.
- [x] Preserve backend validation UX by allowing broad queries to run when intake is provided.
- [x] Extend frontend contract tests for the new gate and validation-path behavior.
- [x] Run frontend verification and capture evidence.

## Review
- Added shared query-specificity utility:
  - `frontend-web/components/chat/case-query-specificity.ts`
  - Reused by both `related-case-panel` and `use-chat-logic`.
- Added frontend intake gate behavior in manual lawyer-research:
  - For low-specificity query text, require at least 2 intake signals (`objective`, `target court`, `procedural posture`, `issue tags`, citation/docket anchor) before dispatching `/api/research/lawyer-cases`.
  - If unmet, no API call is made and a clear action message is shown:
    - `Add at least two intake details (objective, target court, issue tags, or citation/docket anchor) before running broad case-law research queries.`
- Preserved backend broad-query validation path when intake is present (frontend no longer blocks that path once intake minimum is satisfied).
- Verification evidence:
  - `cd frontend-web && npm run test -- --run tests/chat-shell.contract.test.tsx tests/chat-shell.ui.test.tsx` -> `20 passed`
  - `cd frontend-web && npm run test -- --run` -> `70 passed`
  - `cd frontend-web && npm run lint` -> pass
  - `cd frontend-web && npm run typecheck` -> pass

---

# Task Plan - 2026-02-26 - Frontend Decision-Date Intake Wiring

## Current Focus
- Improve research specificity by exposing decision-date window intake controls in the frontend and wiring them into lawyer-research requests with client-side range validation.

## Plan
- [x] Add decision-date intake controls (`from`/`to`) to the case-law panel.
- [x] Wire new intake controls into chat-state types and hooks.
- [x] Include `date_from`/`date_to` in `/api/research/lawyer-cases` payloads.
- [x] Add client-side invalid-range guard (`from` > `to`) to prevent malformed searches.
- [x] Extend frontend tests and run verification.

## Review
- Added new intake controls in the related-case panel:
  - `Decision date from`
  - `Decision date to`
- Wired date intake state and handlers through:
  - `frontend-web/components/chat/use-chat-logic.ts`
  - `frontend-web/components/chat/types.ts`
  - `frontend-web/components/chat/chat-shell-container.tsx`
- Request payload behavior:
  - `date_from` / `date_to` now included in `intake` when provided.
- Validation behavior:
  - Search is blocked client-side when `Decision date from` is later than `Decision date to`.
  - User sees: `Decision date range is invalid. 'From' date must be earlier than or equal to 'to' date.`
- Verification evidence:
  - `cd frontend-web && npm run test -- --run tests/chat-shell.contract.test.tsx tests/chat-shell.ui.test.tsx` -> `21 passed`
  - `cd frontend-web && npm run test -- --run` -> `71 passed`
  - `cd frontend-web && npm run lint` -> pass
  - `cd frontend-web && npm run typecheck` -> pass

---

# Task Plan - 2026-02-26 - Lawyer Research Reliability + Structured Intake + Confidence Transparency

## Current Focus
- Improve legal research reliability and frontend guidance by collecting structured intake details before retrieval, making ranking more intent-aware, and surfacing realistic confidence with reasons.

## Plan
- [x] Add failing backend tests for structured intake schema/planner behavior and response confidence fields.
- [x] Implement backend schema, planner, and orchestration updates for intake-aware query generation/ranking and confidence scoring.
- [x] Add failing frontend tests for intake guidance and research confidence rendering in the case-law panel.
- [x] Implement frontend UX updates for explicit intake feedback and confidence transparency.
- [x] Run targeted backend/frontend verification and capture evidence.

## Review
- Backend reliability and intent-awareness updates:
  - Added structured lawyer intake schema (`objective`, `target_court`, `procedural_posture`, `issue_tags`, citation/docket anchors, fact keywords, date window) and request contract support.
  - Extended planner to merge structured intake into profile extraction and multi-query generation (including intake anchor and objective query variants).
  - Added research confidence output (`research_confidence`, `confidence_reasons`) to lawyer research responses.
  - Updated orchestration to consume intake, apply intake-aware court routing, and compute confidence from source quality, anchors, and result strength.
- Frontend guidance and transparency updates:
  - Added intake controls in case-law panel (`Research objective`, `Target court`, `Procedural posture`, `Issue tags`, `Citation or docket anchor`).
  - Wired intake payload into `/api/research/lawyer-cases` requests without blocking existing flows.
  - Added confidence card rendering (`Research confidence: HIGH/MEDIUM/LOW`) with concise reasons.
- Continued feedback-loop enhancements:
  - Added explicit intake-quality metadata in lawyer research responses: `intake_completeness` and `intake_hints`.
  - Implemented backend intake feedback scoring using court/objective/posture/issue-tag/anchor/fact-keyword coverage with concrete missing-field hints.
  - Extended frontend case panel to display `Intake quality: HIGH/MEDIUM/LOW` and missing-input guidance from backend.
  - Kept manual search non-blocking while surfacing actionable intake guidance for higher-confidence outcomes.
- Verification evidence:
  - `uv run pytest -q tests/test_lawyer_research_schemas.py tests/test_lawyer_research_planner.py tests/test_lawyer_case_research_service.py tests/test_lawyer_research_api.py` -> `23 passed`
  - `uv run pytest -q tests/test_lawyer_research_schemas.py tests/test_lawyer_research_planner.py tests/test_lawyer_case_research_service.py tests/test_lawyer_research_api.py tests/test_chat_service.py tests/test_api_scaffold.py` -> `81 passed`
  - `uv run ruff check src/immcad_api/schemas.py src/immcad_api/services/lawyer_research_planner.py src/immcad_api/services/lawyer_case_research_service.py tests/test_lawyer_research_schemas.py tests/test_lawyer_research_planner.py tests/test_lawyer_case_research_service.py tests/test_lawyer_research_api.py` -> pass
  - `cd frontend-web && npm run test -- --run tests/chat-shell.contract.test.tsx tests/chat-shell.ui.test.tsx` -> `19 passed`
  - `cd frontend-web && npm run test -- --run tests/api-client.contract.test.ts tests/chat-shell.contract.test.tsx tests/chat-shell.ui.test.tsx` -> `33 passed`
  - `cd frontend-web && npm run test -- --run` -> `69 passed`
  - `cd frontend-web && npm run lint` -> pass
  - `cd frontend-web && npm run typecheck` -> pass
  - `uv run pytest -q` -> `483 passed`, `1 failed` (`tests/test_prompt_compatibility.py::test_legacy_prompt_constants_match_policy_prompt_constants`, pre-existing prompt-compat mismatch unrelated to intake/confidence changes)
  - `uv run pytest -q tests/test_lawyer_research_schemas.py tests/test_lawyer_case_research_service.py tests/test_lawyer_research_api.py` -> `19 passed`
  - `uv run pytest -q tests/test_lawyer_research_schemas.py tests/test_lawyer_research_planner.py tests/test_lawyer_case_research_service.py tests/test_lawyer_research_api.py tests/test_chat_service.py tests/test_api_scaffold.py` -> `82 passed`
  - `cd frontend-web && npm run test -- --run tests/chat-shell.contract.test.tsx tests/chat-shell.ui.test.tsx tests/api-client.contract.test.ts` -> `33 passed`

---

# Task Plan - 2026-02-26 - Frontend Case-Search Query Refinement UX Pass

## Current Focus
- Improve case-search interaction quality in the frontend by guiding users away from broad one-word queries and providing one-tap refinement suggestions.

## Plan
- [x] Add failing frontend UI test coverage for low-specificity query guidance and clickable refinement chips.
- [x] Implement query-specificity analysis and refinement chip rendering in the case-law panel.
- [x] Re-run frontend tests/lint/typecheck and document evidence.

## Review
- Added low-specificity guidance in the case-law panel so broad/generic queries receive immediate actionable feedback:
  - `Query may be too broad. Add at least two anchors: program/issue and court or citation.`
- Added one-tap refinement chips in the case-law panel (brand-styled buttons) generated from current query + matter profile anchors (issue tags, target court, citation seed).
- Preserved existing explicit manual-search control and retrieval provenance behavior (`Auto-retrieved` vs `Manual case search`).
- Verification evidence:
  - `cd frontend-web && npm run test -- --run tests/chat-shell.ui.test.tsx` -> `6 passed`
  - `cd frontend-web && npm run test -- --run tests/chat-shell.contract.test.tsx tests/chat-shell.ui.test.tsx tests/home-page.rollout.test.tsx tests/api-client.contract.test.ts` -> `33 passed`
  - `cd frontend-web && npm run test -- --run` -> `67 passed`
  - `cd frontend-web && npm run lint` -> pass (`next lint`, no warnings/errors)
  - `cd frontend-web && npm run typecheck` -> pass (`tsc --noEmit --incremental false`)

---

# Task Plan - 2026-02-26 - Research Retrieval and Precedent Relevance Overhaul (Backend-First)

## Current Focus
- Improve backend case-law retrieval quality, precedent relevance ranking, and query handling first, then align frontend workflow clarity so users can clearly distinguish conversation responses from case-law research outputs.

## Plan
- [x] Audit current retrieval/query/ranking/UX flows and identify root causes of weak precedent relevance and workflow confusion.
- [x] Align on architecture direction with user (intent-gated auto retrieval + manual control retained).
- [x] Produce and save approved design doc in `docs/plans/2026-02-26-research-precedent-retrieval-design.md`.
- [x] Produce detailed implementation plan in `docs/plans/2026-02-26-research-precedent-retrieval-implementation-plan.md`.
- [x] Execute backend-first implementation via TDD (intent gating, planner, ranking, validation hints, API contract updates).
- [x] Execute frontend clarity implementation via TDD (workflow labels, retrieval provenance visibility, stale-query cues).
- [x] Run targeted verification gates and document results.

## Review
- Backend-first implementation completed:
  - Added graded case-query assessment with refinement hints and stricter generic-query detection (`help with immigration` now correctly flagged as broad).
  - Updated `/api/search/cases` and `/api/research/lawyer-cases` to include actionable refinement hints in broad-query validation responses.
  - Expanded lawyer research planner with compact citation/docket anchor queries (for example `2024 FC 101 precedent`, `A-1234-23 precedent`).
  - Improved lawyer-case ranking to prioritize exact citation/docket anchors over generic token density.
  - Added intent-gated chat `research_preview` metadata (`retrieval_mode=auto`) with graceful degradation when preview lookup fails.
- Frontend clarity implementation completed:
  - Added `research_preview` contract support in frontend API types and chat-state wiring so related cases can auto-hydrate from chat responses.
  - Added explicit retrieval provenance labels in the case-law panel (`Auto-retrieved for this answer` vs `Manual case search`) to disambiguate workflow mode.
  - Improved conversation/case-law separation with chat-area labeling (`Conversation answers`, `Chat workspace`) and updated case-law panel heading/copy.
  - Normalized diagnostics API target display by trimming trailing slashes in `ChatShell` support context rendering.
- Verification evidence:
  - `PYTHONPATH=src uv run pytest -q tests/test_case_query_validation.py tests/test_lawyer_research_planner.py tests/test_lawyer_case_research_service.py tests/test_lawyer_research_api.py tests/test_case_search_service.py tests/test_chat_service.py tests/test_api_scaffold.py` -> `92 passed`
  - `make lint` -> pass (`ruff check .`, all checks passed)
  - `make test` -> partial failure (`tests/test_prompt_compatibility.py::test_legacy_prompt_constants_match_policy_prompt_constants`), unrelated to this backend retrieval change-set and already due to legacy/policy prompt divergence.
  - `cd frontend-web && npm run test -- --run tests/chat-shell.contract.test.tsx tests/chat-shell.ui.test.tsx tests/api-client.contract.test.ts` -> `30 passed`
  - `cd frontend-web && npm run test -- --run` -> `66 passed`
  - `cd frontend-web && npm run lint` -> pass (`next lint`, no warnings/errors)
  - `cd frontend-web && npm run typecheck` -> pass (`tsc --noEmit --incremental false`)

---

# Task Plan - 2026-02-26 - AI Assistant Architecture Improvement Audit

## Current Focus
- Audit IMMCAD’s current legal-assistant architecture (tooling, retrieval, reliability, policy controls) and produce prioritized improvement proposals grounded in both repo evidence and current external guidance.

## Plan
- [x] Review current backend/frontend architecture paths for chat, grounding, case-search, lawyer-research, policy, and telemetry.
- [x] Research current best-practice guidance for agent tool-calling, evals/trace grading, legal-AI governance, and case-law source constraints.
- [x] Produce a prioritized proposal document with implementation phases, acceptance metrics, and concrete next actions.

## Review
- Completed a repo-specific architecture audit across:
  - backend orchestration (`src/immcad_api/main.py`, `services/*`, `sources/*`, `policy/*`, `telemetry/*`),
  - frontend integration/runtime behavior (`frontend-web/lib/*`, `frontend-web/components/chat/*`).
- Produced a new proposal document with:
  - prioritized P0/P1/P2 architecture upgrades,
  - measurable acceptance criteria,
  - 90-day phased execution sequence,
  - external references aligned to current guidance.
- Output artifact:
  - `docs/research/2026-02-26-ai-assistant-architecture-improvements.md`

---

# Task Plan - 2026-02-26 - Brand Guidelines Frontend Polish

## Current Focus
- Apply `brand-guidelines` refinements to the active Next.js frontend (`frontend-web`) for stronger Anthropic visual consistency while preserving existing behavior.

## Plan
- [x] Add reusable brand styling primitives (pills/buttons/surfaces) in `frontend-web/app/globals.css`.
- [x] Apply the primitives to key chat-shell surfaces and remove scattered hardcoded color treatments.
- [x] Fix mobile case-law drawer accessibility wiring (`aria-controls` target + dialog semantics).
- [x] Run frontend lint + typecheck + targeted UI tests and record evidence.

## Review
- Implemented a focused brand-consistency pass using shared Anthropic styling primitives:
  - added reusable `imm-pill-*` tone classes and `imm-btn-*` action classes in `frontend-web/app/globals.css`.
  - reduced hardcoded color scattering by consuming these primitives in page header badges, chat header badges, composer controls, quick prompts, related-case actions/status chips, and diagnostics/status surfaces.
- Improved mobile drawer accessibility wiring in `frontend-web/components/chat/chat-shell-container.tsx`:
  - added `id="mobile-case-law-drawer"` to the drawer target used by `aria-controls`,
  - when open, drawer now declares dialog semantics (`role="dialog"`, `aria-modal`, `aria-label`).
- Verification evidence:
  - `npm --prefix frontend-web run lint` -> pass (`next lint`, no warnings/errors)
  - `npm --prefix frontend-web run typecheck` -> pass (`tsc --noEmit --incremental false`)
  - `npm --prefix frontend-web run test -- tests/chat-shell.ui.test.tsx tests/home-page.rollout.test.tsx` -> pass (`7 passed`)

---

# Task Plan - 2026-02-25 - Frontend Editorial Legal Desk Redesign

## Current Focus
- Rebuild the active Next.js UI (`frontend-web`) into a distinctive editorial/legal-desk experience while preserving chat/case-search/export behavior.

## Plan
- [x] Document approved redesign direction and implementation scope (editorial / legal desk) in `docs/plans/2026-02-25-frontend-editorial-legal-desk-redesign-design.md`.
- [x] Redesign page hero + chat shell layout framing for a non-generic editorial workspace feel.
- [x] Redesign transcript, message bubbles, composer, and quick prompts as a cohesive legal-desk interaction surface.
- [x] Redesign related-case and diagnostics panels to match the editorial system and preserve usability.
- [x] Run frontend lint + typecheck and record evidence.

## Review
- Approved editorial/legal-desk redesign implemented across the active Next.js UI (`frontend-web`) with preserved chat, case-law search, export, and diagnostics behavior.
- Added a reusable editorial design system layer in `frontend-web/app/globals.css` (`imm-paper-shell`, `imm-paper-card`, `imm-kicker`, `imm-ledger-textarea`, subtle page texture, fade-up motion).
- Rebuilt page masthead and chat workspace framing for a stronger legal-research desk composition, including a workspace header/status summary.
- Reworked transcript, message bubbles, source cards, composer, and quick prompts into a cohesive “dossier + ledger” interaction surface while preserving accessible names/labels used by tests.
- Reworked case-law sidebar and diagnostics panel into matching editorial cards and preserved UI contract text for test compatibility.
- Follow-up polish pass added reusable meta/status label primitives, a subtle column separator, transcript scrollbar styling + edge fades, and refined error-status tones while keeping behavior unchanged.
- Mobile-first follow-up polish tightened phone layouts (single-column workspace stats, shorter transcript viewport, full-width primary actions, long diagnostics overflow handling) while preserving all contracts.
- Verification evidence:
  - `npm --prefix frontend-web run lint` -> pass (`next lint`, no warnings/errors)
  - `npm --prefix frontend-web run typecheck` -> pass (`tsc --noEmit --incremental false`)
  - `npm --prefix frontend-web run test` -> pass (`65 passed`)

---

# Task Plan - 2026-02-25 - Anthropic Brand Guidelines UI Pass

## Current Focus
- Apply the installed `brand-guidelines` skill to the active Next.js UI (`frontend-web`) so the chat experience uses Anthropic-inspired colors and typography.

## Plan
- [x] Update global UI typography and theme tokens in `frontend-web/app/layout.tsx` and `frontend-web/app/globals.css` using the Anthropic brand palette (Poppins + Lora, dark/light/gray + accent colors).
- [x] Align Tailwind theme extension colors in `frontend-web/tailwind.config.ts` with the same palette so component utility classes stay consistent.
- [x] Patch high-visibility chat UI components (header, composer, message list, quick prompts, shell container, related case panel/support panel) to remove the strongest legacy blue/amber accents and use the new brand tones.
- [x] Run targeted frontend checks (at least lint/typecheck for touched files if available) and record results.

## Review
- UI theme pass completed across global styling and core chat surfaces:
  - typography switched to `Poppins` (heading) + `Lora` (body) in `frontend-web/app/layout.tsx`,
  - CSS tokens in `frontend-web/app/globals.css` updated to the new brand palette (dark/light gray + orange/blue/green accents),
  - Tailwind semantic colors in `frontend-web/tailwind.config.ts` aligned to the same palette,
  - high-visibility chat components updated: shell, header, composer, message list, related-case panel, quick prompts, support panel.
- Verification evidence:
  - `npm --prefix frontend-web run lint` -> pass (`next lint`, no warnings/errors)
  - `npm --prefix frontend-web run typecheck` -> pass (`tsc --noEmit --incremental false`)

---

# Task Plan - 2026-02-25 - Cloudflare Free Plan Blocker Audit

## Current Focus
- Verify (without assumptions) whether we can continue on Cloudflare free plan and document concrete blockers + next actions.

## Plan
- [x] Validate official Cloudflare free/paid Worker limits using MCP research tools (Brave + Context7) and Cloudflare docs.
- [x] Capture current deploy/runtime facts from Wrangler (`deployments list`, native deploy errors, and dry-run package sizes).
- [x] Verify engineering flow blockers (open PRs, recent CI status, pending migration tasks).
- [x] Add quota-aware alert thresholds and runbook entries for free-plan request/capacity limits.
- [x] Decide and lock backend production path on free tier (`proxy -> origin`) vs native Cloudflare backend refactor/paid-tier migration.

## Review
- Official limits verified:
  - Worker size: `3 MB` (Free) / `10 MB` (Paid).
  - Account plan request body limits: `100 MB` (Free/Pro), `200 MB` (Business), `500 MB` default (Enterprise).
  - Runtime quotas include `100,000` requests/day on Free plan, `10 ms` CPU/request on Free plan, and Free-plan subrequest cap (`50`/request).
- Current measured deployment evidence:
  - Frontend Worker dry-run: `3141.47 KiB` total / `682.47 KiB` gzip.
  - Backend proxy Worker dry-run: `2.27 KiB` total / `0.96 KiB` gzip.
  - Native Python backend dry-run: `27042.96 KiB` total / `5973.60 KiB` gzip; deploy fails with Cloudflare API `code: 10027`.
  - Native Worker deployment list confirms no successful deploy (`code: 10007` worker not found).
- Process status:
  - Open PRs: none (`gh pr list`).
  - Recent CI runs: latest listed workflows succeeded (`Quality Gates`, `CodeQL`, `Ops Metrics Alerts`).
- Interim production decision for free plan:
  - Continue with Cloudflare frontend + backend edge proxy to legacy backend origin.
  - Treat Cloudflare-native Python backend as blocked until dependency/runtime footprint is reduced below free-plan constraints or plan changes.
- Blocker mitigation implemented:
  - Added `scripts/check_cloudflare_free_plan_readiness.sh` + `make cloudflare-free-preflight` to verify frontend/proxy bundle fit on free tier and report native backend status before deploy.
  - Added pre-deploy workflow gate in `.github/workflows/cloudflare-backend-proxy-deploy.yml`.
  - Added bounded timeout/retry and traceable error responses to `backend-cloudflare/src/worker.ts` to make proxy mode safer while native backend remains blocked.
  - `scripts/release_preflight.sh` now runs the Cloudflare free-plan readiness check (unless explicitly skipped) so local release prep fails early on plan-limit surprises.
  - Deployed backend proxy mitigation to Cloudflare Workers (`1499a8af-54f0-451e-a0ac-a39f7cf9e935`, `2026-02-25T22:56:56Z`) using free-tier compatible bundle size (`2.16 KiB` gzip) and verified live custom-domain behavior (`/healthz` 200, allowlist JSON 404 with `x-immcad-edge-proxy` + `x-immcad-trace-id`).
- Quota-risk mitigation implemented:
  - Added Cloudflare free-tier API request projection checks (warn/fail thresholds) to `config/ops_alert_thresholds.json` via derived metrics in `immcad_api.ops.alert_evaluator`.
  - Updated release runbook to run `make ops-alert-eval` as a Cloudflare free-tier budget check before/after deploy.
  - Executed Vercel-free runtime cutover using Cloudflare Tunnel: local IMMCAD backend (`uvicorn` on `127.0.0.1:8001`, `ENABLE_CASE_SEARCH=true`) is now serving through Cloudflare backend proxy via a Cloudflare Quick Tunnel origin; backend proxy redeployed as `b7807e40-9c42-4a48-b683-f0967800079d` and live smokes for `/healthz`, `/api/search/cases`, and `/api/research/lawyer-cases` passed.
  - Validated named Cloudflare Tunnel automation via Cloudflare API + `cloudflared` (remote-config tunnel create/token/config + connector startup), but public named-tunnel cutover remains blocked by DNS-route permissions in the current Cloudflare auth context.
  - Attempted direct backend-proxy cutover to the named tunnel host (`a2f7845e-4751-4ba4-b8aa-160edeb69184.cfargotunnel.com`) and confirmed runtime timeouts (`504`) without a public DNS route; safely rolled back backend proxy origin to the working Quick Tunnel and re-verified live health/search/lawyer-research endpoints (`backend proxy version 6e68a3cc-216f-4f86-83aa-2dd7a4de592d`).
  - Added frontend proxy mitigation for transitional backend-origin gap: upstream `404` on `/api/research/lawyer-cases` now maps to structured `503 SOURCE_UNAVAILABLE`, with regression test coverage and frontend redeploy to Cloudflare (frontend version `30029410-c9b3-41d9-b452-e4dc67f9b596`).
  - Recovered a temporary Cloudflare Quick Tunnel outage (`530 origin unregistered`) caused by process reaping after a non-interactive shell launch: restarted persistent `uvicorn` + `cloudflared`, redeployed backend proxy to a new Quick Tunnel origin, and re-verified live Cloudflare endpoints (`backend proxy version 227b8729-e83e-4276-976e-6a7d09954566`; backend `/healthz` 200 with `x-immcad-edge-proxy`, frontend `/api/search/cases` 200, frontend `/api/research/lawyer-cases` 200 on both custom domain and `workers.dev`).
  - Hardened the Quick Tunnel bridge automation script to survive non-interactive shells by adding `--detach-mode auto|setsid|nohup` (`auto` selects `setsid` when available) and validated persistence with a throwaway bridge on port `8011` (`uvicorn` + `cloudflared` PIDs remained alive after script exit; local `/healthz` 200 from a fresh shell).
  - Promoted the active backend bridge from temporary TTY-held processes to the script-managed detached launcher flow on port `8002` (`/tmp/immcad-cloudflare-bridge-managed/state.env`), redeployed backend proxy to the new Quick Tunnel origin (`e64e1742-f1d4-4d73-a37a-6237b7e0b060`), re-verified Cloudflare `healthz` and case search, then retired the old TTY sessions so runtime is no longer tied to the interactive agent session.
  - Added a one-command named-tunnel cutover automation script (`scripts/finalize_cloudflare_named_tunnel_cutover.sh`) plus `make backend-cf-named-tunnel-doctor` / `make backend-cf-named-tunnel-cutover`; script reuses Wrangler OAuth for tunnel config updates, starts the named connector in detached mode, attempts DNS route creation via API token if present, falls back to `cloudflared tunnel route dns` (one-click `cloudflared tunnel login` if `cert.pem` is missing), redeploys backend proxy, runs live smokes, and auto-rolls back to the Quick Tunnel on cutover failure.
  - Verified current blocker state via the new doctor/non-interactive flow: Wrangler OAuth can update `cfd_tunnel` config but cannot read/create zone DNS records (`code 10000 Authentication error`), and `~/.cloudflared/cert.pem` is currently missing, so the next successful path requires a one-time interactive `cloudflared tunnel login` browser approval.
  - Completed the named-tunnel production cutover after one-click `cloudflared tunnel login`: `cloudflared tunnel route dns` created the route for `immcad-origin-tunnel.arkiteto.dpdns.org`, the cutover script redeployed the backend proxy to the named hostname (`cad122bd-f3e4-4361-aa16-ff59a69c2cc7`), and live Cloudflare endpoint checks passed (`/healthz`, frontend `/api/search/cases`, frontend `/api/research/lawyer-cases`).
  - Fixed a false-negative cutover failure caused by local DNS resolver lag (public Cloudflare DNS had propagated, local resolver had not) by adding a public-DNS + `curl --resolve` reachability fallback in the named-tunnel cutover script, then reran the same one-command cutover successfully.

---

# Task Plan - 2026-02-25 - Production Readiness Fix Pass (Post-Review)

## Current Focus
- Close P1/P2 production blockers found in strict code review for lawyer case research and case export.

## Plan
- [x] Add regression tests for long lawyer-research summaries, docket-style query validation, and unknown-source status classification.
- [x] Prevent internal `CaseSearchRequest` overflow by normalizing/planning query lengths before orchestration calls.
- [x] Harden export download redirect handling to enforce trusted-host checks before fetching redirected payloads.
- [x] Offload blocking case-search/research/export work from async routes to threadpool to reduce event-loop blocking risk.
- [x] Re-run targeted backend/frontend suites and update review evidence with explicit production readiness verdict.

## Review
- Fixed blocking long-query failure in lawyer research orchestration:
  - Added query normalization/truncation before internal `CaseSearchRequest` creation.
  - Added regression test proving long summaries no longer cause 500s and internal query lengths are bounded.
- Extended case-query specificity logic for docket-style identifiers:
  - Added acceptance for patterns like `A-1234-23` and `T-123-24`.
  - Added unit + API-route regression coverage for docket validation behavior.
- Corrected source-status classification:
  - Unknown/missing source IDs no longer count as official-source success.
  - Added regression test for unknown-source classification.
- Hardened export redirect flow:
  - Download now follows redirects manually and blocks untrusted redirect targets before payload retrieval.
  - Added regression test for redirect-host blocking policy (`export_redirect_url_not_allowed_for_source`).
- Reduced async route blocking risk:
  - Moved case search, lawyer research orchestration, and export download work to threadpool execution paths.
- Verification evidence:
  - Backend targeted tests: `56 passed`.
  - Export policy/security regression tests: `16 passed`.
  - Frontend contract tests: `32 passed`.
  - Full frontend suite: `63 passed`.
  - Full backend quality gate: `make quality` passed (`440 passed`, lint/mypy/docs/policy/sync checks green).
  - Source mirror parity: `make backend-vercel-sync-validate` passed.

---

# Task Plan - 2026-02-25 - Lawyer Case Research Production Path

## Current Focus
- Ship a production-safe lawyer case-research flow with grounded retrieval, explicit PDF/export status, and frontend integration that does not depend on chat-only scaffolding.

## Plan
- [x] Task 1: Define lawyer research API contract (backend schema + frontend client types + contract tests).
- [x] Task 2: Build matter extractor + multi-query planner.
- [x] Task 3: Implement lawyer case research orchestration service with deterministic merge/ranking and deduplication.
- [x] Task 4: Add document/PDF availability resolver and integrate into service responses.
- [x] Task 5: Add `/api/research/lawyer-cases` backend route (enabled + disabled modes).
- [x] Task 6: Integrate frontend related-case workflow with lawyer research endpoint and richer case cards.
- [x] Task 7: Add lawyer-research observability fields + docs contract updates.
- [x] Task 8: Final release-readiness closure (known issues, quality/release gates evidence).

## Review
- Added resolver-backed support metadata for each recommended case:
  - explicit `pdf_status`, `pdf_reason`,
  - `source_id`, `export_allowed`, `export_policy_reason`,
  - grounded `relevance_reason`.
- Added backend route and disabled-mode behavior:
  - `POST /api/research/lawyer-cases` now available when case search is enabled,
  - returns structured `SOURCE_UNAVAILABLE` envelope when case search is disabled.
- Frontend now uses lawyer-research endpoint for related-case retrieval:
  - proxy route added at `frontend-web/app/api/research/lawyer-cases/route.ts`,
  - support context now records `/api/research/lawyer-cases`,
  - related case cards now show relevance rationale and explicit PDF availability badges.
- Proxy safety maintained:
  - scaffold fallback remains chat-only,
  - lawyer-research proxy failures map to `SOURCE_UNAVAILABLE`.
- Verification evidence:
  - Backend targeted tests: `12 passed`.
  - Frontend targeted tests: `37 passed`.
  - `frontend-web` typecheck/lint: pass.
  - backend/deploy mirror sync check: pass.
  - full quality gate: `make quality` -> pass (`414 passed`, docs/architecture/source-registry/sync/hygiene checks green).

---

# Task Plan - 2026-02-25 - Cloudflare Migration (Vercel Exit Path)

## Current Focus
- Execute a production-safe Cloudflare migration plan with frontend-first rollout and explicit backend architecture gate.

## Plan
- [ ] Phase 0 decision gate: confirm Workers paid-tier production target and environment mapping (`dev/staging/prod`).
- [x] Phase 1 frontend migration: move `frontend-web` to Cloudflare Workers via OpenNext adapter and validate runtime parity.
- [x] Phase 2 backend architecture spike: run POC for Cloudflare Containers vs Python Worker FastAPI path and choose one using measured criteria.
  - [x] Transitional edge step implemented: Cloudflare backend proxy scaffold + workflow (`backend-cloudflare/*`, `.github/workflows/cloudflare-backend-proxy-deploy.yml`).
  - [x] Native backend runtime decision recorded: proceed with Python Workers path for next implementation phase (Containers remain optional fallback path).
- [ ] Phase 3 backend implementation: ship chosen backend path with secrets/auth/policy parity and canary rollout.
- [ ] Phase 4 CI/CD migration: add Cloudflare deploy workflows with deterministic pre-deploy quality gates and rollback command.
  - [x] Frontend workflow added (`.github/workflows/cloudflare-frontend-deploy.yml`) with typecheck/test/build-before-deploy gate.
  - [x] Backend transitional proxy workflow added (`.github/workflows/cloudflare-backend-proxy-deploy.yml`) for edge ingress migration.
  - [ ] Backend native-runtime deploy workflow pending Python Workers implementation + canary.
- [ ] Phase 5 production cutover: staged DNS/traffic migration with 24h and 72h observation windows and rollback criteria.
  - [x] Initial Cloudflare DNS/traffic cutover executed (workers.dev + custom domains reachable).
  - [ ] Observation windows and formal rollback attestation pending.
- [x] Evidence and signoff: release artifacts and known-issues register updated with current deployment evidence and remaining blockers.

## Task Plan - 2026-02-25 - Cloudflare Migration Audit

### Current Focus
- Evaluate release documentation, Cloudflare deploy configs/workflows (frontend + backend proxy), and list concrete gaps blocking production cutover.

### Plan
- [x] Audit `docs/release/known-issues.md` to confirm existing Cloudflare migration entries describe up-to-date blockers and note any missing evidence.
- [x] Review frontend and backend Cloudflare deploy configs/workflows for completeness (wrangler, OpenNext, GitHub Actions) and record missing steps or unpinned/pending parts.
- [x] Compile a concise list of actionable gaps (documentation, config, automation) that must be fixed before Cloudflare migration is production-ready.

## Review
- Phase 1 frontend migration executed for `frontend-web`:
  - Added Cloudflare OpenNext tooling: `@opennextjs/cloudflare@1.14.2` (pinned for Next.js `14.2.26` compatibility) and `wrangler`.
  - Added Cloudflare config artifacts: `frontend-web/open-next.config.ts`, `frontend-web/wrangler.jsonc`, `frontend-web/.dev.vars.example`.
  - Added Cloudflare scripts to `frontend-web/package.json`: `cf:build`, `cf:preview`, `cf:deploy`, `cf:upload`.
  - Updated `frontend-web/next.config.mjs` with `initOpenNextCloudflareForDev()` for local runtime parity.
  - Updated `frontend-web/.gitignore` for Cloudflare build/runtime artifacts (`.open-next/`, `.wrangler/`, `.dev.vars*`).
  - Updated `frontend-web/README.md` with Cloudflare local preview/deploy flow.
- Verification evidence:
  - `npm run typecheck` -> pass.
  - `npm run test` -> pass (`61 passed`).
  - `npm run build` -> pass.
  - `npm run cf:build` -> pass (OpenNext bundle generated at `.open-next/worker.js`).
  - `timeout 40s npm run cf:preview` -> reached Wrangler ready state (`Ready on http://localhost:8787`) before timeout stop.
  - `uv run pytest -q tests/test_cloudflare_backend_proxy_deploy_workflow.py tests/test_cloudflare_backend_migration_artifacts.py tests/test_cloudflare_frontend_deploy_workflow.py tests/test_workflow_action_pinning.py tests/test_quality_gates_workflow.py tests/test_release_gates_workflow.py` -> pass (`30 passed`).
  - `npx --yes wrangler@4.68.1 deploy --config backend-cloudflare/wrangler.backend-proxy.jsonc --dry-run` -> pass (Worker bundles and bindings resolve).
  - `docker build -f backend-cloudflare/Dockerfile -t immcad-backend-spike:local .` -> pass.
- CI/CD migration progress:
  - Added Cloudflare frontend deploy workflow with pinned actions + explicit secret checks.
  - Added Cloudflare backend proxy deploy workflow with pinned actions + explicit secret checks.
  - Added Makefile Cloudflare frontend targets (`frontend-cf-build`, `frontend-cf-preview`, `frontend-cf-deploy`).
  - Added Makefile backend Cloudflare targets (`backend-cf-spike-build`, `backend-cf-proxy-deploy`).
  - Updated env/docs to reflect Cloudflare-first frontend deploy path.
  - Added backend Cloudflare migration scaffold (`backend-cloudflare/`) and contract tests.
- Additional stability fix discovered during verification:
  - Resolved existing lint-blocking JSX quote escaping in `frontend-web/components/chat/related-case-panel.tsx`.
- Phase 2 backend spike + compatibility hardening executed:
  - Python Workers local spikes showed `healthz` recovery when handlers are async and surfaced strict client-ID failure in middleware.
  - Implemented worker-safe backend updates in both runtime paths:
    - Cloudflare-aware client ID resolution (`cf-connecting-ip` / `true-client-ip`) with host-header fallback when `request.client` is unavailable.
    - Converted API route handlers + health/ops endpoints to `async def` to avoid sync-handler runtime failures under worker shims.
    - Set Redis behavior to explicit opt-in (`REDIS_URL` required); default is now in-memory limiter.
  - Verification evidence:
    - `uv run pytest -q tests/test_settings.py tests/test_api_scaffold.py tests/test_rate_limiters.py` -> pass (`130 passed`).
    - `uv run ruff check ...` (changed backend/runtime files + tests) -> pass.
    - `make backend-vercel-sync-validate` -> pass.
- Continuation alignment pass completed:
  - Added deterministic release preflight guard (`scripts/release_preflight.sh`) and Make target (`make release-preflight`) to enforce clean-worktree + hygiene + Wrangler auth before deploy execution.
  - Rewrote `docs/release/pre-deploy-command-sheet-2026-02-25.md` to Cloudflare-first deploy/smoke/rollback commands.
  - Refreshed `docs/release/lead-engineering-readiness-audit-2026-02-25.md` with current Cloudflare deployment evidence and updated residual risk verdict.
  - Updated migration/status docs and onboarding/secret workflows to remove Vercel-first ambiguity:
    - `docs/plans/2026-02-25-cloudflare-migration-plan.md`
    - `docs/plans/2026-02-25-production-finalization-go-live-plan.md` (historical banner)
    - `docs/plans/2026-02-25-pre-deploy-deep-audit-plan.md` (historical banner)
    - `docs/plans/2026-02-25-deep-production-readiness-audit-plan.md` (historical banner)
    - `docs/release/git-secret-runbook.md`
    - `docs/development-environment.md`
    - `docs/onboarding/developer-onboarding-guide.md`
  - Updated known-issues status:
    - Closed process-control/doc-drift gaps via `KI-2026-02-25-C19` and `KI-2026-02-25-C20`.
    - Added DNS propagation operational watch item `KI-2026-02-25-08`.
- Native runtime execution pass completed:
  - Added Cloudflare native backend scaffold for Python Workers:
    - `backend-cloudflare/src/entry.py`
    - `backend-cloudflare/wrangler.toml`
    - `backend-cloudflare/pyproject.toml`
  - Added dedicated native deploy workflow:
    - `.github/workflows/cloudflare-backend-native-deploy.yml`
    - workflow contract tests in `tests/test_cloudflare_backend_native_deploy_workflow.py`
  - Extended migration artifact tests to cover native runtime scaffold.
  - Added authenticated backend performance smoke harness + Make target:
    - `scripts/run_cloudflare_backend_perf_smoke.sh`
    - `make backend-cf-perf-smoke`
  - Updated Cloudflare docs/runbooks to include native runtime and perf canary steps.
  - Updated known-issues register with:
    - `KI-2026-02-25-C21` (native runtime scaffold),
    - `KI-2026-02-25-C22` (perf smoke harness),
    - and retained `KI-2026-02-25-07` as open pending production-grade load evidence.
  - Verification evidence:
    - `cd backend-cloudflare && uv sync --dev` -> pass.
    - `cd backend-cloudflare && uv run pywrangler sync` -> pass.
    - `./scripts/venv_exec.sh pytest -q tests/test_cloudflare_backend_native_deploy_workflow.py tests/test_cloudflare_backend_migration_artifacts.py tests/test_workflow_action_pinning.py` -> pass (`12 passed`).
    - `./scripts/venv_exec.sh ruff check backend-cloudflare/src/entry.py tests/test_cloudflare_backend_native_deploy_workflow.py tests/test_cloudflare_backend_migration_artifacts.py` -> pass.
    - Native deploy attempt 1 (`cd backend-cloudflare && uv run pywrangler deploy`) -> failed with `ModuleNotFoundError: immcad_api` (resolved by adding `scripts/sync_backend_cloudflare_native_source.sh` + workflow sync step).
    - Native deploy attempt 2 (after sync) -> failed with Cloudflare API `code: 10027` bundle-size limit (`immcad-backend-native-python`), recorded as `KI-2026-02-25-09`.

## References
- Detailed plan: `docs/plans/2026-02-25-cloudflare-migration-plan.md`

---

# Task Plan - 2026-02-25 - Production Readiness Closure (Case Law)

## Current Focus
- Close remaining production blockers for case-law research reliability, security posture, and release evidence.

## Plan
- [ ] P0 deploy evidence: run source-based backend/frontend production deploy when Vercel quota resets; capture deployment IDs + timestamps in `docs/release/known-issues.md`.
- [x] P1 retrieval precision: block stopword-only queries from returning latest unrelated decisions and enforce minimum semantic query quality server-side.
- [x] P1 CanLII relevance fallback: remove broad unranked return path (`return cases`) when token matching fails; return empty or source-unavailable with reason.
- [x] P1 export approval hardening: require signed approval tokens for export in all environments (remove non-hardened compatibility bypass).
- [x] P2 UX/API contract alignment: enforce `maxLength=300` on case query input and replace policy-refusal copy that incorrectly implies case search is unavailable globally.
- [x] P1 frontend fallback control: require explicit env opt-in for chat scaffold proxy fallback in non-hardened environments (`IMMCAD_ALLOW_PROXY_SCAFFOLD_FALLBACK=true`).
- [x] P1 provider response guardrails: strengthen Gemini/OpenAI prompt instructions to prevent model/vendor identity drift and include grounded citation context in generation prompts.
- [x] Verification gate: re-run backend/ frontend tests + smoke checks and update issue statuses to closed/open with explicit evidence.

## Review
- Implemented case-search query specificity validation with structured `VALIDATION_ERROR` (`policy_reason=case_search_query_too_broad`) for broad/noise requests.
- Removed CanLII unranked no-match fallback path and added regression tests for short/no-match and long/no-match queries.
- Enforced signed export approval tokens in all environments and reordered export checks so policy/host failures still return precise reasons without reaching download logic.
- Set hardened defaults/guards for `CASE_SEARCH_OFFICIAL_ONLY_RESULTS` and updated settings + docs/tests accordingly.
- Updated frontend case-search UX constraints (`maxLength=300`) and policy-refusal messaging clarity.
- Disabled implicit frontend chat scaffold fallback by default; fallback now requires explicit server opt-in (`IMMCAD_ALLOW_PROXY_SCAFFOLD_FALLBACK=true`) and remains disabled in hardened environments.
- Improved case-search validation UX so broad-query policy failures return actionable guidance instead of generic temporary-unavailable copy.
- Hardened provider prompts to enforce IMMCAD identity/scope rules and include grounded citation context for both Gemini and OpenAI generation calls.
- Improved case-research workflow UX in the right panel: explicit 3-step flow, Enter-to-search support, stale-result query-change guidance, and visible "results for query" context to reduce confusion between chat and case-search services.
- Updated known-issues register with newly closed items; only deployment quota evidence remains as the P0 blocker.
- Re-attempted source-based production deploys (`backend-vercel`, `frontend-web`) at `2026-02-25 20:57 UTC`; both remained blocked by Vercel quota (`api-deployments-free-per-day`, retry window ~14 minutes).

---

# Task Plan - 2026-02-25 - Case Law Search Reliability Fix

## Current Focus
- Stabilize case-law research UX and retrieval relevance so case search behaves as an independent service and avoids misleading synthetic/noise results.

## Plan
- [x] Remove synthetic scaffold fallback for `/api/search/cases` and `/api/export/cases*` proxy failures.
- [x] Add independent editable case-search query input in UI (prefilled from last successful chat question).
- [x] Tighten backend ranking to avoid false positives for short/noise queries (e.g., `oi`).
- [x] Add regression tests for proxy fallback semantics, editable case query flow, and ranking noise filtering.
- [x] Validate frontend contracts/build + targeted backend case-search suites + source sync parity.

## Review
- Frontend proxy now only scaffold-falls back for chat; case-search/export failures return structured `SOURCE_UNAVAILABLE` with trace IDs (`frontend-web/lib/backend-proxy.ts`).
- Related case panel now exposes explicit `Case search query` input and search runs against that value, not an implicit hidden chat-only state (`frontend-web/components/chat/related-case-panel.tsx`, `frontend-web/components/chat/chat-shell-container.tsx`).
- Backend ranking updated to suppress irrelevant short/noise-query matches while preserving normal broad-query behavior:
  - `src/immcad_api/sources/official_case_law_client.py`
  - `src/immcad_api/sources/canlii_client.py`
  - mirrored in `backend-vercel/src/immcad_api/sources/*`.
- Added regression coverage:
  - `frontend-web/tests/backend-proxy.contract.test.ts`
  - `frontend-web/tests/chat-shell.contract.test.tsx`
  - `tests/test_official_case_law_client.py`
  - `tests/test_canlii_client.py`
- Verification evidence:
  - `npm run test --prefix frontend-web` -> pass (`59 passed`)
  - `npm run build --prefix frontend-web` -> pass
  - `npm run typecheck --prefix frontend-web` -> pass
  - `uv run pytest -q tests/test_canlii_client.py tests/test_official_case_law_client.py tests/test_case_search_service.py` -> pass (`26 passed`)
  - `uv run pytest -q tests/test_api_scaffold.py -k 'case_search or canlii'` -> pass (`13 passed, 19 deselected`)
  - `make backend-vercel-sync-validate` -> pass
  - live smoke: `/api/search/cases` now returns `{"results":[]}` for `query="oi"` and real official results for targeted immigration queries.

---

# Task Plan - 2026-02-25 - Frontend E2E Setup (Playwright)

## Current Focus
- Establish a production-oriented browser E2E suite for `frontend-web` with deterministic local and CI execution.

## Plan
- [x] Choose and configure the E2E framework with environment-aware defaults.
- [x] Add Page Object + fixture structure for maintainable test authoring.
- [x] Implement baseline user-journey specs (chat send + related case search) with network stubbing.
- [x] Add cross-browser/mobile project matrix and CI workflow integration.
- [x] Document local usage/debug flow and capture verification evidence.

## Review
- Added Playwright framework in `frontend-web`:
  - `frontend-web/playwright.config.ts` with environment-aware web server boot, project matrix, retries/reporting, and artifact output.
  - New scripts in `frontend-web/package.json` (`test:e2e*`) plus root Makefile wrappers (`frontend-e2e*`).
- Added maintainable E2E structure:
  - Fixtures: `frontend-web/e2e/fixtures/chat-data.ts`, `frontend-web/e2e/fixtures/test-fixtures.ts`.
  - Page object: `frontend-web/e2e/pages/chat-shell.page.ts`.
  - Network stubs: `frontend-web/e2e/support/network-stubs.ts`.
  - Specs:
    - `frontend-web/e2e/specs/chat-flow.spec.ts`
    - `frontend-web/e2e/specs/chat-policy-refusal.spec.ts`
    - `frontend-web/e2e/specs/chat-export.spec.ts`
    - `frontend-web/e2e/specs/chat-accessibility-visual.spec.ts`
  - Docs: `frontend-web/e2e/README.md` + `frontend-web/README.md` script/usage updates.
- CI integration:
  - Added `.github/workflows/frontend-e2e.yml` with pinned actions and matrix execution for `chromium`, `firefox`, and `webkit`.
  - Uploads Playwright HTML/JUnit/test-result artifacts per browser job.
- Headless-server hardening:
  - Local default Playwright projects now run `chromium`, `firefox`, and `Mobile Chrome` only.
  - `webkit` / `Mobile Safari` are explicit opt-in scripts for environments with required system libraries.
  - Browser install scripts split into default (`chromium+firefox`) and explicit WebKit install commands.
- Verification evidence:
  - `npm run typecheck` (`frontend-web`) -> pass.
  - `npm run lint` (`frontend-web`) -> pass.

# Task Plan - 2026-02-25 - Documentation Cloudflare Migration Sync

## Current Focus
- Align release/plan/readme artifacts so they describe the Cloudflare-first rollout instead of the legacy Vercel-first flow.

## Plan
- [ ] Inventory `docs/release`, `docs/plans`, `README.md`, `backend-cloudflare/README.md`, and `frontend-web/README.md` for Vercel-first instructions.
- [ ] For each file, capture sections that now need Cloudflare-first language and note what should replace them.
- [ ] Prioritize doc edits (by user impact/clarity) and provide concrete recommendations per file.

# Task Plan - 2026-02-25 - Documentation Cloudflare Migration Sync

## Current Focus
- Align release/plan/readme artifacts so they describe the Cloudflare-first rollout instead of the legacy Vercel-first flow.

## Plan
- [ ] Inventory `docs/release`, `docs/plans`, `README.md`, `backend-cloudflare/README.md`, and `frontend-web/README.md` for Vercel-first instructions.
- [ ] For each file, capture sections that now need Cloudflare-first language and note what should replace them.
- [ ] Prioritize doc edits (by user impact/clarity) and provide concrete recommendations per file.
  - `npm run test` (`frontend-web`) -> pass (`59 tests`).
  - `npm run test:e2e` (`frontend-web`) -> pass (`18 passed`, `0 skipped`).
  - `npm run test:e2e:cross-browser` (`frontend-web`) -> pass (`chromium+firefox`, `6 tests`).
  - `npm run test:e2e:mobile` (`frontend-web`) -> pass (`Mobile Chrome`, `3 tests`).
  - `npx playwright test` (`frontend-web`) -> pass (`chromium+firefox+Mobile Chrome` with visual/a11y/export coverage).
  - `npx playwright test e2e/specs/chat-accessibility-visual.spec.ts --project=chromium --update-snapshots` -> pass; baseline snapshot generated.
  - `npx playwright test --project=webkit` (`frontend-web`) -> fails locally due missing Linux WebKit shared libs in this workstation (expected on this host).
  - `uv run pytest -q tests/test_workflow_action_pinning.py tests/test_quality_gates_workflow.py tests/test_release_gates_workflow.py` -> pass (`18 tests`).

---

# Task Plan - 2026-02-25 - Readiness Hardening Continuation (Code-Only)

## Current Focus
- Execute remaining production-readiness code improvements that are deploy-independent, with verification evidence.

## Plan
- [x] Close CI determinism risk by enforcing frontend workflow order (`build -> typecheck -> test`) in release-critical workflows.
- [x] Add workflow regression tests that assert frontend step order in both quality and release gates.
- [x] Expand `mypy` quality gate scope from two files to production-critical backend/runtime modules + core tests.
- [x] Fix blocking type issues surfaced by expanded `mypy` scope.
- [x] Run targeted verification for changed files and then re-run `make quality`.
- [x] Update readiness artifacts (`docs/release/known-issues.md`, `tasks/todo.md`) with closed/open status and evidence.

## Review
- `./scripts/venv_exec.sh mypy` -> pass (`17 source files`), expanded from prior 2-file scope.
- Typing defects fixed to enable expanded gate:
  - `src/immcad_api/services/chat_service.py` (`raw_url` typed as `object | None` in citation extraction),
  - `src/immcad_api/policy/compliance.py` (removed incompatible variable re-assignment in grounded citation verification).
- Backend mirror parity preserved after runtime typing fixes:
  - `make backend-vercel-sync-validate` -> pass.
- Workflow determinism evidence:
  - frontend order remains `build -> typecheck -> test` and backend `mypy` now runs in both `.github/workflows/quality-gates.yml` and `.github/workflows/release-gates.yml`,
  - `./scripts/venv_exec.sh pytest -q tests/test_quality_gates_workflow.py tests/test_release_gates_workflow.py` -> `17 passed`.
- Runtime safety regression checks:
  - `./scripts/venv_exec.sh pytest -q tests/test_chat_service.py tests/test_export_policy_gate.py tests/test_settings.py tests/test_api_scaffold.py` -> `145 passed`.
- Full quality gate:
  - `make quality` -> pass (`374 passed`, mypy gate green, source sync green, policy/hygiene/eval checks green).
- Issue tracker updates:
  - Closed typing/quality issue as `KI-2026-02-25-C07`.
  - Remaining blockers are operational or policy scope decisions (`KI-2026-02-25-01`, `KI-2026-02-25-03`, `KI-2026-02-25-04`, `KI-2026-02-25-05`).

---

# Task Plan - 2026-02-25 - Deep Production Readiness Audit (Pre-Deploy)

## Current Focus
- Perform a deep pre-deploy audit so the next backend/frontend deployment can run end-to-end without new blockers.

## Plan
- [x] Phase 0: Baseline snapshot (repo state, PR state, active deployments, known blockers).
- [x] Phase 1: Backend deep audit (API contracts, auth/hardening, export policy, source controls).
- [x] Phase 2: Frontend deep audit (proxy contracts, chat/case/export UX, runtime config/fallbacks).
- [x] Phase 3: Security and compliance audit (secrets/artifacts hygiene, Canada-only policy checks).
- [x] Phase 4: CI/CD and deploy process audit (quality gates, deploy config, deterministic redeploy checklist).
- [x] Phase 5: Operations and recovery audit (metrics/alerts, incident/rollback runbooks, smoke readiness).
- [x] Consolidate findings with severity (`P0-P3`), owner, and target date in `docs/release/known-issues.md`.
- [x] Produce final go/no-go readiness summary + command sheet for the next deploy window.

## References
- Detailed audit execution plan: `docs/plans/2026-02-25-pre-deploy-deep-audit-plan.md`
- Supporting summary plan: `docs/plans/2026-02-25-deep-production-readiness-audit-plan.md`
- Existing go-live plan baseline: `docs/plans/2026-02-25-production-finalization-go-live-plan.md`
- Current known issues register: `docs/release/known-issues.md`

## Review
- Baseline snapshot executed (`2026-02-25 19:08:56 UTC`) on `main` (`0c35b05`); no open PRs and latest merged PR is `#33`.
- Production alias snapshot confirmed:
  - Backend alias -> READY `dpl_7q6JDuNMy8wefcBVxns76VV4hbho` (latest backend attempt still ERROR `dpl_G7S9EGK8p2DgXv7jscjqYvynwFxc`).
  - Frontend alias -> READY `dpl_9YbaotuCWvMXptmWS3x4TPo6tTn8`.
- Full verification matrix executed:
  - `make quality` -> pass (`370 passed` + architecture/docs validators + source registry + backend mirror sync + legal suite + hygiene).
  - `make source-registry-validate` -> pass.
  - `uv run pytest -q tests/test_api_scaffold.py tests/test_export_policy_gate.py tests/test_source_policy.py tests/test_settings.py tests/test_case_search_service.py tests/test_official_case_law_client.py` -> pass (`162 passed`).
  - `npm run build --prefix frontend-web` -> pass.
  - `npm run typecheck --prefix frontend-web` -> pass (after Next type generation); `npm run test --prefix frontend-web` -> pass (`50 passed`).
  - `uv run python scripts/scan_domain_leaks.py` -> pass.
  - `bash scripts/check_repository_hygiene.sh` -> pass.
  - workflow/ops gate tests: `uv run pytest -q tests/test_quality_gates_workflow.py tests/test_release_gates_workflow.py tests/test_ops_alerts_workflow.py tests/test_backend_vercel_deploy_config.py tests/test_staging_smoke_workflow.py tests/test_ops_alert_evaluator.py` -> pass.
- Critical blocker found and fixed during audit:
  - `scripts/validate_backend_vercel_source_sync.py` initially failed due mirror drift (`api/routes/cases.py`, `main.py`, `schemas.py`).
  - Executed repo-prescribed mirror sync (`rsync ... src/immcad_api/ -> backend-vercel/src/immcad_api/`), then `make backend-vercel-sync-validate` passed.
- Production smoke validation executed on active backend alias:
  - `/healthz` -> `200` (`{\"status\":\"ok\",\"service\":\"IMMCAD API\"}`).
  - `/ops/metrics` and `/api/chat` without token -> `401 UNAUTHORIZED` (expected for protected config).
- Deliverables produced:
  - Deep audit plans: `docs/plans/2026-02-25-pre-deploy-deep-audit-plan.md`, `docs/plans/2026-02-25-deep-production-readiness-audit-plan.md`.
  - Command sheet: `docs/release/pre-deploy-command-sheet-2026-02-25.md`.
  - Updated issue tracker: `docs/release/known-issues.md`.
- Continuation verification (`2026-02-25 19:14:57 UTC`):
  - Baseline re-check confirmed `main` at `0c35b05`, still no open PRs, latest merged PR remains `#33`.
  - Deployment aliases remain READY (`backend`: `dpl_7q6JDuNMy8wefcBVxns76VV4hbho`, `frontend`: `dpl_9YbaotuCWvMXptmWS3x4TPo6tTn8`).
  - `make backend-vercel-sync-validate` and `make quality` re-ran successfully (`370 passed`).
  - Unauthenticated direct `curl` smoke checks are now blocked by Vercel Authentication for this environment; authenticated smoke must use protection bypass flow in the next deploy window.
- Final continuation pass (`2026-02-25 19:27:37 UTC`):
  - Source-based deploy retries were attempted for both backend and frontend:
    - `vercel --cwd backend-vercel deploy --prod --yes` -> blocked by `api-deployments-free-per-day`.
    - `vercel --cwd frontend-web deploy --prod --yes` -> blocked by `api-deployments-free-per-day`.
  - CI determinism hardening completed:
    - workflow order updated to `build -> typecheck -> test` in both quality and release gates.
    - workflow contract tests now pass with order assertions (`20 passed`).
  - Deploy-window execution evidence captured: `artifacts/release/deploy-window-execution-2026-02-25.md`.

---

# Task Plan - 2026-02-25 - Production Finalization Audit + Deploy Recovery

## Current Focus
- Finalize production readiness for IMMCAD frontend + backend with verified deploy-safe configuration, Canada-domain migration guardrails, and explicit post-deploy validation steps.

## Plan
- [x] Review lessons, current plan backlog, and repo state before touching deploy/runtime config.
- [x] Audit latest frontend/backend production deployments and identify current backend deploy failure root cause.
- [x] Verify user-facing readiness (case search, related-case review flow, export-policy gates, AI API routes).
- [x] Verify local quality gates (`make lint`, `make test`, `make verify`, `make quality`) and frontend build/test/typecheck.
- [x] Identify India->Canada migration residue and determine whether it is runtime-impacting.
- [x] Harden backend Vercel deploy config:
- [x] Pin a supported Vercel Python runtime via `backend-vercel/.python-version` (not `vercel.json` runtime override).
- [x] Add `.vercelignore` protections to block local `.env*` and stale `.vercel/output` artifacts from deploy context.
- [x] Add repository hygiene guard to fail when a backend prebuilt artifact references local `.env` files.
- [x] Add/extend tests for backend deploy hardening and hygiene checks.
- [x] Expand default domain-leak scanning to include `config/`.
- [x] Replace stale India-domain content in unused compatibility file `config/prompts.yaml` with Canada-safe prompts.
- [x] Re-run targeted verification for changed files + impacted scripts/tests.
- [x] Re-run full production verification batch (backend + frontend + policy/conformance checks).
- [ ] Redeploy backend from source (not stale `--prebuilt`) and verify Vercel build succeeds with supported Python runtime.
- [ ] Redeploy frontend (if desired for same release SHA) and record deployment IDs/timestamps.
- [x] Run production smoke checks on active deployment endpoints (`/healthz`, `/ops/metrics`, frontend UI) and capture evidence.
- [x] Decide whether to widen `mypy` gate scope now or explicitly defer with a documented production rationale.

## Review
- Lead-engineering audit + decision log captured in:
  - `docs/release/lead-engineering-readiness-audit-2026-02-25.md`
  - `docs/release/known-issues.md`
- Deployment audit (2026-02-25 UTC):
  - Frontend latest production deployment: READY (`dpl_9YbaotuCWvMXptmWS3x4TPo6tTn8`) at `2026-02-25 01:29:16 UTC`.
  - Backend latest production deployment: ERROR (`dpl_G7S9EGK8p2DgXv7jscjqYvynwFxc`) at `2026-02-25 01:32:31 UTC`.
  - Vercel build logs reported invalid serverless runtime `index (python3.11)`.
  - Local prebuilt manifest `backend-vercel/.vercel/output/functions/index.func/.vc-config.json` confirmed `"runtime": "python3.11"` and `.env.production.*` file references in `filePathMap`.
  - Latest READY backend production deployment remains `dpl_7q6JDuNMy8wefcBVxns76VV4hbho` at `2026-02-25 00:41:36 UTC`.
  - Source-based backend redeploy attempt (`vercel --cwd backend-vercel deploy --prod --yes`) was blocked by Vercel quota: `api-deployments-free-per-day`.
- User-facing capability audit:
  - Frontend supports chat + "Find related cases" review flow via `frontend-web/components/chat/chat-shell-container.tsx` and related-case panel components.
  - Backend exposes `/api/chat`, `/api/search/cases`, `/api/export/cases`, `/ops/metrics`, `/healthz`.
  - Export/download path enforces user approval + source-policy/trusted-domain checks.
- Local verification (pre-change audit batch):
  - `make lint` -> pass
  - `make test` -> pass (`355 passed`)
  - `make verify` -> pass (warnings only; optional tools/env absent)
  - `make quality` -> pass
  - `npm run typecheck --prefix frontend-web` -> pass
  - `npm run test --prefix frontend-web` -> pass
  - `npm run build --prefix frontend-web` -> pass
  - `scripts/validate_source_registry.py` -> pass
  - `scripts/scan_domain_leaks.py` -> pass (before `config/` was included in defaults)
  - `scripts/check_repository_hygiene.sh` -> pass
  - `scripts/run_case_law_conformance.py --strict` -> pass (`fail=0`, warning-only output)
- Local verification (post-change re-run, 2026-02-25):
  - `make quality` -> pass (`363 passed`)
  - `make verify` -> pass (warnings only: missing `.env`, `redis-cli`, optional `git-secret`)
  - `npm run typecheck --prefix frontend-web` -> pass
  - `npm run test --prefix frontend-web` -> pass (`50 passed`)
  - `npm run build --prefix frontend-web` -> pass
  - `pytest -q tests/test_backend_vercel_deploy_config.py tests/test_repository_hygiene_script.py tests/test_domain_leak_scanner.py tests/test_export_policy_gate.py` -> pass (`31 passed`)
  - `bash -n scripts/check_repository_hygiene.sh` -> pass
  - `ruff check scripts/scan_domain_leaks.py tests/test_backend_vercel_deploy_config.py tests/test_repository_hygiene_script.py tests/test_domain_leak_scanner.py` -> pass
- Migration residue audit:
  - `config/prompts.yaml` has been rewritten to Canada-safe compatibility text.
  - Active runtime prompts are Canada-safe in `src/immcad_api/policy/prompts.py` and mirrored backend path.
  - Runtime scan excluding evaluation modules found no India-domain term leaks in `src/immcad_api` and `backend-vercel/src/immcad_api`.
  - Residual India-domain terms remain in tests/evaluation guardrails, migration docs, and historical notebook artifacts only.
- PR / release state:
  - Open PRs currently: none (`gh pr list --state open` returned no rows).
  - Latest merged PR is `#33` (`MERGED`, created `2026-02-25T14:31:11Z`) and it is now on `main`.
- Production smoke checks (active deployments):
  - `GET https://backend-vercel-eight-sigma.vercel.app/healthz` -> `200`.
  - `GET https://backend-vercel-eight-sigma.vercel.app/ops/metrics` -> `401` (expected: bearer token required).
  - `GET https://frontend-web-plum-five.vercel.app/` -> `200` (scope notice and chat shell render).
  - Direct backend `/api/chat` and `/api/search/cases` without token -> `401` (expected in protected production config).
- Decision log (go/no-go):
  - Adopted Vercel-documented Python pinning via `backend-vercel/.python-version` (`3.12`), not `functions.runtime` override for official Python runtime.
  - Initial decision deferred full-repo `mypy src tests` expansion due unrelated backlog; later continuation pass expanded the scoped release gate from 2 to 17 production-critical files (see top 2026-02-25 continuation section).
  - Deployment completion is currently blocked by Vercel free-plan daily deployment quota, not by failing quality gates.
- Deployment state snapshot (2026-02-25 UTC):
  - Backend active alias resolves to READY deployment `dpl_7q6JDuNMy8wefcBVxns76VV4hbho` (`2026-02-25 00:41:36 UTC`).
  - Latest backend deployment attempt remains ERROR `dpl_G7S9EGK8p2DgXv7jscjqYvynwFxc` (`2026-02-25 01:32:31 UTC`).
  - Frontend active alias resolves to READY deployment `dpl_9YbaotuCWvMXptmWS3x4TPo6tTn8` (`2026-02-25 01:29:16 UTC`).
  - Backend + frontend redeploy attempts during this run were blocked by quota (`api-deployments-free-per-day`).
- Backend + frontend redeploy checklist (next operator steps after config/test re-verification):
  - Backend:
    - Ensure latest Vercel CLI and linked `backend-vercel` project.
    - Prefer source-based deploy (avoid stale `--prebuilt` output).
    - Confirm no local `.env.production.*` files are in deploy context (guard + `.vercelignore` now enforce this).
    - Record deployment ID, status, and timestamp.
  - Frontend:
    - Deploy `frontend-web` for same release SHA if required.
    - Record deployment ID, status, and timestamp.
  - Smoke:
    - Validate `/healthz`, `/api/chat`, `/api/search/cases`, `/ops/metrics`.
    - Validate frontend related-case flow and export confirmation behavior against production backend.

---

# Task Plan - 2026-02-24 - Senior Lead MVP Next Steps

## Current Focus
- Drive a controlled MVP closure sequence for production-safe legal research delivery (source correctness, policy enforcement, CI reliability, and runtime safety).

## Plan
- [x] Phase 0 (24h): Complete release safety preconditions.
- [x] Confirm `.env-backups/` is ignored and no backup artifacts are tracked (`git ls-files '.env-backups/**'`).
- [x] Finalize workflow dedup/concurrency and artifact semantics in `quality-gates.yml` and `release-gates.yml`.
- [x] Run: `scripts/venv_exec.sh pytest -q tests/test_quality_gates_workflow.py tests/test_release_gates_workflow.py tests/test_ops_alerts_workflow.py`.
- [x] Phase 1 (48h): Close in-flight parser and ingestion-policy work.
- [x] Finish SCC/FC/FCA parser hardening in `src/immcad_api/sources/canada_courts.py` and registry wording consistency.
- [x] Validate ingestion policy behavior with: `scripts/venv_exec.sh pytest -q tests/test_canada_courts.py tests/test_ingestion_jobs.py tests/test_canada_registry.py tests/test_validate_source_registry.py`.
- [x] Phase 2 (72h): Lock runtime/API safety.
- [x] Close remaining auth/prompt/citation/export gate checks (`main.py`, `settings.py`, `app.py`, `policy/prompts.py`, `policy/source_policy.py`).
- [x] Run: `scripts/venv_exec.sh pytest -q tests/test_api_scaffold.py tests/test_chat_service.py tests/test_source_policy.py tests/test_export_policy_gate.py`.
- [x] Phase 3 (96h): Tooling/docs alignment and final gate.
- [ ] Complete Makefile hermeticity + docs-maintenance script fixes and test hardening backlog.
- [ ] Run final gate: `scripts/venv_exec.sh mypy src tests`, `scripts/venv_exec.sh ruff check src/immcad_api scripts tests`, targeted pytest matrix, and `scripts/venv_exec.sh python scripts/validate_source_registry.py`.
- [ ] Delivery control:
- [ ] Ship as one PR per phase; do not mix workflow/security with parser/runtime changes.
- [ ] Update this section and associated plan sections with concrete evidence before marking done.

## Review
- Phase 0 evidence:
  - `git ls-files '.env-backups/**'` returned no tracked backup files.
  - `scripts/venv_exec.sh pytest -q tests/test_quality_gates_workflow.py tests/test_release_gates_workflow.py tests/test_ops_alerts_workflow.py` -> `13 passed`.
- Phase 1 evidence:
  - Hardened FCA parsing fallback for HTML listings and parse-error fallback in `src/immcad_api/sources/canada_courts.py`.
  - `scripts/venv_exec.sh pytest -q tests/test_canada_courts.py tests/test_ingestion_jobs.py tests/test_canada_registry.py tests/test_validate_source_registry.py` -> `25 passed`.
- Phase 2 evidence:
  - Updated hardened-mode API tests for full env contract and runtime source-unavailable simulation in `tests/test_api_scaffold.py`.
  - `scripts/venv_exec.sh pytest -q tests/test_api_scaffold.py tests/test_chat_service.py tests/test_source_policy.py tests/test_export_policy_gate.py` -> `50 passed`.
- Phase 3 evidence:
  - Fixed lint blocker in `scripts/generate_ingestion_plan.py`.
  - Final verification batch:
    - `scripts/venv_exec.sh ruff check src/immcad_api scripts tests` -> pass.
    - targeted pytest verification matrix -> `72 passed`.
    - `scripts/venv_exec.sh python scripts/validate_source_registry.py` -> pass.
    - `scripts/venv_exec.sh python scripts/run_ingestion_smoke.py ...` -> pass.
    - `scripts/venv_exec.sh python scripts/run_case_law_conformance.py --strict ...` -> pass (`fail=0`).
- Type-check tool gap:
  - `scripts/venv_exec.sh mypy src tests` failed because `mypy` is not installed in this environment.
  - `scripts/venv_exec.sh pyright --version` also not available.
- Continuation update (research/remediation alignment):
  - Implemented source-level fetch policy support:
    - added canonical config file `config/fetch_policy.yaml`,
    - added loader module `src/immcad_api/ingestion/source_fetch_policy.py` with shared `CONFIG_FETCH_POLICY_PATH`,
    - wired retry budget + per-source timeout behavior into `src/immcad_api/ingestion/jobs.py`,
    - added CLI support via `--fetch-policy` in `scripts/run_ingestion_jobs.py`.
  - Added ingestion retry-budget regression tests in `tests/test_ingestion_jobs.py` (success-after-retry and exhausted-retry paths).
  - Aligned research docs to current policy decisions:
    - updated provider wording in `docs/research/canada-legal-ai-source-and-ingestion-guide.md` to separate `vLex (vLex Canada)` and `Lexum / CanLII commercial API`,
    - updated Phase 1 citation threshold language in `docs/research/canada-legal-ai-production-implementation-plan.md` (`>= 90%` onboarding, `>= 99%` steady-state target).
  - Verification:
    - `scripts/venv_exec.sh ruff check src/immcad_api/ingestion/source_fetch_policy.py src/immcad_api/ingestion/jobs.py scripts/run_ingestion_jobs.py tests/test_ingestion_jobs.py` -> pass.
    - `scripts/venv_exec.sh pytest -q tests/test_ingestion_jobs.py tests/test_canada_courts.py tests/test_source_policy.py tests/test_case_law_conformance_script.py tests/test_release_gates_workflow.py tests/test_quality_gates_workflow.py` -> `44 passed`.
    - `scripts/venv_exec.sh python scripts/run_ingestion_jobs.py --cadence daily --output /tmp/ingestion-daily.json --state-path /tmp/ingestion-daily-state.json` -> pass.
- Additional hardening pass:
  - Updated rate-limiter logger to module-scoped naming in `src/immcad_api/middleware/rate_limit.py` and made logger-capture test robust in `tests/test_rate_limiters.py`.
  - Added explicit loader type guard before `exec_module` in `tests/test_prompt_compatibility.py`.
  - Verification:
    - `scripts/venv_exec.sh pytest -q tests/test_rate_limiters.py tests/test_prompt_compatibility.py tests/test_legacy_runtime_convergence.py tests/test_doc_maintenance.py tests/test_ingestion_smoke_script.py` -> `24 passed`.
    - `scripts/venv_exec.sh ruff check src/immcad_api/middleware/rate_limit.py tests/test_rate_limiters.py tests/test_prompt_compatibility.py` -> pass.
- Fetch-policy coverage expansion:
  - Added dedicated fetch-policy unit tests in `tests/test_source_fetch_policy.py` (explicit missing-path behavior, default-file loading, source override parsing, invalid schema guard).
  - Verification:
    - `scripts/venv_exec.sh pytest -q tests/test_source_fetch_policy.py tests/test_ingestion_jobs.py` -> `14 passed`.
    - `scripts/venv_exec.sh ruff check src/immcad_api/ingestion/source_fetch_policy.py tests/test_source_fetch_policy.py` -> pass.

---

# Task Plan - 2026-02-24 - Canada Legal Research Agent Source Guide

## Current Focus
- Build comprehensive, evidence-backed documentation for Canadian case-law acquisition and ingestion under CanLII API constraints.

## Plan
- [x] Create missing task tracking files (`tasks/todo.md`, `tasks/lessons.md`).
- [x] Compile source feasibility matrix (CanLII, SCC, FC, FCA, IRB, Open Government, commercial providers).
- [x] Author comprehensive guide in `docs/research/` with best-practice architecture, compliance controls, and phased rollout.
- [x] Add validation summary and open questions for procurement/legal review.
- [x] Add review section documenting outcomes and next actions.

## Review
- Created `docs/research/canada-legal-ai-source-and-ingestion-guide.md` with:
  - source-by-source technical feasibility and rights considerations
  - ingestion architecture and phased rollout plan
  - PDF/website ingestion best practices
  - 2026 agent best-practice synthesis (OpenAI/Anthropic/Gemini)
  - validated endpoint/reference appendix
- Added missing findings after deep endpoint review:
  - A2AJ and Refugee Law Lab accelerator options (with explicit licensing caveats)
  - SCC/FC/FCA rights-reference links
  - crawler reliability caveats (feed-window limits, year validation, CanLII anti-crawl posture)
- Created `docs/research/README.md` index.
- Created `tasks/lessons.md` baseline for future correction-driven updates.

---

# Task Plan - 2026-02-24 - Production Implementation Plan (Doc Update)

## Current Focus
- Review latest documentation additions and convert requirements into an execution-ready production plan.

## Plan
- [x] Validate whether existing guide covers the five required rollout tracks.
- [x] Add explicit A2AJ/Refugee Law Lab policy decision to the source guide.
- [x] Create a dedicated production implementation plan document with workstreams, gates, timeline, and go/no-go criteria.
- [x] Update research documentation index to include the production plan.

## Review
- Confirmed existing guide already covered most requested tracks (rights matrix, connectors, conformance tests, pilot metrics, procurement), with one major gap:
  - A2AJ and Refugee Law Lab usage was conditional but not explicitly classified as internal-only vs production.
- Updated `docs/research/canada-legal-ai-source-and-ingestion-guide.md` with explicit decision:
  - A2AJ: internal-only allowed; production blocked pending legal sign-off.
  - Refugee Law Lab: internal-only allowed; production blocked pending legal sign-off.
- Added `docs/research/canada-legal-ai-production-implementation-plan.md` including:
  - 5 execution workstreams mapped to requested priorities
  - rights/policy gate implementation details
  - SCC/FC/FCA safeguard requirements
  - conformance and pilot evaluation gates
  - parallel commercial diligence workflow
  - timeline, ownership model, and readiness checklist.

---

# Task Plan - 2026-02-24 - Production Readiness Prioritization

## Current Focus
- Produce a step-by-step production-readiness implementation sequence with explicit top priorities, based on parallel codebase analysis and Context7-aligned agent best practices.

## Plan
- [x] Run parallel repository analysis for connectors, policy/tests, and ops readiness.
- [x] Validate plan against Context7 guidance for production agent controls.
- [x] Update production plan doc with ranked priorities, critical path, and parallel execution lanes.
- [x] Add a concrete first 10 business day rollout checklist.

## Review
- Parallel analysis confirmed:
  - ingestion/checkpoint scaffolding exists but SCC/FC/FCA connectors and safeguards are incomplete,
  - policy/refusal and citation checks exist at chat runtime but source rights matrix + source policy gates are missing at ingestion/export boundaries,
  - CI/runbooks are strong but operational metrics and alert escalation for rollout SLOs need completion.
- Updated `docs/research/canada-legal-ai-production-implementation-plan.md` with:
  - ranked `P0/P1/P2` priorities,
  - Context7-aligned reliability controls,
  - critical path and parallel lane execution model,
  - first 10 business days step-by-step implementation checklist.

---

# Task Plan - 2026-02-24 - Execute P0 Day 1-2

## Current Focus
- Implement production policy-gate foundations (source policy config + runtime enforcement + tests).

## Plan
- [x] Add machine-readable source policy config (`config/source_policy.yaml`).
- [x] Add source rights matrix document (`docs/release/source-rights-matrix.md`).
- [x] Implement source policy loader and decision helpers in backend policy module.
- [x] Wire ingestion runtime to enforce source policy by environment.
- [x] Add tests for source policy behavior and ingestion policy blocking.
- [x] Update ingestion CLI docs/flags to support policy path + environment.
- [x] Run lint and targeted tests.

## Review
- Implemented policy module:
  - `src/immcad_api/policy/source_policy.py`
  - added exports in `src/immcad_api/policy/__init__.py`.
- Enforced ingestion policy gates in `src/immcad_api/ingestion/jobs.py`:
  - blocks production-ingest disallowed sources,
  - blocks unknown sources in production,
  - records `blocked_policy` status and `policy_reason`,
  - reports `blocked` count.
- Updated ingestion CLI and smoke behavior:
  - `scripts/run_ingestion_jobs.py` now supports `--source-policy` and `--environment`.
  - `scripts/run_ingestion_smoke.py` now validates zero policy blocks in smoke runs.
- Added/updated tests:
  - `tests/test_source_policy.py`
  - `tests/test_ingestion_jobs.py` (policy block/allow coverage).
- Validation:
  - `scripts/venv_exec.sh ruff check ...` passed.
  - `scripts/venv_exec.sh pytest -q tests/test_source_policy.py tests/test_ingestion_jobs.py tests/test_ingestion_smoke_script.py` passed (`18 passed`).

---

# Task Plan - 2026-02-24 - Execute P0 Day 3 (Connector Safeguards Foundation)

## Current Focus
- Implement SCC/FC/FCA source parsing and ingestion-time safeguard validation with regression tests.

## Plan
- [x] Add court connector parsing/validation module for SCC/FC/FCA payloads.
- [x] Integrate court payload validation into ingestion success criteria.
- [x] Add SCC/FC/FCA sources to required registry IDs and canonical source registry.
- [x] Update jurisdiction domain allowlist for new official court domains.
- [x] Add parser and ingestion integration tests for valid/invalid payloads.
- [x] Run lint + targeted tests + registry validation.

## Review
- Added `src/immcad_api/sources/canada_courts.py`:
  - parse SCC JSON feed and Decisia RSS feeds (FC/FCA),
  - extract case IDs/citations/PDF URL patterns,
  - validate court-specific citation format and metadata shape,
  - return structured validation summary.
- Updated `src/immcad_api/ingestion/jobs.py` to enforce connector safeguards:
  - recognized court sources now require parseable records,
  - ingestion fails when invalid records are detected,
  - ingestion report now captures parsed/valid/invalid record counts.
- Updated registry and required-source baseline:
  - added `SCC_DECISIONS`, `FC_DECISIONS`, `FCA_DECISIONS` to
    `data/sources/canada-immigration/registry.json`,
  - added these source IDs to `src/immcad_api/sources/required_sources.py`.
- Updated jurisdiction domain allowlist:
  - `src/immcad_api/evaluation/jurisdiction.py` now includes Decisia court domains.
- Added tests:
  - `tests/test_canada_courts.py`,
  - extended `tests/test_ingestion_jobs.py` with SCC valid/invalid payload cases.
- Validation:
  - `scripts/venv_exec.sh ruff check ...` passed.
  - `scripts/venv_exec.sh pytest -q tests/test_canada_registry.py tests/test_validate_source_registry.py tests/test_source_policy.py tests/test_canada_courts.py tests/test_ingestion_jobs.py tests/test_ingestion_smoke_script.py tests/test_jurisdiction_suite.py` passed (`34 passed`).
  - `scripts/venv_exec.sh python scripts/validate_source_registry.py` passed (`20` required sources present).

---
# Task Plan - 2026-02-24 - Production Readiness Risk Assessment

## Current Focus
- Surface the highest-risk production issues across legacy modules, quality gates, migrations, and security/runtime config.

## Plan
- [ ] Inventory legacy/archived module references and gauge their influence on production code paths.
- [ ] Audit lint/test/morph tooling to find gaps in quality gates or missing enforcement on critical flows.
- [ ] Review framework migrations, runtime config, and security-sensitive setups for incomplete transitions or risky defaults.
- [ ] Compile prioritized findings with severity, explicit file references, and evidence-ready notes.

## Review
- [pending]

---

# Task Plan - 2026-02-24 - Review Findings Closure (Patch Self-Containment + Ops Auth)

## Current Focus
- Resolve reviewer-reported patch completeness issues and `/ops` auth regression with minimal scoped changes.

## Plan
- [x] Verify reviewer findings against current workspace state (`policy`/`sources` imports and `/ops` middleware auth condition).
- [x] Patch `/ops` auth gating so bearer auth is enforced only when `API_BEARER_TOKEN` is configured.
- [x] Add a regression test proving `/ops/metrics` remains accessible when bearer auth is unset.
- [x] Ensure new modules referenced by package imports are included in the patch (`policy/prompts.py`, `policy/source_policy.py`, `sources/canada_courts.py`).
- [x] Run targeted verification (import smoke + focused pytest).

## Review
- Fixed `/ops` auth regression in `src/immcad_api/main.py` by enforcing bearer auth only when `API_BEARER_TOKEN` is configured.
- Added regression test `test_ops_metrics_does_not_require_auth_when_bearer_token_unset` in `tests/test_api_scaffold.py`.
- Added the reviewer-flagged new modules to version control so the package imports are self-contained in the patch:
  - `src/immcad_api/policy/prompts.py`
  - `src/immcad_api/policy/source_policy.py`
  - `src/immcad_api/sources/canada_courts.py`
- Validation:
  - `PYTHONPATH=src uv run python -c "import immcad_api.policy, immcad_api.sources; print('import-smoke-ok')"` ✅
  - `PYTHONPATH=src uv run pytest -q tests/test_api_scaffold.py -k 'ops_metrics'` ✅ (`3 passed, 18 deselected`)

---

# Task Plan - 2026-02-24 - Comprehensive Findings Closure (Second-Pass Gap Coverage)

## Current Focus
- Close all reported findings with explicit file-level coverage, deduplicate repeated comments, and enforce per-track validation gates.

## Gap Review (Misses in Prior Plan)
- [x] Prior plan did not explicitly map all documentation/research/plans findings to concrete files.
- [x] Prior plan did not explicitly include legacy runtime code hardening in `legacy/local_rag/lawglance_main.py` and `legacy_api_client.py`.
- [x] Prior plan did not explicitly call out `ops/alert_evaluator.py` correctness fixes and related workflow/test anchoring changes.
- [x] Prior plan did not explicitly enumerate all required targeted test assertions/timeouts/path-hardening tasks.
- [x] Prior plan did not explicitly include `scripts/scan_domain_leaks.py` fallback behavior and `scripts/vercel_env_sync.py` newline handling fix.
- [x] Prior plan did not explicitly include `docs/release/source-rights-matrix.md` + `config/source_policy.yaml` consistency fixes for citation policy flags.
- [x] Prior plan did not explicitly include AGENTS/task-structure cleanup requirements (`tasks/` entry, nested list formatting, duplicate task block removal).

## Coverage Matrix (All Findings Grouped)

### Track A — Secrets/Backup Hygiene + Env Template Safety (`P0`)
- [x] Add `.env-backups/` ignore rule in repository root `.gitignore`.
- [x] Verify `git ls-files '.env-backups/**'` is empty; if not, untrack backups from index.
- [ ] Keep backups out of version control and move any retained examples to stable non-backup paths (`docs/` or `backend-vercel/.env.example` / `frontend-web/.env.example`).
- [x] Update env examples for safe defaults and required placeholders:
  - `backend-vercel/.env.example` (`ENVIRONMENT`, `CITATION_TRUSTED_DOMAINS`, provider key guidance).
  - backup-derived examples only if intentionally retained as non-secret templates.
- [ ] Document manual external actions required before merge when secrets were exposed:
  - rotate/revoke API/OIDC/provider tokens,
  - history purge with `git filter-repo`/BFG if sensitive values were pushed.

### Track B — CI Workflow Correctness + Dedup/Concurrency (`P0`)
- [x] `.github/workflows/quality-gates.yml`:
  - decide docs maintenance mode (`--dry-run` with optional upload or non-dry run with guaranteed artifact),
  - set `PYTHONPATH: src` if script imports from `src`,
  - make upload semantics explicit (`if-no-files-found: ignore` or remove upload step).
- [x] `.github/workflows/release-gates.yml`:
  - resolve duplicate trigger strategy (`tags` vs `release/**`),
  - add workflow-level `concurrency` keyed by `${{ github.ref }}`.
- [x] Pin mutable action references where required (dependency-review action).
- [x] Update workflow tests accordingly:
  - `tests/test_quality_gates_workflow.py`,
  - `tests/test_release_gates_workflow.py`,
  - `tests/test_ops_alerts_workflow.py`.

### Track C — Runtime/API Hardening (`P0/P1`)
- [x] `src/immcad_api/main.py`: protect `/ops` endpoints regardless of `API_BEARER_TOKEN` nullability.
- [x] `src/immcad_api/settings.py`: hardened `CITATION_TRUSTED_DOMAINS` must reject comma-only/empty parsed values.
- [ ] `app.py`: sanitize markdown citation fields (`title`, `pin`) and validate/allowlist URL schemes.
- [x] `src/immcad_api/policy/prompts.py`: include user question placeholder in `QA_PROMPT`.
- [x] `src/immcad_api/policy/source_policy.py`: parse YAML/JSON based on file type (default path is `.yaml`).
- [ ] `legacy_api_client.py`: narrow transport exception handling and log failures.
- [ ] `legacy/local_rag/lawglance_main.py`: remove module-level `basicConfig`, use module logger, add cache TTL write.

### Track D — Ingestion/Source/Policy Correctness (`P1`)
- [ ] `src/immcad_api/sources/canada_courts.py`:
  - scalar text coercion in `_dict_text`,
  - dedupe recursion behavior in `_iter_json_item_dicts`,
  - catch parse/decode failures and convert to controlled validation outcome.
- [ ] `scripts/scan_domain_leaks.py`: ensure fallback to root legacy file set if `legacy/local_rag` structure is missing.
- [ ] `src/immcad_api/evaluation/jurisdiction.py`: remove incorrect `decisions.fca-caf.gc.ca` allow marker and clarify FCA hosting note.
- [ ] `data/sources/canada-immigration/registry.json`: normalize SCC/FCA instrument text wording.
- [ ] Align rights/citation policy docs and config:
  - `docs/release/source-rights-matrix.md`,
  - `config/source_policy.yaml` (CANLII_TERMS, A2AJ, REFUGEE_LAW_LAB citation flags).

### Track E — Ops Alert Evaluator + URL/Value Semantics (`P1`)
- [ ] `src/immcad_api/ops/alert_evaluator.py`:
  - base URL normalization ordering in `build_metrics_url`,
  - treat bool metric values as non-numeric,
  - correct healthy/breach message semantics.
- [ ] `scripts/vercel_env_sync.py`: tighten literal `\\n` trimming logic to avoid corrupting valid encoded values.
- [ ] Update related tests:
  - `tests/test_ops_alert_evaluator.py` (repo-root anchored config path),
  - `tests/test_ops_alerts_workflow.py` (path anchoring + cron assertion robustness).

### Track F — Makefile Hermeticity + Guardrails (`P1`)
- [ ] `Makefile`:
  - remove non-hermetic `ingestion-smoke` from mandatory `quality`,
  - add optional integration-quality target or flag-based inclusion,
  - add `TS` fail-fast guard for restore target usage,
  - pass `--environment $(ENV)` for `vercel-env-push-dry-run` if supported.
- [ ] `docs/development-environment.md`: replace hardcoded restore timestamp with placeholder.

### Track G — Doc-Maintenance Reliability (`P1/P2`)
- [ ] `scripts/check_repository_hygiene.sh`: explicit `git grep` exit-code branching (`0/1/other`).
- [ ] `scripts/doc_maintenance/audit.py`:
  - recursive glob semantics (`**`) correctness,
  - subprocess timeout behavior and non-blocking git metadata reads,
  - prose-only word count (frontmatter/code/inlines/URLs handling).
- [ ] `scripts/doc_maintenance/optimizer.py`:
  - TOC replacement normalization,
  - TOC detection via regex not plain substring,
  - prevent self-referential TOC generation.
- [ ] `scripts/doc_maintenance/styler.py`:
  - skip fenced code links/line-length checks,
  - safe parsing for optional/invalid `max_line_length`.
- [ ] `scripts/doc_maintenance/validator.py`:
  - guarded local-anchor file read with error reporting.

### Track H — Test Contract Hardening (`P1/P2`)
- [ ] `tests/test_api_scaffold.py`:
  - assert trace header in unsupported locale/mode validation path,
  - assert disclaimer on trusted-domain-constrained response path.
- [ ] `tests/test_chat_service.py`:
  - enforce non-PII audit helper on grounding failure event,
  - add disclaimer/fallback/prompt-leak checks for untrusted-domain rejection,
  - add answer/prompt-leak assertions for trusted-domain acceptance path.
- [ ] `tests/test_ingestion_jobs.py`: parametrize internal runtime behavior (`development` and `internal_runtime` or equivalent).
- [ ] `tests/test_rate_limiters.py`: capture correct logger namespace.
- [ ] `tests/test_canada_courts.py`: assert `court_code` is preserved.
- [ ] `tests/test_ingestion_smoke_script.py`: add subprocess timeout and safer payload key assertions including `second_run["succeeded"]`.
- [ ] `tests/test_prompt_compatibility.py`: robust spec/loader guards, `sys.modules` registration before `exec_module`.
- [ ] `tests/test_legacy_runtime_convergence.py`: avoid runtime module import side effects (`find_spec` + static symbol checks), tighten forbidden import matching.

### Track I — Documentation and Task-Plan Consistency (`P2`)
- [ ] `AGENTS.md`:
  - add `tasks/` entry under project structure,
  - fix numbered workflow list nested markdown indentation.
- [ ] `tasks/todo.md`:
  - [ ] add missing `## Review` stubs for Framework Usage Audit and Rights Matrix task blocks.
  - [x] remove duplicate Source Policy Handoff Audit block.
- [ ] `docs/architecture/09-documentation-automation.md`: clarify `docs-fix` only refreshes TOC and manual follow-up requirements.
- [ ] `docs/research/README.md`: convert machine-specific absolute links to relative links.
- [ ] `docs/research/canada-legal-ai-production-implementation-plan.md`:
  - heading-level hierarchy fixes,
  - terminology/provider naming fixes (`vLex` vs `Lexum/CanLII API`),
  - timeline consistency across sections,
  - abbreviation definition (`Refugee Law Lab (RLL)`),
  - remove Context7 misattribution in section title/wording,
  - explicit freshness threshold cross-reference where ambiguous.
- [ ] `docs/research/canada-legal-ai-source-and-ingestion-guide.md`:
  - ensure cross-document links resolve,
  - adjust Phase 1 citation threshold framing/path to 99%,
  - add explicit Refugee Law Lab search-indexing prohibition controls.
- [ ] `docs/plans/2026-02-24-canada-legal-readiness-remediation-plan.md`:
  - declare concrete test file paths for tasks,
  - canonical fetch-policy config path contract,
  - final verification gate includes type-check and added test files.

## Verification Gates (Execution Order)
- [x] Gate 1 (Tracks A-B): workflow + secret hygiene checks (`git ls-files`, workflow tests, targeted lint).
- [ ] Gate 2 (Tracks C-D-E): runtime/parser/policy tests (`test_api_scaffold`, `test_chat_service`, `test_canada_courts`, `test_ingestion_jobs`, `test_ops_alert_evaluator`).
- [ ] Gate 3 (Tracks F-G): tooling/doc-maint tests (`test_doc_maintenance`, script smoke checks, Makefile command sanity).
- [ ] Gate 4 (Tracks H-I): remaining targeted tests + docs/task consistency validations.
- [ ] Final gate: `ruff`, focused `pytest` matrix, registry validation, ingestion smoke, and any newly added conformance checks.

## Review
- Batch 1 completed (Tracks A/B + part of C):
  - Added root `.env-backups/` ignore and verified no tracked `.env-backups/**` files in current index.
  - Hardened `backend-vercel/.env.example` with safe `ENVIRONMENT=development`, explicit `CITATION_TRUSTED_DOMAINS`, and provider key guidance.
  - Fixed CI workflow correctness:
    - `quality-gates.yml` dependency-review action SHA pin + docs artifact upload `if-no-files-found: ignore`.
    - `release-gates.yml` removed duplicate `release/**` push trigger and added workflow-level concurrency on `${{ github.ref }}`.
  - Hardened runtime/config:
    - `/ops` endpoints now always require bearer auth.
    - hardened trusted-domain parsing rejects comma-only values.
    - `QA_PROMPT` now includes user question placeholder.
    - source policy loader supports YAML/JSON by extension.
  - Updated tests to match new contracts (workflow pin/concurrency checks, settings comma-only guard, API scaffold `/ops` auth baseline + missing assertions).
  - Verification:
    - `./scripts/venv_exec.sh pytest -q tests/test_quality_gates_workflow.py tests/test_release_gates_workflow.py tests/test_settings.py tests/test_source_policy.py tests/test_prompt_compatibility.py` -> `47 passed`
    - `./scripts/venv_exec.sh ruff check src/immcad_api/main.py src/immcad_api/settings.py src/immcad_api/policy/prompts.py src/immcad_api/policy/source_policy.py legacy/local_rag/prompts.py tests/test_quality_gates_workflow.py tests/test_release_gates_workflow.py tests/test_settings.py tests/test_api_scaffold.py` -> pass
    - `./scripts/venv_exec.sh pytest -q tests/test_api_scaffold.py` -> `20 passed`

---

# Task Plan - 2026-02-24 - Legacy Archive Importability Hardening

## Current Focus
- Execute architecture validation follow-through: keep legacy archive importable for notebook workflows without restoring root legacy shims.

## Plan
- [x] Confirm archive orchestrator uses package-relative imports.
- [x] Make `legacy/local_rag` an explicit Python package.
- [x] Remove eager heavy dependency imports from archived modules to avoid import-time crashes.
- [x] Add regression tests for package importability and relative-import contract.
- [x] Update legacy archive documentation with supported import path and dependency behavior.
- [x] Run focused tests and lint checks.

## Review
- Implemented archive hardening:
  - Added `legacy/local_rag/__init__.py`.
  - Kept `legacy.local_rag.lawglance_main` package-relative imports.
  - Updated archived `chains.py` and `cache.py` to lazy-load optional legacy dependencies with explicit runtime errors when missing.
  - Removed unused `langchain.schema` import from archived orchestrator to reduce import-time coupling.
- Added regression coverage in `tests/test_legacy_runtime_convergence.py`:
  - explicit package marker check,
  - package-path module import smoke check,
  - relative-import contract assertions.
- Updated `legacy/local_rag/README.md` with supported usage (`from legacy.local_rag.lawglance_main import Lawglance`) and dependency notes.
- Verification:
  - `./scripts/venv_exec.sh pytest -q tests/test_legacy_runtime_convergence.py` -> `8 passed`
  - `./scripts/venv_exec.sh ruff check legacy/local_rag/lawglance_main.py legacy/local_rag/chains.py legacy/local_rag/cache.py legacy/local_rag/__init__.py tests/test_legacy_runtime_convergence.py` -> pass

---

# Task Plan - 2026-02-24 - Legacy Archive + Citation Domain Allowlist Hardening

## Current Focus
- Execute remaining production-hardening tasks:
  - remove/archive remaining root-level legacy modules and clean final references
  - require explicit trusted citation domain allowlist configuration for hardened environments

## Plan
- [x] Confirm root legacy modules are archived under `legacy/local_rag/` and removed from repo root.
- [x] Remove remaining root-import references in non-archive artifacts.
- [x] Enforce explicit `CITATION_TRUSTED_DOMAINS` configuration in `production`/`prod`/`ci`.
- [x] Update CI safety-toggle checks and tests for explicit trusted-domain configuration.
- [x] Update runtime/docs guidance to reflect explicit hardened-environment requirement.
- [x] Run targeted tests for settings, API scaffold, legacy convergence, and workflow assertions.
- [x] Add review summary with verification evidence.

## Review
- Hardened `load_settings` now requires `CITATION_TRUSTED_DOMAINS` to be explicitly set in `production`/`prod`/`ci`, while keeping defaults for development.
- Updated CI hardened-mode validation steps in both quality/release workflows to provide explicit trusted domains.
- Updated tests:
  - `tests/test_settings.py` adds explicit-production-domain requirement coverage.
  - `tests/test_api_scaffold.py` hardened-mode tests now set trusted-domain env.
  - `tests/test_quality_gates_workflow.py` and `tests/test_release_gates_workflow.py` assert trusted-domain env presence.
- Removed remaining root-level legacy import reference from `test.ipynb`; remaining legacy imports now exist only in archived modules/tests.
- Added `tests/test_legacy_runtime_convergence.py::test_root_legacy_module_imports_are_absent_from_root_notebook` to prevent root-level legacy import regressions.
- Verification:
  - `./scripts/venv_exec.sh pytest -q tests/test_settings.py tests/test_api_scaffold.py tests/test_legacy_runtime_convergence.py tests/test_quality_gates_workflow.py tests/test_release_gates_workflow.py` -> `56 passed`
  - `./scripts/venv_exec.sh ruff check src/immcad_api/settings.py tests/test_settings.py tests/test_api_scaffold.py tests/test_legacy_runtime_convergence.py tests/test_quality_gates_workflow.py tests/test_release_gates_workflow.py` -> pass

---

# Task Plan - 2026-02-24 - Framework Usage Audit

## Current Focus
- Audit which runtime/framework stack IMMCAD is currently using and document migration status.

## Plan
- [ ] Inspect main entry points (`app.py`, `src/immcad_api`, `frontend-web/`, `legacy/`) for runtime/runtime commands.
- [ ] Identify active backend and frontend frameworks, noting configuration/spec files that mention them.
- [ ] List any legacy modules still referenced and gather file paths/evidence.
- [ ] Summarize findings, assessing migration completeness with citations to files.

## Review
- [pending]

---
# Task Plan - 2026-02-24 - Rights Matrix & Policy Gate Readiness

## Current Focus
- Evaluate repository readiness for enforcing rights matrix, internal/production policy gates, and conformance testing coverage across compliance-critical modules.

## Plan
- [ ] Catalog existing enforcement points (code/modules/tests) for rights and policy controls.
- [ ] Identify missing policy gates for internal-only vs production source policies and export controls.
- [ ] Map current conformance test coverage, noting specific tests that need to be added to cover uncovered policies or workflows.

## Review
- [pending]

---

# Task Plan - 2026-02-24 - Handoff Audit + Implementation Plan

## Current Focus
- Audit handoff claims against repository/tooling reality and produce a gated implementation plan for next execution phase.

## Plan
- [x] Run repository reality-check commands (`pwd`, `git status`, branch/log checks).
- [x] Verify handoff claims in referenced files/modules/tests.
- [x] Re-run handoff validation commands (ruff, pytest, registry validator, ingestion smoke).
- [x] Validate assumption-sensitive points with live endpoint probes and context references.
- [x] Publish remediation implementation plan in `docs/plans/2026-02-24-canada-legal-readiness-remediation-plan.md`.

## Review
- Repository checks completed on `main` with a dirty working tree (many modified/untracked files); no handoff claim was accepted without verification.
- Handoff validation commands reproduced successfully:
  - `ruff check` passed on targeted files.
  - Targeted test suite passed: `34 passed`.
  - `scripts/validate_source_registry.py` passed (`20` required sources, `22` policy entries).
  - `scripts/run_ingestion_smoke.py` passed.
- Live ingestion reality check surfaced material production risks:
  - `FCA_DECISIONS` configured URL currently returns `404`.
  - Live SCC/FC feeds include records failing strict citation checks; scheduled ingestion run failed 3/5 sources due validation/endpoint errors.
- Saved execution-ready remediation plan with CI gates and validation checkpoints at:
  - `docs/plans/2026-02-24-canada-legal-readiness-remediation-plan.md`.

---

# Task Plan - 2026-02-24 - Architecture Documentation Refresh

## Current Focus
- Regenerate and align architecture documentation with current runtime reality (FastAPI + Next.js + script-based ingestion + provider routing).

## Plan
- [x] Audit architecture docs against current code paths and workflows.
- [x] Update core architecture documents (`01`, `02`, `03`, `06`) to remove stale assumptions and match package topology.
- [x] Refresh architecture index/governance docs (`README`, `09`, `arc42-overview`, `ADR README`).
- [x] Update provider-fallback ADR to reflect current implementation.
- [x] Run architecture validation and targeted workflow tests.

## Review
- Updated architecture narratives to remove stale Grok references and outdated module map assumptions.
- Clarified ingestion execution as script-driven runtime flow rather than an already-separated worker container.
- Synchronized provider architecture documentation with current `ProviderRouter` behavior and non-prod scaffold fallback usage.
- Improved architecture docs governance and automation sections to reflect current CI workflows and local validation commands.
- Verification:
  - `./scripts/venv_exec.sh python scripts/generate_module_dependency_diagram.py` -> pass
  - `bash scripts/validate_architecture_docs.sh` -> pass
  - `./scripts/venv_exec.sh pytest -q tests/test_quality_gates_workflow.py tests/test_release_gates_workflow.py` -> `9 passed`

---
# Task Plan - 2026-02-24 - Production Readiness/Operations Assessment

## Current Focus
- Assess CI gates, pilot evaluation harness, operational monitoring, and rollback plans for a production rollout.

## Plan
- [ ] Inventory existing CI/test/verification gates (e.g., workflows, lint/test commands) with file references.
- [ ] Document any pilot evaluation or gating harnesses (test data, evaluation scripts, dashboards) tied to rollout readiness.
- [ ] Evaluate current metrics/SLO monitoring or alerting coverage (instrumentation, dashboards, configs) and note gaps.
- [ ] Review rollback and recovery procedures, including data/feature toggles and documented playbooks.
- [ ] Synthesize findings into readiness summary with prioritized implementation tasks and file refs.

## Review
- [pending]

---

# Task Plan - 2026-02-24 - Source Policy Handoff Audit

## Current Focus
- Verify repository reality matches claimed source-policy/court ingestion handoff deliverables.

## Plan
- [ ] Inspect files/code associated with the 11 handoff claims and note line references.
- [ ] Identify and document any mismatches between the claims and repository contents.
- [ ] Summarize audit findings with severity/confidence and cite evidence.

## Review
- [pending]

---

# Task Plan - 2026-02-24 - Source Registry Validation Tolerance

## Current Focus
- Review `/home/ec2-user/IMMCAD/.worktrees/court-validation-thresholds` to understand source registry validation logic around ratio thresholds and year ranges.

## Plan
- [ ] Inspect `scripts/validate_source_registry.py` and related validation code/tests in the court-validation-thresholds worktree to map current enforcement.
- [ ] Record exact paths/line references describing how invalid ratios and year windows are handled today.
- [ ] Identify minimal change points to allow small invalid ratios and a configurable/relaxed year window.

## Review
- [pending]

---

# Task Plan - 2026-02-24 - Backend Architecture Summary

## Current Focus
- Document the backend architecture of `src/immcad_api`, entrypoints, routing, service layers, policy/ingestion flows, storage, and observability connections for quick onboarding.

## Plan
- [ ] Inventory the main entrypoints and script runners (`app.py`, API routers, `scripts/`).
- [ ] Map routers, services, policy gates, ingestion workflow, storage dependencies, and observability hooks within `src/immcad_api`/`scripts/`, noting file references.
- [ ] Synthesize findings into a concise textual summary for the user and note any uncovered gaps in `tasks/lessons.md` if needed.

## Review
- [pending]

---

# Task Plan - 2026-02-24 - Next Steps Remediation Execution (Sequential Priorities)

## Current Focus
- Execute remaining verified findings in production-risk order, with explicit verify-before-fix checks and per-batch validation gates.

## Plan
- [ ] Phase 1 (P0): Secrets/backups hygiene and exposure containment.
- [ ] Add `.env-backups/` ignore coverage and stop tracking any backup snapshots currently in git index.
- [ ] Relocate/normalize tracked env examples into stable non-backup locations and update references.
- [ ] Document required manual actions: rotate exposed tokens/keys and perform history purge (`git filter-repo`/BFG) before merge if leaked values were pushed.
- [ ] Validate with: `git ls-files '.env-backups/**'` (expect none) and targeted grep/audit checks.
- [ ] Phase 2 (P0): Runtime auth/policy hardening.
- [ ] Fix `/ops` auth enforcement in `src/immcad_api/main.py` so ops endpoints are always protected.
- [ ] Harden `CITATION_TRUSTED_DOMAINS` parsing/validation in `src/immcad_api/settings.py` for comma-only/empty parsed values.
- [ ] Ensure `QA_PROMPT` includes user question placeholder aligned with chain input in `src/immcad_api/policy/prompts.py`.
- [ ] Align `source_policy` loader with YAML default path in `src/immcad_api/policy/source_policy.py`.
- [ ] Validate with targeted tests: `tests/test_api_scaffold.py`, `tests/test_settings.py`, `tests/test_chat_service.py`, `tests/test_source_policy.py`.
- [ ] Phase 3 (P0/P1): CI workflow correctness and deduplication.
- [ ] Update `.github/workflows/quality-gates.yml` docs-maintenance step/env/artifact behavior (`--dry-run` decision + `if-no-files-found` semantics).
- [ ] Add release workflow concurrency and trigger dedupe in `.github/workflows/release-gates.yml`.
- [ ] Pin mutable action refs where required and align workflow assertions in tests.
- [ ] Validate with targeted tests: `tests/test_quality_gates_workflow.py`, `tests/test_release_gates_workflow.py`, `tests/test_ops_alerts_workflow.py`.
- [ ] Phase 4 (P1): Parser/ingestion robustness and safety output.
- [ ] Harden `app.py` citation markdown rendering with escaping + URL scheme allowlist.
- [ ] Improve `src/immcad_api/sources/canada_courts.py` scalar handling, duplicate item recursion behavior, and parse-exception safety.
- [ ] Apply requested domain-marker correction in `src/immcad_api/evaluation/jurisdiction.py`.
- [ ] Validate with targeted tests: `tests/test_canada_courts.py`, `tests/test_ingestion_jobs.py`, `tests/test_chat_service.py`.
- [ ] Phase 5 (P1): Makefile hermeticity and guardrails.
- [ ] Remove non-hermetic dependency from `quality` target and add explicit integration-quality path.
- [ ] Add `TS` fail-fast guards and align `vercel-env-push-dry-run` environment flag behavior with script support.
- [ ] Validate with Makefile target smoke checks and docs updates where commands changed.
- [ ] Phase 6 (P1/P2): Doc-maintenance script resiliency.
- [ ] Fix `scripts/check_repository_hygiene.sh` git-grep exit-code branching.
- [ ] Harden `scripts/doc_maintenance/{audit.py,optimizer.py,styler.py,validator.py}` for timeout, glob semantics, TOC idempotence, and non-code false positives.
- [ ] Validate with `tests/test_doc_maintenance.py` and targeted script runs.
- [ ] Phase 7 (P2): Test hardening and stability improvements.
- [ ] Apply requested test assertions/timeouts/path anchoring across API/chat/ingestion/ops/prompt compatibility/rate limiter suites.
- [ ] Replace brittle import execution in legacy convergence checks with safe spec/static checks.
- [ ] Validate with consolidated targeted pytest batch covering touched test modules.
- [ ] Phase 8 (P2): Documentation/task consistency cleanup.
- [ ] Resolve AGENTS/task formatting and duplicate task-block issues in `AGENTS.md` and `tasks/todo.md`.
- [ ] Apply docs corrections for architecture/research/release/source-rights and registry wording consistency.
- [ ] Validate with markdown lint/doc maintenance audit and spot-check links.

## Review
- [pending]

# Task Plan - 2026-02-24 - Backend Diff Review

## Current Focus
- Audit backend changes under `src/immcad_api` against `35a79b9f1376f99f5a63918ed0d0809727d1f97a` to find correctness regressions.

## Plan
- [ ] Fetch diff for `src/immcad_api/settings.py`, `services/chat_service`, `ingestion/jobs`, `policy/compliance`, `middleware/rate_limit`, `api/routes/cases`, and `schemas` relative to base commit.
- [ ] Identify regressions by reasoning about new/changed logic (e.g., validation, gating, policy flows) with precise file/line refs.
- [ ] Confirm each regression is supported by code evidence; skip speculative issues.
- [ ] Summarize confirmed regressions in review response with references and reasoning.

## Review
- [pending]

---

# Task Plan - 2026-02-24 - Reconcile Dirty Tree to Main (Production Readiness)

## Current Focus
- Reconcile all uncommitted local work into a reviewed, test-validated commit stack and merge safely to `main` without data loss.

## Plan
- [x] Create redundant filesystem and git-diff safety snapshots before any reconciliation.
- [x] Audit local worktrees, local branches, remote branches, and divergence from `origin/main`.
- [x] Move dirty state off `main` into a dedicated reconciliation branch.
- [x] Group changes into reviewable commits by domain (runtime/policy, CI/ops, docs maintenance, legacy migration, architecture/research docs).
- [x] Run lint + targeted/full tests and capture evidence.
- [x] Perform self-review on each commit (diff sanity + regression scan).
- [x] Update local `main` to `origin/main`, merge reconciliation branch, and verify clean state.
- [x] Push branch and/or merged `main` to remote; report any push blockers.

## Review
- Created and validated a 7-commit stack on top of `origin/main` covering runtime policy gates, CI/ops hardening, docs tooling resilience, legacy runtime convergence, architecture/readiness docs, repo/env hygiene, and post-integration test deduplication.
- Validation evidence:
  - `PYTHONPATH=.:src uv run pytest -q` -> `202 passed`
  - `PYTHONPATH=.:src uv run ruff check <python files changed vs merge-base>` -> pass
  - `PYTHONPATH=.:src uv run python scripts/doc_maintenance/main.py --config scripts/doc_maintenance/config.yaml --dry-run` -> pass
- Merged into local `main` and pushed to `origin/main` (`5847ff1..4a7aedd`).
- Residual local-only artifacts intentionally retained: `.ai/` snapshot backups (untracked).

---

# Task Plan - 2026-02-24 - Archived Branch Extraction Backlog (Post-Reconcile)

## Current Focus
- Keep `main` stable while extracting any still-useful deltas from archived historical branches in small, reviewable slices.

## Plan
- [x] Preserve all non-main branch states as immutable remote archive refs (`archive/*`).
- [x] Verify all active worktrees are clean and no uncommitted changes remain.
- [x] Triage `archive/feature-source-registry-loader-20260224` against `main` and confirm whether core loader/validation assets are already present.
- [x] Triage `archive/feature-api-scaffold-20260224` commit-level deltas (`f66a290`, `ee7dd8b`, `e40b997`) with dry-run checks.
- [ ] Extract only high-value, low-risk deltas from `archive/feature-api-scaffold-20260224` into a new branch from `main` (no bulk merge).
- [ ] Defer `archive/ralph-canada-hardening-next-loop-20260224` and `archive/ralph-prod-readiness-canlii-legal-research-20260224` to selective cherry-pick only; no direct merge due to high drift risk.

## Review
- `main` is clean and synchronized with `origin/main`.
- Archive refs were created for all at-risk local/gone-upstream branches to prevent work loss.
- `feature/source-registry-loader` content is functionally superseded by current `main` (core loader/tests already present and evolved).
- `feature-api-scaffold` does not merge cleanly into current `main`; must be handled via selective extraction, not branch merge.

---

# Task Plan - 2026-02-25 - Case-Law Tooling Hardening + Runtime Alignment

## Current Focus
- Execute step-by-step production hardening for case-law chat retrieval: wire case-search tool orchestration, keep backend/backend-vercel parity, and close hardened-env policy mismatches with verification.

## Plan
- [x] Wire `ChatService` to `CaseSearchService` in `src/immcad_api/main.py` after case-search initialization.
- [x] Mirror chat-service wiring and implementation parity in `backend-vercel/src/immcad_api/main.py` and `backend-vercel/src/immcad_api/services/chat_service.py`.
- [x] Add/extend backend tests for chat tool invocation, skip logic, and tool-error auditing.
- [x] Add integration proof that `/api/chat` now uses case-search citations for case-law prompts.
- [x] Expand default trusted citation domains to include official court domains used by official feeds, including backend-vercel mirror.
- [x] Run focused verification on touched backend and frontend runtime-hardening tests.

## Review
- Completed wiring so chat orchestration now passes `case_search_service` into `ChatService` (`src` + `backend-vercel`).
- Added deterministic tests for:
  - tool usage on case-law prompts,
  - non-case prompt bypass,
  - tool error audit events,
  - chat API integration path (case-search citation appears in `/api/chat` response).
- Added official court hosts to default trusted citation domains:
  - `decisions.scc-csc.ca`
  - `decisions.fct-cf.gc.ca`
  - `decisions.fca-caf.gc.ca`
- Added signed export-approval handshake:
  - new backend endpoint `/api/export/cases/approval` issues short-lived signed tokens,
  - hardened environments now require a valid signed approval token for `/api/export/cases`,
  - frontend now requests approval token after explicit confirmation and sends it with export.
- Verification evidence:
  - `uv run ruff check src/immcad_api/main.py src/immcad_api/services/chat_service.py src/immcad_api/policy/compliance.py tests/test_chat_service.py tests/test_api_scaffold.py tests/test_settings.py` -> pass
  - `PYTHONPATH=.:src uv run pytest -q tests/test_chat_service.py tests/test_api_scaffold.py tests/test_settings.py` -> `129 passed`
  - `npm run test -- tests/server-runtime-config.contract.test.ts tests/backend-proxy.contract.test.ts` (in `frontend-web/`) -> `19 passed`
  - `PYTHONPATH=.:src uv run pytest -q tests/test_export_policy_gate.py tests/test_api_scaffold.py` -> `46 passed`
  - `npm run test -- tests/chat-shell.contract.test.tsx tests/api-client.contract.test.ts tests/export-cases-route.contract.test.ts` (in `frontend-web/`) -> `18 passed`
  - `make quality` -> pass (`370 passed`)
  - `npm run test` (in `frontend-web/`) -> pass (`52 passed`)
  - `npm run typecheck` (in `frontend-web/`) -> pass

---

# Task Plan - 2026-02-25 - API Contract Hardening (Case Search + Cloudflare Edge)

## Current Focus
- Close production blockers in case-search error handling and edge-proxy error-contract compatibility while preserving backend/backend-vercel parity.

## Plan
- [x] Reproduce and confirm `/api/search/cases` unhandled `ApiError` path and add structured error handling in route layer.
- [x] Remove duplicated URL allowlist logic in case-export route by reusing shared document-resolver helpers.
- [x] Replace hardcoded official-source classification in lawyer research with registry-aware classification (with fallback behavior).
- [x] Align Cloudflare edge-proxy error response envelope and trace headers with frontend API client contract.
- [x] Add regression tests for: case-search rate-limit envelope, registry-aware official classification, frontend legacy/edge trace parsing, and edge artifact contract assertions.
- [x] Run focused and full verification gates (`ruff`, targeted pytest/vitest, `make quality`, frontend full test + typecheck).

## Review
- Fixed API route robustness:
  - `/api/search/cases` now catches `ApiError` and returns structured envelopes instead of raw 500s.
  - case-export route now uses shared host-allowlist helpers from `case_document_resolver` to avoid policy drift.
- Fixed classification robustness:
  - lawyer research source-status classification now checks `source_registry` (case_law entries) when available, with deterministic fallback for legacy/offline contexts.
- Fixed Cloudflare migration contract gap:
  - Worker error responses now emit nested `{ error: { code, message, trace_id, policy_reason } }` and include `x-trace-id` (while retaining `x-immcad-trace-id`).
  - Frontend API client now accepts either `x-trace-id` or `x-immcad-trace-id` and can parse legacy flat proxy error envelopes during rollout.
- Verification evidence:
  - `uv run ruff check src/immcad_api/api/routes/cases.py src/immcad_api/services/lawyer_case_research_service.py backend-vercel/src/immcad_api/api/routes/cases.py backend-vercel/src/immcad_api/services/lawyer_case_research_service.py tests/test_api_scaffold.py tests/test_lawyer_case_research_service.py tests/test_cloudflare_backend_migration_artifacts.py` -> pass
  - `PYTHONPATH=src uv run pytest -q tests/test_api_scaffold.py tests/test_lawyer_case_research_service.py tests/test_case_query_validation.py tests/test_case_export_security.py tests/test_export_policy_gate.py tests/test_cloudflare_backend_migration_artifacts.py` -> `75 passed`
  - `npm run test -- --run tests/api-client.contract.test.ts tests/server-runtime-config.contract.test.ts tests/backend-proxy.contract.test.ts` (in `frontend-web/`) -> `37 passed`
  - `make quality` -> pass (`448 passed`)
  - `npm run test` (in `frontend-web/`) -> pass (`64 passed`)
  - `npm run typecheck` (in `frontend-web/`) -> pass

---

# Task Plan - 2026-02-25 - Cloudflare Edge Contract Preflight Guard

## Current Focus
- Add deterministic edge-contract guardrails so preflight and release/deploy workflows fail fast on proxy/frontend contract drift.

## Plan
- [x] Add a dedicated script to validate critical Cloudflare edge-proxy contract literals (allowlist, error envelope, trace headers, frontend compatibility hooks).
- [x] Wire edge-contract check into `scripts/release_preflight.sh` with explicit skip toggle for diagnostics.
- [x] Expose a standalone Make target for local edge-contract preflight.
- [x] Enforce the same check in release/quality CI and Cloudflare backend proxy deploy workflow.
- [x] Add deterministic tests for script behavior and workflow/preflight wiring.
- [x] Run focused verification and a preflight diagnostic execution.

## Review
- Added `scripts/check_cloudflare_edge_proxy_contract.sh` to guard:
  - worker allowlisted paths (`/api/`, `/ops/`, `/healthz`),
  - nested proxy error payload keys (`code`, `trace_id`, `policy_reason`),
  - trace header continuity (`x-trace-id` and `x-immcad-trace-id`) in error/success paths,
  - frontend API-client compatibility for legacy edge envelope + legacy trace header fallback.
- Updated Cloudflare worker success header behavior:
  - `backend-cloudflare/src/worker.ts` now sets `x-trace-id` on proxied success responses (not only `x-immcad-trace-id`).
- Wired checks into execution paths:
  - `scripts/release_preflight.sh` now runs edge-contract checks by default (toggle: `SKIP_CLOUDFLARE_EDGE_CONTRACT_CHECK=1`).
  - `Makefile` now includes `cloudflare-edge-contract-preflight`.
  - `.github/workflows/quality-gates.yml`, `.github/workflows/release-gates.yml`, and `.github/workflows/cloudflare-backend-proxy-deploy.yml` now run the edge-contract check.
- Added/updated tests:
  - `tests/test_cloudflare_edge_proxy_contract_script.py`
  - `tests/test_release_preflight_script.py`
  - `tests/test_cloudflare_backend_proxy_deploy_workflow.py`
  - `tests/test_quality_gates_workflow.py`
  - `tests/test_release_gates_workflow.py`
- Verification evidence:
  - `bash scripts/check_cloudflare_edge_proxy_contract.sh` -> pass
  - `PYTHONPATH=src uv run pytest -q tests/test_cloudflare_edge_proxy_contract_script.py tests/test_release_preflight_script.py tests/test_cloudflare_backend_proxy_deploy_workflow.py tests/test_quality_gates_workflow.py tests/test_release_gates_workflow.py tests/test_cloudflare_backend_migration_artifacts.py` -> `33 passed`
  - `PYTHONPATH=src uv run pytest -q tests/test_cloudflare_free_plan_readiness_script.py tests/test_cloudflare_backend_proxy_deploy_workflow.py tests/test_cloudflare_edge_proxy_contract_script.py tests/test_release_preflight_script.py tests/test_quality_gates_workflow.py tests/test_release_gates_workflow.py tests/test_cloudflare_backend_migration_artifacts.py` -> `36 passed`
  - `npm run test --prefix frontend-web -- --run tests/api-client.contract.test.ts tests/backend-proxy.contract.test.ts` -> `24 passed`
  - `SKIP_CLOUDFLARE_FREE_PLAN_CHECK=1 SKIP_WRANGLER_AUTH_CHECK=1 bash scripts/release_preflight.sh --allow-dirty` -> pass
  - `make quality` -> pass (`453 passed`)
  - `npm run test --prefix frontend-web` -> pass (`65 passed`)
  - `npm run typecheck --prefix frontend-web` -> pass

---

# Task Plan - 2026-02-26 - Cloudflare Named Tunnel Systemd Hardening

## Current Focus
- Close the remaining Cloudflare-only production hardening blocker by migrating the local backend origin stack from detached user processes to reboot-persistent `systemd` services, while preserving live traffic on the named tunnel path and documenting operational decisions.

## Plan
- [x] Add `systemd` units for the local backend (`uvicorn`) and Cloudflare named tunnel connector, plus a grouping target for the origin stack.
- [x] Add an installer/switchover script that persists the tunnel token securely, installs/enables units, retires detached Quick Tunnel fallback processes, and runs smoke checks.
- [x] Add a health-check script and Make targets for repeatable operational validation.
- [x] Execute the systemd switchover, verify live Cloudflare health/search/lawyer-research routes, and confirm the tunnel token is no longer exposed in process args.
- [x] Update known-issues and lessons with the final state and token-file compatibility learnings.

## Review
- Added reboot-persistent Cloudflare origin supervision:
  - `ops/systemd/immcad-backend-local.service`
  - `ops/systemd/immcad-cloudflared-named-tunnel.service`
  - `ops/systemd/immcad-cloudflare-origin-stack.target`
- Added repeatable operations tooling:
  - `scripts/install_cloudflare_named_tunnel_systemd_stack.sh`
  - `scripts/check_cloudflare_named_origin_stack_health.sh`
  - `Makefile` targets: `backend-cf-origin-stack-systemd-install`, `backend-cf-origin-stack-health`
- Executed live switchover to systemd-managed services and retired detached Quick Tunnel fallback processes.
- Security hardening during rollout:
  - switched tunnel service from `cloudflared ... --token` to `--token-file` to avoid token exposure in `ps` / `systemctl status`
  - installer now writes token file with `ec2-user:ec2-user` and `0600` after discovering `cloudflared` rejected a root-owned group-readable token file.
- Validation evidence:
  - `bash scripts/check_cloudflare_named_origin_stack_health.sh --with-search` -> pass
  - `curl https://immcad-api.arkiteto.dpdns.org/healthz` -> `200`
  - `POST https://immcad.arkiteto.dpdns.org/api/search/cases` -> `200`
  - `POST https://immcad-api.arkiteto.dpdns.org/api/research/lawyer-cases` (authenticated) -> `200`, structured cases returned
  - `POST https://immcad.arkiteto.dpdns.org/api/research/lawyer-cases` -> `200`, structured cases returned
  - `ps -ef | rg 'cloudflared tunnel run'` shows `--token-file /etc/immcad/immcad_named_tunnel.token` (token hidden)
  - `ps -ef | rg 'trycloudflare'` -> no matches (Quick Tunnel fallback retired)

---

# Task Plan - 2026-02-26 - Prompt / Frontend / Case-Law Reliability Stabilization

## Current Focus
- Review and remediate production-readiness gaps causing poor first impression, slow/opaque responses, weak answer correctness, and brittle case-law research behavior.

## Plan
- [x] Align prompt/runtime contract (remove unsupported chat-history claims or implement memory injection).
- [x] Fix citation semantics so frontend-displayed citations reflect verified grounding, not provider passthrough placeholders.
- [x] Split frontend async state by workflow (chat vs case search vs export) so the composer stays responsive.
- [x] Add slow-response detection UX (elapsed time, degraded-state messaging, trace-aware retry/cancel guidance).
- [x] Unify incident/degraded banners across chat + case-law + export failures; mount diagnostics panel when enabled.
- [x] Run `/api/chat` blocking backend work in a threadpool to reduce event-loop contention.
- [x] Harden case-search fallback behavior (official-source errors should not prevent CanLII fallback when available).
- [x] Revisit case-law query validation/planner interaction so valid matter summaries are not rejected too early.
- [x] Separate lawyer-research result visibility from export eligibility so useful cases do not appear “broken.”
- [x] Expand eval/regression coverage for prompt correctness, case-law reliability, and frontend slow-state UX.

## Review (2026-02-26 - Batch 1 Progress)
- Completed a first stabilization batch covering prompt/runtime contract accuracy, frontend async-state split, chat slow-response loading cues, chat degraded/fallback response labeling, `/api/chat` threadpool execution, and case-search fallback hardening for official-source `ApiError` failures.
- Verification run: `uv run pytest -q tests/test_case_search_service.py tests/test_openai_provider.py tests/test_chat_service.py` (pass), `uv run pytest -q tests/test_api_scaffold.py::test_chat_endpoint_contract_shape tests/test_api_scaffold.py::test_chat_policy_block_response tests/test_api_scaffold.py::test_chat_case_law_query_uses_case_search_tool_citations tests/test_api_scaffold.py::test_chat_validation_error_for_unsupported_locale_and_mode` (pass), `npm --prefix frontend-web run typecheck` (pass), `npm --prefix frontend-web run test -- tests/message-list.performance.test.tsx` (pass).
- Remaining high-priority gaps from this plan: none in this stabilization slice (follow-on quality work can continue under separate roadmap items).
- Batch 2 progress (2026-02-26):
  - Lawyer research validation now allows broad matter summaries when intake specificity is sufficiently structured (2+ intake signals), avoiding early rejection of otherwise actionable requests.
  - Added targeted frontend regression coverage for unified non-chat workflow error banners (case-law search and export paths) with diagnostics-enabled trace visibility.
  - Confirmed export-policy blocks preserve result visibility with explicit “online review still available” messaging.
- Batch 2 verification evidence:
  - `PYTHONPATH=src uv run pytest -q tests/test_lawyer_research_api.py -k "broad_summary or generic_query"` -> `3 passed, 5 deselected`
  - `PYTHONPATH=src uv run pytest -q tests/test_lawyer_research_api.py tests/test_lawyer_case_research_service.py tests/test_lawyer_research_planner.py tests/test_lawyer_research_schemas.py` -> `28 passed`
  - `PYTHONPATH=src uv run ruff check src/immcad_api/api/routes/lawyer_research.py tests/test_lawyer_research_api.py` -> pass
  - `cd frontend-web && npm run test -- --run tests/chat-shell.contract.test.tsx tests/chat-shell.ui.test.tsx` -> `26 passed`
  - `cd frontend-web && npm run typecheck` -> pass
- Batch 3 progress (2026-02-26):
  - Expanded official grounding catalog coverage for high-frequency immigration intents (study permit extension and spousal sponsorship) so chat grounding has stronger authoritative source recall.
  - Confirmed citation semantics path is grounded-only: providers emit plain text without model-provided citations, and chat response citations remain filtered through grounding validation.
- Batch 3 verification evidence:
  - `PYTHONPATH=src uv run pytest -q tests/test_grounding.py tests/test_chat_service.py tests/test_openai_provider.py tests/test_gemini_provider.py` -> `26 passed`
  - `PYTHONPATH=src uv run ruff check src/immcad_api/services/grounding.py tests/test_grounding.py tests/test_chat_service.py tests/test_openai_provider.py tests/test_gemini_provider.py` -> pass
- Batch 4 progress (2026-02-26):
  - Further expanded retrieval-backed grounding coverage with official IRCC sources for work permits and visitor-status extensions to improve answer grounding recall on high-frequency intake queries.
- Batch 4 verification evidence:
  - `PYTHONPATH=src uv run pytest -q tests/test_grounding.py tests/test_chat_service.py tests/test_openai_provider.py tests/test_gemini_provider.py` -> `28 passed`
  - `PYTHONPATH=src uv run ruff check src/immcad_api/services/grounding.py tests/test_grounding.py tests/test_chat_service.py tests/test_openai_provider.py tests/test_gemini_provider.py` -> pass
  - `make quality` -> pass

## Review (Pre-Implementation Findings)
- Frontend uses a single pending flag across chat, case search, and export flows (`frontend-web/components/chat/use-chat-logic.ts`), which disables unrelated interactions and makes long-running actions feel like the entire app is frozen.
- Incident banner rendering is chat-error-only (`frontend-web/components/chat/status-banner.tsx`) while non-chat failures are reduced to sidebar helper text; `SupportContextPanel` is imported but currently not rendered in `frontend-web/components/chat/chat-shell-container.tsx`.
- Prompt claims full chat-history continuity (`src/immcad_api/policy/prompts.py`) but backend runtime remains stateless for chat turns (`src/immcad_api/providers/prompt_builder.py`, `src/immcad_api/services/chat_service.py`, `src/immcad_api/schemas.py`).
- OpenAI/Gemini providers currently return input grounding citations as response citations (`src/immcad_api/providers/openai_provider.py`, `src/immcad_api/providers/gemini_provider.py`), which can overstate answer grounding quality.
- Grounding is mostly static/keyword-catalog based (`src/immcad_api/services/grounding.py`), so many queries lack relevant evidence and either produce weak answers or safe-fallbacks.
- `CaseSearchService` only treats `SourceUnavailableError` as official-source fallback-safe (`src/immcad_api/services/case_search_service.py`), so other official-client errors can abort fallback behavior.
- Lawyer research/export metadata can make relevant cases look unavailable or broken when source metadata/policy signals are incomplete (`src/immcad_api/services/lawyer_case_research_service.py`, `frontend-web/components/chat/related-case-panel.tsx`).

---

# Task Plan - 2026-02-26 - Cloudflare CLI Interactive Auth + Key Recovery Continuation

## Current Focus
- Install Cloudflare tunnel tooling in Codespaces, complete an interactive Cloudflare auth flow that works in a remote environment, and validate the path to safely cut over the Cloudflare proxy to a replacement backend origin using the recovered backend env (with `CANLII_API_KEY` already upserted).

## Plan
- [x] Install `cloudflared` CLI locally in Codespaces and verify version.
- [x] Run interactive Cloudflare auth (`cloudflared tunnel login`) and confirm local credentials are created.
- [x] Re-check Wrangler auth options for Codespaces (interactive callback workaround vs API token) and document the working path.
- [x] Verify the recovered backend env file is ready for the replacement origin path without changing live Cloudflare routing.
- [x] Add a short review entry with verification evidence and next cutover steps.

## Review
- Installed `cloudflared` in Codespaces (`2026.2.0`) and completed interactive `cloudflared tunnel login`; Cloudflare origin cert saved to `~/.cloudflared/cert.pem`.
- Verified Cloudflare account/tunnel access with `cloudflared tunnel list`; existing named tunnel `a2f7845e-4751-4ba4-b8aa-160edeb69184` (previous production cutover tunnel) is present.
- Confirmed Wrangler OAuth remains non-viable in Codespaces interactive mode for this session because `wrangler login` redirects to `localhost:8976` even when `--callback-host` is changed; this blocks browser callback to the remote Codespace without extra local port-forward choreography.
- Built local runtime environment in Codespaces (`make setup`, installed `uv`) and started IMMCAD backend on `127.0.0.1:8002` using recovered `backend-vercel/.env.production.vercel` (contains recovered production env plus upserted `CANLII_API_KEY`).
- Reconnected the existing named tunnel from Codespaces using a freshly fetched token file (`/tmp/immcad_named_tunnel.token`) and `cloudflared tunnel run --token-file ...`; Cloudflare pushed the expected remote config mapping `immcad-origin-tunnel.arkiteto.dpdns.org -> http://127.0.0.1:8002`.
- Live Cloudflare recovery verification:
  - `https://immcad-origin-tunnel.arkiteto.dpdns.org/healthz` -> `200` (`{"status":"ok","service":"IMMCAD API"}`)
  - `https://immcad-api.arkiteto.dpdns.org/healthz` -> `200`
  - `POST https://immcad.arkiteto.dpdns.org/api/search/cases` -> `200`, real FCA case returned (`2026 FCA 36`)
  - `POST https://immcad-api.arkiteto.dpdns.org/api/research/lawyer-cases` (bearer from recovered env) -> `200`, structured FC case result returned
- CanLII key verification:
  - `make canlii-key-verify` with recovered env loaded -> `[OK] CanLII API key verified. caseDatabases returned: 406`
- Temporary state warning:
  - Production traffic is currently restored through a Codespaces-hosted backend + named tunnel connector. This is functional but not durable; it will drop if the Codespace sleeps/stops. Next step is replacing the lost VPS with a stable origin host and moving the recovered env there.

### Follow-up Fix (2026-02-26) - FC `norma.lexum.com` Export Host Alias
- Patched `case_document_resolver` host trust to allow the FC official-source host (`decisions.fct-cf.gc.ca`) to trust the current FC document host alias (`norma.lexum.com`) used in live Lexum links.
- Added regression coverage:
  - `tests/test_case_document_resolver.py` alias trust unit test
  - `tests/test_case_export_security.py` approval + export success test for FC `norma.lexum.com` document URL
- Verification:
  - `./scripts/venv_exec.sh pytest -q tests/test_case_document_resolver.py tests/test_case_export_security.py` -> `6 passed`
  - Restarted the Codespaces-hosted backend process serving Cloudflare traffic (same named tunnel)
  - Live authenticated `/api/research/lawyer-cases` FC result now reports `pdf_status=available`, `export_allowed=true` for `https://norma.lexum.com/.../document.do`
  - Live export flow (`/api/export/cases/approval` + `/api/export/cases`) for FC `norma.lexum.com` returned `200` with `application/pdf` and `%PDF-` payload

### Follow-up Ops Hardening (2026-02-26) - Detached Codespaces Recovery Runtime
- Moved the temporary Codespaces recovery backend + named tunnel connector from interactive TTY sessions to detached processes (reparented to PID 1) with PID/log/state files under `/tmp/immcad-codespace-named-origin`.
- Validation after detached restart:
  - `cloudflared tunnel info a2f7845e-4751-4ba4-b8aa-160edeb69184` shows active connector from Codespaces
  - `GET https://immcad-api.arkiteto.dpdns.org/healthz` -> `200`
  - `make canlii-key-verify` -> OK
  - `IMMCAD_API_BASE_URL=https://immcad-api.arkiteto.dpdns.org make canlii-live-smoke` -> OK (`Results: 5`)
  - `/api/chat` -> `200` structured response (`answer`, `confidence`, `fallback_used`)
  - `/api/search/cases` -> real official results with export metadata
  - `/api/research/lawyer-cases` -> FC result `pdf_status=available`, `export_allowed=true`

### Next Execution Plan (2026-02-26) - Repeatable Recovery Ops + AI Case-Law Smoke
- [x] Add a repeatable script to start the Codespaces-backed named-tunnel runtime (`uvicorn` + `cloudflared`) with PID/state/log files and post-start health checks.
- [x] Add companion stop/health scripts so runtime lifecycle is deterministic and operator-friendly.
- [x] Add a deterministic chat case-law smoke script that verifies `/api/chat` returns at least one case-law citation source for a known-good prompt.
- [x] Wire new scripts into `Makefile` targets and run end-to-end verification (`start` -> `health` -> `chat smoke` -> `stop`).

### Review (2026-02-26) - Recovery Ops Workflow Implemented
- Added repeatable runtime lifecycle scripts:
  - `scripts/run_cloudflare_named_tunnel_codespace_runtime.sh`
  - `scripts/stop_cloudflare_named_tunnel_codespace_runtime.sh`
  - `scripts/check_cloudflare_named_tunnel_codespace_runtime_health.sh`
- Added deterministic chat case-law retrieval smoke:
  - `scripts/run_chat_case_law_tool_smoke.sh`
  - Asserts non-empty `/api/chat` answer and at least one case-law citation source (`FC_DECISIONS`/`FCA_DECISIONS`/`SCC_DECISIONS`/CanLII).
- Added Make targets:
  - `backend-cf-codespace-runtime-start`
  - `backend-cf-codespace-runtime-stop`
  - `backend-cf-codespace-runtime-health`
  - `chat-case-law-smoke`
- Verification:
  - `bash -n` syntax checks passed for all new scripts.
  - `make backend-cf-codespace-runtime-start` -> idempotent runtime detection works.
  - `make backend-cf-codespace-runtime-health` -> passed (includes search + chat case-law + CanLII live smoke).
  - `make chat-case-law-smoke` (with env/token) -> passed with case-law citation sources `FCA_DECISIONS`, `FC_DECISIONS`.

### Review (2026-02-26) - Free-Tier Validation Bundle + Documentation
- Added consolidated free-tier runtime validator:
  - `scripts/run_free_tier_runtime_validation.sh`
  - Checks backend health, frontend case-search, chat case-law citations, lawyer-research, and CanLII live smoke in one command.
- Added Make target:
  - `free-tier-runtime-validate`
- Extended CI live-smoke workflow:
  - `.github/workflows/canlii-live-smoke.yml` now runs `scripts/run_free_tier_runtime_validation.sh` after CanLII smoke.
- Added free-tier operations documentation:
  - `docs/release/free-tier-cloudflare-operations-runbook-2026-02-26.md`
  - Updated `docs/release/pre-deploy-command-sheet-2026-02-25.md`
  - Updated `docs/release/incident-observability-runbook.md`
  - Updated `docs/release/known-issues.md` with active Codespaces runtime durability risk (`KI-2026-02-26-01`).
- Added regression tests for new script/workflow contracts:
  - `tests/test_canlii_live_smoke_workflow.py`
  - `tests/test_free_tier_runtime_validation_script.py`
- Verification:
  - `bash scripts/run_free_tier_runtime_validation.sh` (with production env vars loaded) -> passed.
  - `./scripts/venv_exec.sh pytest -q tests/test_canlii_live_smoke_workflow.py tests/test_free_tier_runtime_validation_script.py tests/test_release_preflight_script.py tests/test_cloudflare_free_plan_readiness_script.py` -> `10 passed`.

---

# Task Plan - 2026-02-27 - Document Upload/Disclosure Consistency Continuation

## Current Focus
- Continue the document upload/disclosure hardening pass by removing remaining identifier inconsistencies and aligning allowed upload types with deterministic extraction behavior.

## Plan
- [x] Fix readiness output key mismatch for translator declaration requirements.
- [x] Harden extraction to parse only recognized upload signatures (`pdf/png/jpeg/tiff`) instead of broad auto-detection.
- [x] Add/adjust tests for valid PNG intake behavior and malformed image handling.
- [x] Deduplicate readiness warnings for deterministic API output across multi-file uploads.
- [x] Re-run document intake/readiness/upload route test suites and lint/sync verification.

## Review
- Updated readiness requirement output to use `translator_declaration` consistently across policy evaluation and package checks:
  - `src/immcad_api/policy/document_requirements.py`
  - `backend-vercel/src/immcad_api/policy/document_requirements.py`
- Tightened extraction parser selection to signature-detected supported formats only:
  - `src/immcad_api/services/document_extraction.py`
  - `backend-vercel/src/immcad_api/services/document_extraction.py`
- Extended service coverage for image uploads:
  - `tests/test_document_intake_service.py` now verifies valid PNG payloads are accepted for OCR-review workflow (`needs_review` + `ocr_required`).
  - `tests/test_document_upload_security.py` verifies both malformed-image failure behavior and valid PNG acceptance behavior.
- Readiness API now deduplicates and sorts warning issues before response serialization, preventing duplicate warning entries across processed files:
  - `src/immcad_api/api/routes/documents.py`
  - `backend-vercel/src/immcad_api/api/routes/documents.py`
  - `tests/test_document_routes.py` includes regression coverage for deduplicated warnings.
- Verification evidence:
  - `PYTHONPATH=src uv run pytest -q tests/test_document_routes.py tests/test_document_upload_security.py tests/test_document_intake_service.py tests/test_document_requirements.py` -> `20 passed`
  - `PYTHONPATH=src uv run ruff check src/immcad_api/api/routes/documents.py src/immcad_api/services/document_extraction.py src/immcad_api/policy/document_requirements.py tests/test_document_routes.py tests/test_document_upload_security.py tests/test_document_intake_service.py` -> pass
  - `PYTHONPATH=src uv run python scripts/validate_backend_vercel_source_sync.py` -> pass

---

# Task Plan - 2026-02-27 - Free Open-Source OCR Continuation

## Current Focus
- Continue the document upload/disclosure hardening by adding a free open-source OCR fallback for scanned files and validating runtime dependencies.

## Plan
- [x] Install free OCR runtime dependencies (Tesseract + supporting system packages) and Python OCR libraries.
- [x] Integrate optional OCR fallback into document extraction when native text layer is empty.
- [x] Add deterministic tests for OCR fallback and non-OCR paths.
- [x] Verify tests, lint, and backend/source sync.

## Review
- Installed open-source OCR stack components in this environment:
  - System packages: `tesseract-ocr`, `ghostscript`, `qpdf`, `unpaper`, `pngquant`
  - Python packages: `pytesseract`, `ocrmypdf`
- Integrated optional OCR fallback in extraction:
  - `src/immcad_api/services/document_extraction.py`
  - `backend-vercel/src/immcad_api/services/document_extraction.py`
  - Behavior: if page text extraction is empty, OCR is attempted (Tesseract) and failures degrade gracefully to empty OCR text (no 500 regressions).
  - Feature toggle: `IMMCAD_ENABLE_TESSERACT_OCR` (`1` by default, disable with `0/false/no/off`).
- Added/updated tests:
  - `tests/test_document_extraction.py` (new): unsupported signature rejection, OCR fallback path, and skip-OCR when native text exists.
  - `tests/test_document_intake_service.py`: deterministic image test and OCR-fallback classification path.
- Verification evidence:
  - `PYTHONPATH=src uv run pytest -q tests/test_document_extraction.py tests/test_document_intake_service.py tests/test_document_upload_security.py tests/test_document_routes.py tests/test_document_requirements.py` -> `25 passed`
  - `PYTHONPATH=src uv run ruff check src/immcad_api/services/document_extraction.py tests/test_document_extraction.py tests/test_document_intake_service.py` -> pass
  - `PYTHONPATH=src uv run python scripts/validate_backend_vercel_source_sync.py` -> pass
- Dependency status snapshot:
  - Installed binaries: `tesseract`, `gs`, `qpdf`, `unpaper`, `pngquant`
  - Missing optional binary: `jbig2`
  - Installed Python modules: `pytesseract`, `ocrmypdf`, `PIL`

---

# Task Plan - 2026-02-27 - Rule Research + Rule-Aware Compilation Plan

## Current Focus
- Research current Federal Court and IRB filing-rule requirements from primary sources, then produce a source-cited implementation plan for rule-aware document compilation.

## Plan
- [x] Gather and review primary legal sources for Federal Court JR + IRB divisions (`RPD`, `RAD`, `ID`, `IAD`).
- [x] Identify enforceable requirements relevant to compilation (required documents, order/index/TOC, pagination, translation declarations, timing constraints).
- [x] Draft a source-cited implementation plan mapped to current codebase components and tests.
- [x] Save implementation plan under `docs/plans/` for execution handoff.

## Review
- Research-backed plan saved:
  - `docs/plans/2026-02-27-rule-aware-document-compilation-implementation-plan.md`
- Research baseline saved:
  - `docs/research/2026-02-27-court-tribunal-document-compilation-rules-baseline.md`
- Primary-source baseline covered:
  - Federal Court immigration JR rules (SOR/93-22)
  - Federal Courts Rules (SOR/98-106)
  - IRB RPD rules (SOR/2012-256)
  - IRB RAD rules (SOR/2012-257)
  - IRB ID rules (SOR/2002-229)
  - IRB IAD rules (current SOR/2022-277)

---

# Task Plan - 2026-02-27 - Rule-Aware Compilation Execution (Parallel Agents)

## Current Focus
- Execute the rule-aware court/tribunal document compilation implementation plan end-to-end with parallel backend/frontend tracks and verification.

## Plan
- [x] Implement versioned, source-cited document compilation rule catalog and strict loader validation.
- [x] Implement rule validator and metadata-first assembly planner (TOC page ranges + package page map).
- [x] Implement forum record builders and integrate package generation with compilation profiles/rule violations.
- [x] Expand intake/store/schema contracts for per-file compilation metadata and backward-safe decoding.
- [x] Upgrade readiness/package routes and frontend UI/contracts for violations, TOC, pagination, and block reasons.
- [x] Add OCR capability/confidence outputs, compilation telemetry counters, and E2E compilation matrix tests.
- [x] Sync backend-vercel source mirror and run backend/frontend verification.

## Review
- New backend policy/assembly modules:
  - `src/immcad_api/policy/document_compilation_rules.py`
  - `src/immcad_api/policy/document_compilation_validator.py`
  - `src/immcad_api/services/document_assembly_service.py`
  - `src/immcad_api/services/record_builders/*.py`
  - `data/policy/document_compilation_rules.ca.json`
- Integrated runtime/API/schema updates:
  - `src/immcad_api/services/document_package_service.py`
  - `src/immcad_api/api/routes/documents.py`
  - `src/immcad_api/schemas.py`
  - `src/immcad_api/services/document_intake_service.py`
  - `src/immcad_api/services/document_matter_store.py`
  - `src/immcad_api/services/document_extraction.py`
  - `src/immcad_api/telemetry/request_metrics.py`
- Frontend contract/UX updates:
  - `frontend-web/lib/api-client.ts`
  - `frontend-web/components/chat/types.ts`
  - `frontend-web/components/chat/use-chat-logic.ts`
  - `frontend-web/components/chat/related-case-panel.tsx`
  - `frontend-web/tests/document-compilation.contract.test.tsx`
- Added test suites:
  - `tests/test_document_compilation_rules.py`
  - `tests/test_document_compilation_validator.py`
  - `tests/test_document_assembly_service.py`
  - `tests/test_record_builders.py`
  - `tests/test_document_compilation_state.py`
  - `tests/test_document_compilation_routes.py`
  - `tests/test_document_compilation_e2e.py`
  - `tests/test_document_extraction_limits.py`
- Verification evidence:
  - `make test-document-compilation` -> `71 passed`
  - `PYTHONPATH=src uv run pytest -q ...` (document compilation matrix) -> `96 passed`
  - `npm --prefix frontend-web run test -- tests/document-compilation.contract.test.tsx tests/chat-shell.contract.test.tsx` -> `20 passed`
  - `npm --prefix frontend-web run lint -- --file lib/api-client.ts --file components/chat/types.ts --file components/chat/use-chat-logic.ts --file components/chat/related-case-panel.tsx --file tests/document-compilation.contract.test.tsx` -> pass
  - `npm --prefix frontend-web run typecheck` -> pass
  - `PYTHONPATH=src uv run ruff check <changed src/backend-vercel/tests files>` -> pass
  - `PYTHONPATH=src uv run python scripts/validate_backend_vercel_source_sync.py` -> pass

---

# Task Plan - 2026-02-27 - Runtime Compilation Profile Selection + Capability Gap Documentation

## Current Focus
- Complete runtime-selectable compilation profile behavior (FC JR leave vs hearing and persisted profile selection), preserve compatibility with existing package-service test stubs, and publish a plain-language capability/gap document for court/tribunal compilation.

## Plan
- [x] Finish `DocumentPackageService` profile resolver API and profile-aware rule-evaluation flow.
- [x] Add route compatibility shims for legacy package-service stubs (missing resolver or `compilation_profile_id` arg).
- [x] Finalize schema/store support for `compilation_profile_id` persistence + decoding.
- [x] Add/extend backend tests for resolver behavior, route validation, legacy stub compatibility, and store round-trip behavior.
- [x] Sync `backend-vercel` mirrored source files.
- [x] Publish capability-gap documentation covering can-do vs cannot-yet, key risks, and prioritized improvements.

## Review
- Parallel execution via subagents (independent ownership tracks):
  - Service/profile resolver + rule-evaluation compatibility.
  - Route intake/package compatibility + invalid profile tests.
  - Schema/store persistence typing + round-trip tests.
- Runtime profile selection completed:
  - Intake accepts optional `compilation_profile_id` and validates forum/profile consistency when resolver is available.
  - Selected profile is persisted in matter store and reused by readiness/package endpoints.
  - Package service now exposes `resolve_compilation_profile_id(...)` and defaults by forum when no profile is requested.
- Backward compatibility preserved:
  - Package service now handles monkeypatched legacy `_evaluate_rule_violations(...)` signatures used by tests.
  - Route logic falls back when custom package stubs do not implement resolver/profile-aware build signature.
- New documentation published:
  - `docs/research/2026-02-27-document-compilation-capability-gap-assessment.md`
  - `docs/research/README.md` index updated.
- Progress note (2026-02-27):
  - Updated `docs/research/2026-02-27-document-compilation-capability-gap-assessment.md` to reflect ranked classification candidates + confidence as implemented, and revised classification risk wording to partially mitigated/residual risk.
  - Added integration coverage for profile defaults/overrides and persisted matter-state behavior in `tests/test_document_compilation_e2e.py`:
    - default profile assignment by forum at intake
    - `federal_court_jr_hearing` override persistence through readiness/package responses
  - Updated the P0 roadmap status in `docs/research/2026-02-27-document-compilation-capability-gap-assessment.md` to mark profile-selection integration tests as implemented.
  - Added `record_sections` contract support in readiness/package responses and wired forum/profile record-builder sections through package generation, with builder doc-type labels aligned to classifier/catalog vocabulary.
  - Updated capability-gap documentation to mark record-section wiring as implemented and narrow the remaining gap to typed-slot validation + frontend rendering.
  - Added a feature-flagged compiled binder metadata path:
    - persisted per-file source payload bytes in matter state (`source_files`)
    - package/readiness now surface `compiled_artifact` metadata when `IMMCAD_ENABLE_COMPILED_PDF` is enabled and source coverage is complete
    - default runtime remains `metadata_plan_only` when flag is off or source coverage is incomplete
- Verification evidence:
  - `uv run pytest -q tests/test_document_intake_service.py tests/test_document_intake_schemas.py tests/test_document_routes.py tests/test_document_package_service.py tests/test_document_compilation_routes.py tests/test_document_matter_store.py` -> `63 passed`
  - `uv run pytest -q tests/test_document_compilation_e2e.py tests/test_document_routes.py tests/test_document_compilation_routes.py` -> `29 passed`
  - `uv run pytest -q tests/test_document_package_service.py tests/test_document_compilation_routes.py tests/test_document_intake_schemas.py tests/test_record_builders.py tests/test_document_compilation_e2e.py tests/test_document_routes.py` -> `76 passed`
  - `PYTHONPATH=src uv run pytest -q tests/test_document_package_service.py tests/test_document_matter_store.py tests/test_document_compilation_e2e.py tests/test_document_compilation_routes.py tests/test_document_intake_schemas.py` -> `61 passed`
  - `uv run ruff check src/immcad_api/services/document_intake_service.py src/immcad_api/schemas.py src/immcad_api/api/routes/documents.py src/immcad_api/services/document_package_service.py tests/test_document_intake_service.py tests/test_document_intake_schemas.py tests/test_document_routes.py tests/test_document_package_service.py tests/test_document_compilation_routes.py backend-vercel/src/immcad_api/services/document_intake_service.py backend-vercel/src/immcad_api/schemas.py backend-vercel/src/immcad_api/api/routes/documents.py backend-vercel/src/immcad_api/services/document_package_service.py` -> pass
  - `uv run ruff check src/immcad_api/schemas.py src/immcad_api/services/document_package_service.py src/immcad_api/api/routes/documents.py src/immcad_api/services/record_builders/*.py tests/test_document_package_service.py tests/test_document_compilation_routes.py tests/test_document_intake_schemas.py tests/test_record_builders.py tests/test_document_compilation_e2e.py backend-vercel/src/immcad_api/schemas.py backend-vercel/src/immcad_api/services/document_package_service.py backend-vercel/src/immcad_api/api/routes/documents.py backend-vercel/src/immcad_api/services/record_builders/*.py` -> pass
  - `PYTHONPATH=src uv run ruff check src/immcad_api/schemas.py src/immcad_api/services/document_package_service.py src/immcad_api/services/document_matter_store.py src/immcad_api/api/routes/documents.py tests/test_document_package_service.py tests/test_document_matter_store.py tests/test_document_compilation_e2e.py tests/test_document_compilation_routes.py tests/test_document_intake_schemas.py backend-vercel/src/immcad_api/schemas.py backend-vercel/src/immcad_api/services/document_package_service.py backend-vercel/src/immcad_api/services/document_matter_store.py backend-vercel/src/immcad_api/api/routes/documents.py` -> pass
  - `PYTHONPATH=src uv run python scripts/validate_backend_vercel_source_sync.py` -> pass
  - `make test-document-compilation` -> `109 passed`
  - `make test-document-compilation` -> `115 passed`
  - `make docs-audit` -> pass (`[docs-maintenance] audited files: 78`)

---

# Task Plan - 2026-02-27 - Compiled Binder Download Endpoint (Step-by-Step)

## Current Focus
- Expose a production-safe download path for compiled binder PDFs so clients can retrieve actual PDF bytes when a matter is ready and compiled mode is enabled.

## Plan
- [x] Add package-service API for compiled binder payload generation with metadata consistency checks.
- [x] Add backend route (`/api/documents/matters/{matter_id}/package/download`) with policy-safe error handling and PDF response headers.
- [x] Add backend tests for success, blocked-not-ready, disabled/unavailable binder, and not-found matter cases.
- [x] Mirror backend changes to `backend-vercel` source tree and validate source sync.
- [x] Add frontend proxy route and API client method for binder download, with contract tests.
- [x] Run targeted and broader verification and record evidence.

## Review
- Backend service/runtime:
  - Added `DocumentPackageService.build_compiled_binder(...)` to return `(package, payload_bytes)` for eligible matters, with payload-derived artifact metadata alignment.
  - Added compiled binder download route:
    - `GET /api/documents/matters/{matter_id}/package/download`
    - `404` when matter is missing
    - `409 POLICY_BLOCKED document_package_not_ready` when package is incomplete/blocked
    - `409 POLICY_BLOCKED document_compiled_artifact_unavailable` when compiled output is unavailable
    - `200 application/pdf` with `content-disposition` when successful
- Frontend integration:
  - Added proxy route `frontend-web/app/api/documents/matters/[matterId]/package/download/route.ts`.
  - Added API client method `downloadMatterPackagePdf(matterId)` returning blob/filename/content type.
  - Added/updated contract tests for new route and client behavior.
- Verification evidence:
  - `PYTHONPATH=src uv run ruff check src/immcad_api/services/document_package_service.py src/immcad_api/api/routes/documents.py tests/test_document_package_service.py tests/test_document_routes.py tests/test_document_compilation_routes.py tests/test_document_compilation_e2e.py backend-vercel/src/immcad_api/services/document_package_service.py backend-vercel/src/immcad_api/api/routes/documents.py` -> pass
  - `PYTHONPATH=src uv run pytest -q tests/test_document_package_service.py tests/test_document_routes.py tests/test_document_compilation_routes.py tests/test_document_compilation_e2e.py` -> `53 passed`
  - `npm --prefix frontend-web run test -- tests/document-package-download-route.contract.test.ts tests/api-client.contract.test.ts` -> `17 passed`
  - `npm --prefix frontend-web run lint -- --file app/api/documents/matters/[matterId]/package/download/route.ts --file lib/api-client.ts --file tests/document-package-download-route.contract.test.ts --file tests/api-client.contract.test.ts` -> pass
  - `PYTHONPATH=src uv run python scripts/validate_backend_vercel_source_sync.py` -> pass
  - `make test-document-compilation` -> `123 passed`
  - `make docs-audit` -> pass (`[docs-maintenance] audited files: 78`)

---

# Task Plan - 2026-02-27 - Compiled Binder Download UX Wiring

## Current Focus
- Complete frontend chat-panel UX for compiled binder download so users can trigger PDF download directly from the document workflow once compiled output is available.

## Plan
- [x] Wire document download state and callback through chat hook/container/panel props.
- [x] Add a document-workflow "Download binder PDF" action with proper disable/enable gating for compiled mode.
- [x] Surface compiled-binder availability metadata in the panel summary.
- [x] Add contract test coverage for end-to-end compiled binder download behavior.
- [x] Run frontend tests, lint, and typecheck for touched files.

## Review
- Frontend workflow updates:
  - `frontend-web/components/chat/related-case-panel.tsx`
    - Added `Download binder PDF` button in document actions.
    - Added disable gating to require compiled output + artifact metadata.
    - Included download state in control locking and workflow-mode activation.
    - Added compiled artifact summary text (`filename`, `pageCount`) and metadata-only guidance text.
  - `frontend-web/components/chat/use-chat-logic.ts`
    - (Already wired in prior step) uses `downloadMatterPackagePdf` callback and browser-download helper.
- Progress note (2026-02-27):
  - Added a near-action download hint/tooltip message for metadata-only compilation mode:
    - "Download unavailable: compilation mode is metadata only. Generate a compiled PDF binder to enable download."
  - Extended contract coverage to assert the metadata-only disabled state for `Download binder PDF`.
- Contract coverage:
  - `frontend-web/tests/chat-shell.contract.test.tsx`
    - Added `downloads compiled binder PDF when compiled output is available` scenario covering:
      - intake -> readiness -> package generation (`compiled_pdf`) -> download call
      - browser download trigger (`URL.createObjectURL`, anchor click, revoke)
      - support-context endpoint update for package download.
- Verification evidence:
  - `npm --prefix frontend-web run test -- tests/chat-shell.contract.test.tsx tests/chat-shell.ui.test.tsx tests/document-compilation.contract.test.tsx` -> `30 passed`
  - `npm --prefix frontend-web run test -- tests/chat-shell.contract.test.tsx` -> `19 passed`
  - `npm --prefix frontend-web run lint -- --file components/chat/related-case-panel.tsx --file tests/chat-shell.contract.test.tsx` -> pass
  - `npm --prefix frontend-web run typecheck` -> pass
  - `make test-document-compilation` -> `123 passed`

---

# Task Plan - 2026-02-27 - Top 5 Priorities (Document Compilation)

## Current Focus
- Prioritize the next highest-impact steps to move from metadata-first compilation to production-safe, court/tribunal-ready document assembly and broader immigration coverage.

## Top 5 Priorities
1. Promote compiled binder generation from feature-flag path to production-safe default.
2. Close document classification ambiguity with deterministic doc-type normalization and review workflow gates.
3. Complete rule-to-record section wiring across all forums/profiles (FC JR + IRB divisions) with consistent section outputs.
4. Implement procedural timing/deadline validation and forum/channel submission preflight checks.
5. Expand profile coverage beyond current litigation forums (IAD subtype profiles first, then non-litigation immigration application packages).

## Execution Plan
- [x] Priority 1: Compiled Binder Production Path
  - [x] Finalize merge/bookmark/page-stamp pipeline and artifact integrity validation.
  - [x] Add CI matrix coverage for compiled mode (mixed scans, malformed PDFs, OCR-heavy inputs).
  - [x] Define rollout controls: feature flag guardrails, canary metrics, and rollback playbook.
- [x] Priority 2: Classification Reliability
  - [x] Introduce canonical doc-type dictionary shared by classifier, rules catalog, and record builders.
  - [x] Enforce confidence thresholds that trigger explicit `needs_review` instead of silent auto-assignment.
  - [x] Add audit telemetry for low-confidence classifications by forum/profile.
- [x] Priority 3: Record Section Completeness
  - [x] Map every required/conditional rule item to a deterministic record section slot.
  - [x] Ensure readiness/package responses include section-level status + missing rationale.
  - [x] Add frontend rendering for section completeness and section-level remediation guidance.
- [x] Priority 4: Deadline + Preflight Enforcement
  - [x] Add inputs and validators for decision/hearing/service dates and filing windows.
  - [x] Add channel constraints (file count/size limits and upload preflight blocks/warnings).
  - [x] Add deterministic tests per forum/profile for deadline pass/fail and override behavior.
- [x] Priority 5: Coverage Expansion
  - [x] Split `iad` into subtype profiles (sponsorship/residency/admissibility) with source-cited constraints.
  - [x] Add first non-litigation application profile family (start with highest-volume immigration package).
  - [x] Publish profile support matrix and explicit “supported vs unsupported” API/UI messaging.

## Sequencing / Dependency Order
1. Priority 1 and Priority 2 in parallel (shared release gate).
2. Priority 3 after Priority 2 canonical dictionary lands.
3. Priority 4 after Priority 1 baseline is stable in compiled mode.
4. Priority 5 after Priorities 1-4 are production-safe.

## Verification Gates
- Gate A (Core reliability): compiled-mode matrix green + no blocker regressions in readiness/package routes.
- Gate B (Policy correctness): rule/section/deadline tests deterministic across FC JR + IRB profiles.
- Gate C (Runtime safety): telemetry dashboards + alert thresholds + rollback drill complete.

## Progress Note (2026-02-27)
- Priority 1 / substep complete:
  - Compiled binder generation now writes deterministic PDF bookmarks from assembly TOC and page stamps (`IMMCAD page X of Y`) into output artifacts.
  - Added compiled artifact integrity validation gate:
    - compiled page count must match assembly plan page map
    - compiled TOC structure/title/page anchors must match expected assembly TOC
    - fallback to `metadata_plan_only` when integrity validation fails
  - Added compiled-mode matrix coverage for:
    - mixed PDF + image payload sources (including image->PDF conversion path)
    - malformed payload fallback to `metadata_plan_only`
    - multipage OCR-heavy style payload handling with deterministic page stamps
  - Fixed source-conversion bug in compiled mode: payloads opened as non-PDF documents are now rejected in the raw-PDF open path (`is_pdf` guard), then converted via inferred image type when applicable.
  - Added operational rollout controls playbook for compiled binder mode:
    - feature-flag guardrails
    - canary success metrics and thresholds
    - explicit rollback criteria and procedure
- Priority 2 / substep complete:
  - Added canonical document-type registry with normalization/validation helpers and integrated it across:
    - rules loader validation (`required/conditional/order/pagination` document-type fields)
    - record-builder section definitions
    - intake classification output normalization
  - Enforced low-confidence review gating in intake pipeline:
    - configurable threshold (`minimum_classification_confidence_for_auto_processing`)
    - low-confidence results now emit `classification_low_confidence` and set `quality_status=needs_review`
  - Extended telemetry for low-confidence classification monitoring:
    - added `low_confidence_classification_files` and `low_confidence_classification_rate` to intake metrics snapshots/events
- Priority 3 / substep complete:
  - Added deterministic rule-to-section slot mapping in package assembly:
    - each required/conditional compilation rule document now resolves to exactly one record section slot
    - package build now raises a deterministic mapping error if a rule document is unmapped/ambiguous
  - Extended `record_sections` response contract with section-level completeness metadata:
    - `section_status`
    - `slot_statuses` (`document_type`, `status`, `rule_scope`, `reason`)
    - `missing_document_types`
    - `missing_reasons`
  - Wired section completeness through package + readiness response payloads and added frontend rendering:
    - new “Record section completeness” panel in document workflow
    - explicit missing-slot guidance and remediation copy surfaced in UI
- Priority 4 / substep complete:
  - Added filing deadline policy evaluation for profile-specific windows with override + approaching warning behavior.
  - Added intake schema/route inputs for `submission_channel`, `decision_date`, `hearing_date`, `service_date`, `filing_date`, and `deadline_override_reason`.
  - Persisted `filing_context` in matter storage and preserved it through classification overrides.
  - Enforced deadline blocking in readiness and package/package-download routes, including package-builder blocking injection for deterministic readiness parity.
  - Added deterministic tests for deadline pass/fail/override and channel-limit preflight behavior.
- Priority 5 / substep complete:
  - Added three subtype-aware IAD profiles to the catalog:
    - `iad_sponsorship`
    - `iad_residency`
    - `iad_admissibility`
  - Extended compilation profile literals and route validation path to accept new IAD subtype IDs.
  - Added subtype support in deadline-policy evaluation and record-section builders.
  - Kept `iad` as the default forum profile for backward compatibility while enabling explicit subtype selection.
  - Added first non-litigation forum/profile path:
    - forum: `ircc_application`
    - default profile: `ircc_pr_card_renewal`
  - Added explicit profile support matrix API endpoint:
    - `GET /api/documents/support-matrix`
  - Added explicit supported-vs-unsupported profile messaging:
    - actionable intake validation message for unsupported profile selection
    - frontend documents panel copy listing currently supported and unsupported profile families.
- Files updated:
  - `src/immcad_api/services/document_package_service.py`
  - `backend-vercel/src/immcad_api/services/document_package_service.py`
  - `tests/test_document_package_service.py`
  - `docs/release/compiled-binder-rollout-playbook.md`
  - `src/immcad_api/policy/document_types.py`
  - `src/immcad_api/policy/document_compilation_rules.py`
  - `src/immcad_api/services/document_intake_service.py`
  - `src/immcad_api/services/record_builders/__init__.py`
  - `src/immcad_api/telemetry/request_metrics.py`
  - `src/immcad_api/api/routes/documents.py`
  - `tests/test_document_intake_service.py`
  - `tests/test_document_compilation_rules.py`
  - `tests/test_record_builders.py`
  - `tests/test_request_metrics.py`
  - `backend-vercel/src/immcad_api/policy/document_types.py`
  - `backend-vercel/src/immcad_api/policy/document_compilation_rules.py`
  - `backend-vercel/src/immcad_api/services/document_intake_service.py`
  - `backend-vercel/src/immcad_api/services/record_builders/__init__.py`
  - `backend-vercel/src/immcad_api/telemetry/request_metrics.py`
  - `backend-vercel/src/immcad_api/api/routes/documents.py`
  - `src/immcad_api/schemas.py`
  - `src/immcad_api/services/document_package_service.py`
  - `backend-vercel/src/immcad_api/schemas.py`
  - `backend-vercel/src/immcad_api/services/document_package_service.py`
  - `tests/test_document_intake_schemas.py`
  - `tests/test_document_compilation_routes.py`
  - `tests/test_document_package_service.py`
  - `tests/test_record_builders.py`
  - `frontend-web/lib/api-client.ts`
  - `frontend-web/components/chat/types.ts`
  - `frontend-web/components/chat/use-chat-logic.ts`
  - `frontend-web/components/chat/related-case-panel.tsx`
  - `frontend-web/tests/document-compilation.contract.test.tsx`
  - `src/immcad_api/policy/document_filing_deadlines.py`
  - `backend-vercel/src/immcad_api/policy/document_filing_deadlines.py`
  - `src/immcad_api/services/document_matter_store.py`
  - `backend-vercel/src/immcad_api/services/document_matter_store.py`
  - `tests/test_document_filing_deadlines.py`
  - `data/policy/document_compilation_rules.ca.json`
  - `src/immcad_api/services/record_builders/__init__.py`
  - `backend-vercel/src/immcad_api/services/record_builders/__init__.py`
  - `tests/test_document_compilation_rules.py`
  - `tests/test_record_builders.py`
  - `tests/test_document_compilation_e2e.py`
  - `src/immcad_api/policy/document_requirements.py`
  - `backend-vercel/src/immcad_api/policy/document_requirements.py`
  - `src/immcad_api/services/record_builders/ircc_application.py`
  - `backend-vercel/src/immcad_api/services/record_builders/ircc_application.py`
  - `frontend-web/components/chat/related-case-panel.tsx`
  - `frontend-web/lib/api-client.ts`
  - `tests/test_document_policy_matrix.py`
- Verification evidence:
  - `PYTHONPATH=src uv run pytest -q tests/test_document_package_service.py` -> `23 passed`
  - `PYTHONPATH=src uv run pytest -q tests/test_document_routes.py tests/test_document_compilation_e2e.py tests/test_document_compilation_routes.py` -> `35 passed`
  - `PYTHONPATH=src uv run ruff check src/immcad_api/services/document_package_service.py backend-vercel/src/immcad_api/services/document_package_service.py tests/test_document_package_service.py` -> pass
  - `PYTHONPATH=src uv run python scripts/validate_backend_vercel_source_sync.py` -> pass
  - `make test-document-compilation` -> `128 passed`
  - `make docs-audit` -> pass (`[docs-maintenance] audited files: 79`)
  - `PYTHONPATH=src uv run pytest -q tests/test_document_intake_service.py tests/test_document_compilation_rules.py tests/test_record_builders.py tests/test_request_metrics.py` -> `30 passed`
  - `PYTHONPATH=src uv run pytest -q tests/test_document_routes.py tests/test_document_intake_schemas.py tests/test_document_compilation_routes.py tests/test_document_compilation_e2e.py tests/test_document_package_service.py` -> `85 passed`
  - `PYTHONPATH=src uv run ruff check src/immcad_api/policy/document_types.py src/immcad_api/policy/document_compilation_rules.py src/immcad_api/services/document_intake_service.py src/immcad_api/services/record_builders/__init__.py src/immcad_api/telemetry/request_metrics.py src/immcad_api/api/routes/documents.py tests/test_document_intake_service.py tests/test_document_compilation_rules.py tests/test_record_builders.py tests/test_request_metrics.py backend-vercel/src/immcad_api/policy/document_types.py backend-vercel/src/immcad_api/policy/document_compilation_rules.py backend-vercel/src/immcad_api/services/document_intake_service.py backend-vercel/src/immcad_api/services/record_builders/__init__.py backend-vercel/src/immcad_api/telemetry/request_metrics.py backend-vercel/src/immcad_api/api/routes/documents.py` -> pass
  - `PYTHONPATH=src uv run python scripts/validate_backend_vercel_source_sync.py` -> pass
  - `make test-document-compilation` -> `133 passed`
  - `PYTHONPATH=src uv run pytest -q tests/test_document_intake_schemas.py tests/test_document_compilation_routes.py tests/test_document_package_service.py tests/test_record_builders.py tests/test_document_compilation_e2e.py` -> `77 passed`
  - `npm --prefix frontend-web run test -- tests/document-compilation.contract.test.tsx` -> `4 passed`
  - `npm --prefix frontend-web run test -- tests/chat-shell.contract.test.tsx` -> `19 passed`
  - `npm --prefix frontend-web run typecheck` -> pass
  - `npm --prefix frontend-web run lint -- --file components/chat/related-case-panel.tsx --file components/chat/use-chat-logic.ts --file components/chat/types.ts --file lib/api-client.ts --file tests/document-compilation.contract.test.tsx` -> pass
  - `PYTHONPATH=src uv run ruff check src/immcad_api/schemas.py src/immcad_api/services/document_package_service.py tests/test_document_intake_schemas.py tests/test_document_compilation_routes.py tests/test_document_package_service.py tests/test_record_builders.py backend-vercel/src/immcad_api/schemas.py backend-vercel/src/immcad_api/services/document_package_service.py` -> pass
  - `PYTHONPATH=src uv run python scripts/validate_backend_vercel_source_sync.py` -> pass
  - `make test-document-compilation` -> `135 passed`
  - `PYTHONPATH=src uv run pytest -q tests/test_document_filing_deadlines.py tests/test_document_intake_schemas.py tests/test_document_routes.py` -> `72 passed`
  - `PYTHONPATH=src uv run pytest -q tests/test_document_matter_store.py tests/test_document_package_service.py tests/test_document_compilation_routes.py tests/test_document_compilation_e2e.py` -> `47 passed`
  - `PYTHONPATH=src uv run ruff check src/immcad_api/policy/document_filing_deadlines.py src/immcad_api/api/routes/documents.py tests/test_document_filing_deadlines.py tests/test_document_intake_schemas.py tests/test_document_routes.py` -> pass
  - `PYTHONPATH=src uv run python scripts/validate_backend_vercel_source_sync.py` -> pass
  - `make test-document-compilation` -> `147 passed`
  - `PYTHONPATH=src uv run pytest -q tests/test_document_intake_schemas.py tests/test_document_compilation_rules.py tests/test_record_builders.py tests/test_document_filing_deadlines.py tests/test_document_compilation_e2e.py` -> `86 passed`
  - `PYTHONPATH=src uv run ruff check src/immcad_api/schemas.py src/immcad_api/policy/document_filing_deadlines.py src/immcad_api/services/record_builders/__init__.py tests/test_document_intake_schemas.py tests/test_document_compilation_rules.py tests/test_record_builders.py tests/test_document_filing_deadlines.py tests/test_document_compilation_e2e.py backend-vercel/src/immcad_api/schemas.py backend-vercel/src/immcad_api/policy/document_filing_deadlines.py backend-vercel/src/immcad_api/services/record_builders/__init__.py` -> pass
  - `PYTHONPATH=src uv run python scripts/validate_backend_vercel_source_sync.py` -> pass
  - `make test-document-compilation` -> `157 passed`
  - `PYTHONPATH=src uv run pytest -q tests/test_document_intake_schemas.py tests/test_document_compilation_rules.py tests/test_record_builders.py tests/test_document_policy_matrix.py tests/test_document_package_service.py tests/test_document_routes.py tests/test_document_compilation_e2e.py` -> `145 passed`
  - `PYTHONPATH=src uv run ruff check src/immcad_api/policy/document_requirements.py src/immcad_api/schemas.py src/immcad_api/policy/document_compilation_rules.py src/immcad_api/services/document_package_service.py src/immcad_api/api/routes/documents.py src/immcad_api/services/record_builders/__init__.py src/immcad_api/services/record_builders/ircc_application.py tests/test_document_intake_schemas.py tests/test_document_compilation_rules.py tests/test_record_builders.py tests/test_document_policy_matrix.py tests/test_document_package_service.py tests/test_document_routes.py tests/test_document_compilation_e2e.py backend-vercel/src/immcad_api/policy/document_requirements.py backend-vercel/src/immcad_api/schemas.py backend-vercel/src/immcad_api/policy/document_compilation_rules.py backend-vercel/src/immcad_api/services/document_package_service.py backend-vercel/src/immcad_api/api/routes/documents.py backend-vercel/src/immcad_api/services/record_builders/__init__.py backend-vercel/src/immcad_api/services/record_builders/ircc_application.py` -> pass
  - `npm --prefix frontend-web run test -- --run tests/chat-shell.ui.test.tsx tests/chat-shell.contract.test.tsx tests/document-compilation.contract.test.tsx` -> `32 passed`
  - `npm --prefix frontend-web run lint -- --file components/chat/related-case-panel.tsx --file lib/api-client.ts` -> pass
  - `npm --prefix frontend-web run typecheck` -> pass
  - `PYTHONPATH=src uv run python scripts/validate_backend_vercel_source_sync.py` -> pass
  - `make test-document-compilation` -> `168 passed`
  - `make docs-audit` -> pass (`[docs-maintenance] audited files: 80`)
  - `PYTHONPATH=src uv run pytest -q tests/test_doc_maintenance.py` -> `13 passed`
