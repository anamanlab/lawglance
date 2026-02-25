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
  - [ ] Backend native-runtime deploy workflow pending architecture decision (Containers vs Python Worker).
- [ ] Phase 5 production cutover: staged DNS/traffic migration with 24h and 72h observation windows and rollback criteria.
- [ ] Evidence and signoff: document results in release artifacts and update known-issues register.

## Task Plan - 2026-02-25 - Cloudflare Migration Audit

### Current Focus
- Evaluate release documentation, Cloudflare deploy configs/workflows (frontend + backend proxy), and list concrete gaps blocking production cutover.

### Plan
- [ ] Audit `docs/release/known-issues.md` to confirm existing Cloudflare migration entries describe up-to-date blockers and note any missing evidence.
- [ ] Review frontend and backend Cloudflare deploy configs/workflows for completeness (wrangler, OpenNext, GitHub Actions) and record missing steps or unpinned/pending parts.
- [ ] Compile a concise list of actionable gaps (documentation, config, automation) that must be fixed before Cloudflare migration is production-ready.

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
