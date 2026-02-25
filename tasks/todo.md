# Review Evidence - 2026-02-25 - API/DOC Contract Alignment

- Updated API contract docs in `docs/architecture/api-contracts.md`:
  - `/api/search/cases` result schema now includes `source_id` and `document_url`.
  - Added `/api/export/cases` request contract with `user_approved`.
  - Added missing-approval behavior example (`403 POLICY_BLOCKED`, `policy_reason=source_export_user_approval_required`).
- Synced README contract notes in:
  - `src/immcad_api/README.md`
  - `backend-vercel/src/immcad_api/README.md`
  - Clarified explicit rejection when `user_approved` is missing/false.
- Verification:
  - `./scripts/validate_architecture_docs.sh` -> pass.
  - `make quality` -> pass (`ruff check`, `pytest -q` with `317 passed`, plus architecture/docs/source-sync/legal-review/domain-leak/jurisdiction/repository-hygiene checks).

---

# Task Plan - 2026-02-25 - Track G Doc-Maintenance Closure

## Current Focus
- Close remaining docs-maintenance reliability contracts so Track G can be marked complete with evidence.

## Plan
- [x] Harden `scripts/doc_maintenance/validator.py` to report explicit read errors for cross-file heading anchor validation failures.
- [x] Add regression tests in `tests/test_doc_maintenance.py` for:
  - [x] git metadata timeout fallback behavior in audit analysis.
  - [x] TOC generation idempotence and no self-reference drift.
  - [x] cross-file anchor read-error surfacing contract.
- [x] Run targeted verification:
  - [x] `./scripts/venv_exec.sh pytest -q tests/test_doc_maintenance.py`
  - [x] `./scripts/venv_exec.sh ruff check scripts/doc_maintenance tests/test_doc_maintenance.py`
- [x] Update Track G checklist status and add Review evidence.

## Review
- Implemented cross-file anchor read error surfacing in `scripts/doc_maintenance/validator.py`:
  - `_validate_file_anchor` now returns `(is_valid, error)` instead of swallowing file-read failures,
  - `validate_relative_link` now emits a `medium` `link` issue when anchor validation fails due unreadable target files.
- Added regression tests in `tests/test_doc_maintenance.py`:
  - `test_analyze_markdown_file_handles_git_timeout_without_failing_analysis`,
  - `test_inject_toc_is_idempotent_after_first_rewrite`,
  - `test_validate_relative_link_reports_cross_file_anchor_read_error`.
- Fixed TOC replacement idempotence drift in `scripts/doc_maintenance/optimizer.py` by normalizing one blank line between TOC and next section during replacement.
- Verification:
  - `./scripts/venv_exec.sh pytest -q tests/test_doc_maintenance.py` -> `13 passed`
  - `./scripts/venv_exec.sh ruff check scripts/doc_maintenance tests/test_doc_maintenance.py` -> pass

---

# Task Plan - 2026-02-25 - Case Law Resilience + User-Approved PDF Retrieval

## Current Focus
- Improve case-law research resilience so CanLII acts as an optional accelerator (not a hard dependency) and enforce explicit user approval before any case PDF export/download.

## Plan
- [x] Add failing tests for case-search resilience behavior:
- [x] Official source empty-result fallback should attempt CanLII and return CanLII results when available.
- [x] CanLII failures should not block case search when official sources returned a valid response (including empty).
- [x] Add failing tests for export approval gate behavior:
- [x] `/api/export/cases` must reject requests that do not include explicit user approval.
- [x] Existing export policy/validation tests should continue to pass when user approval is present.
- [x] Implement backend changes in `src/immcad_api`:
- [x] Update `CaseSearchService` fallback logic to keep official search as primary and use CanLII as non-blocking fallback when official returns no results.
- [x] Extend case-search result metadata to support downstream export workflows (`source_id` + `document_url`).
- [x] Enforce explicit user approval in `CaseExportRequest` + `build_case_router` export handler before download.
- [x] Mirror all changed backend runtime sources into `backend-vercel/src/immcad_api` and keep file parity.
- [x] Run verification:
- [x] `scripts/venv_exec.sh pytest -q tests/test_case_search_service.py tests/test_export_policy_gate.py tests/test_api_scaffold.py`
- [x] `scripts/venv_exec.sh ruff check src/immcad_api tests`
- [x] `scripts/venv_exec.sh python scripts/validate_backend_vercel_source_sync.py`

## Review
- Added case-search resilience behavior in `src/immcad_api/services/case_search_service.py`:
  - official feeds remain primary;
  - CanLII is queried only when official search is unavailable or empty;
  - CanLII failures do not block official responses.
- Added export safety gate in `src/immcad_api/api/routes/cases.py` and `src/immcad_api/schemas.py`:
  - `CaseExportRequest.user_approved` is now required for explicit per-request consent;
  - export route blocks with `policy_reason=source_export_user_approval_required` when absent/false.
- Added export-ready metadata on case search results:
  - `source_id` and `document_url` in `CaseSearchResult`;
  - populated in `src/immcad_api/sources/canlii_client.py` and `src/immcad_api/sources/official_case_law_client.py`.
- Test coverage added/updated:
  - `tests/test_case_search_service.py`
  - `tests/test_export_policy_gate.py`
  - `tests/test_canlii_client.py`
  - `tests/test_official_case_law_client.py`
- Verification evidence:
  - `scripts/venv_exec.sh pytest -q tests/test_case_search_service.py tests/test_export_policy_gate.py tests/test_api_scaffold.py tests/test_canlii_client.py tests/test_official_case_law_client.py` -> `58 passed`.
  - `scripts/venv_exec.sh ruff check src/immcad_api tests` -> pass.
  - `scripts/venv_exec.sh python scripts/validate_backend_vercel_source_sync.py` -> pass.

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
- [x] Complete Makefile hermeticity + docs-maintenance script fixes and test hardening backlog.
- [x] Run final gate: `scripts/venv_exec.sh mypy` (scope configured in `pyproject.toml`), `scripts/venv_exec.sh ruff check src/immcad_api scripts tests`, targeted pytest matrix, and `scripts/venv_exec.sh python scripts/validate_source_registry.py`.
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
- Type-check gate resolution:
  - Added `mypy` to the dev dependency group in `pyproject.toml` and refreshed `uv.lock`.
  - Installed/synced dev dependencies via `uv sync --dev`.
  - Standardized final gate on configured-scope typecheck command: `scripts/venv_exec.sh mypy`.
  - Hardened local guardrails:
    - `Makefile` `typecheck` now fails fast when `mypy` is missing instead of silently skipping.
    - `scripts/verify_dev_env.sh` now validates `mypy` availability.
  - Verification:
    - `scripts/venv_exec.sh mypy` -> pass (`Success: no issues found in 2 source files`).
    - `make typecheck` -> pass.
    - `./scripts/verify_dev_env.sh` -> pass (`0 failure(s)`).
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
- Finalization continuation:
  - Closed doc-maintenance reliability edge cases and added explicit regression coverage for git timeout fallback, TOC idempotence, and cross-file anchor read errors.
  - Hardened chat-service test contracts for non-PII audit/fallback/prompt-leak assertions on trusted/untrusted citation-domain flows.
  - Fixed lint blocker in `scripts/validate_backend_vercel_source_sync.py` (unused import) to restore full-repo Ruff pass.
  - Verification:
    - `scripts/venv_exec.sh pytest -q tests/test_api_scaffold.py tests/test_chat_service.py tests/test_canada_courts.py tests/test_ingestion_jobs.py tests/test_ops_alert_evaluator.py tests/test_doc_maintenance.py tests/test_repository_hygiene_script.py tests/test_ingestion_smoke_script.py tests/test_rate_limiters.py tests/test_prompt_compatibility.py tests/test_legacy_runtime_convergence.py` -> `96 passed`.
    - `scripts/venv_exec.sh pytest -q` -> `317 passed`.
    - `scripts/venv_exec.sh ruff check src/immcad_api scripts tests` -> pass.
    - `scripts/venv_exec.sh python scripts/validate_source_registry.py` -> pass.
    - `scripts/venv_exec.sh python scripts/validate_backend_vercel_source_sync.py` -> pass.
    - `scripts/venv_exec.sh python scripts/run_ingestion_smoke.py --output /tmp/ingestion-smoke-report.json --state-path /tmp/ingestion-smoke-state.json` -> pass.
    - `scripts/venv_exec.sh mypy` -> pass (`Success: no issues found in 2 source files`).

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
- [x] `app.py`: sanitize markdown citation fields (`title`, `pin`) and validate/allowlist URL schemes.
- [x] `src/immcad_api/policy/prompts.py`: include user question placeholder in `QA_PROMPT`.
- [x] `src/immcad_api/policy/source_policy.py`: parse YAML/JSON based on file type (default path is `.yaml`).
- [x] `legacy_api_client.py`: narrow transport exception handling and log failures.
- [x] `legacy/local_rag/lawglance_main.py`: remove module-level `basicConfig`, use module logger, add cache TTL write.

### Track D — Ingestion/Source/Policy Correctness (`P1`)
- [x] `src/immcad_api/sources/canada_courts.py`:
  - scalar text coercion in `_dict_text`,
  - dedupe recursion behavior in `_iter_json_item_dicts`,
  - catch parse/decode failures and convert to controlled validation outcome.
- [x] `scripts/scan_domain_leaks.py`: ensure fallback to root legacy file set if `legacy/local_rag` structure is missing.
- [x] `src/immcad_api/evaluation/jurisdiction.py`: remove incorrect `decisions.fca-caf.gc.ca` allow marker and clarify FCA hosting note.
- [x] `data/sources/canada-immigration/registry.json`: normalize SCC/FCA instrument text wording.
- [x] Align rights/citation policy docs and config:
  - `docs/release/source-rights-matrix.md`,
  - `config/source_policy.yaml` (CANLII_TERMS, A2AJ, REFUGEE_LAW_LAB citation flags).

### Track E — Ops Alert Evaluator + URL/Value Semantics (`P1`)
- [x] `src/immcad_api/ops/alert_evaluator.py`:
  - base URL normalization ordering in `build_metrics_url`,
  - treat bool metric values as non-numeric,
  - correct healthy/breach message semantics.
- [x] `scripts/vercel_env_sync.py`: tighten literal `\\n` trimming logic to avoid corrupting valid encoded values.
- [x] Update related tests:
  - `tests/test_ops_alert_evaluator.py` (repo-root anchored config path),
  - `tests/test_ops_alerts_workflow.py` (path anchoring + cron assertion robustness).

### Track F — Makefile Hermeticity + Guardrails (`P1`)
- [x] `Makefile`:
  - remove non-hermetic `ingestion-smoke` from mandatory `quality`,
  - add optional integration-quality target or flag-based inclusion,
  - add `TS` fail-fast guard for restore target usage,
  - pass `--environment $(ENV)` for `vercel-env-push-dry-run` if supported.
- [x] `docs/development-environment.md`: replace hardcoded restore timestamp with placeholder.

### Track G — Doc-Maintenance Reliability (`P1/P2`)
- [x] `scripts/check_repository_hygiene.sh`: explicit `git grep` exit-code branching (`0/1/other`).
- [x] `scripts/doc_maintenance/audit.py`:
  - recursive glob semantics (`**`) correctness,
  - subprocess timeout behavior and non-blocking git metadata reads,
  - prose-only word count (frontmatter/code/inlines/URLs handling).
- [x] `scripts/doc_maintenance/optimizer.py`:
  - TOC replacement normalization,
  - TOC detection via regex not plain substring,
  - prevent self-referential TOC generation.
- [x] `scripts/doc_maintenance/styler.py`:
  - skip fenced code links/line-length checks,
  - safe parsing for optional/invalid `max_line_length`.
- [x] `scripts/doc_maintenance/validator.py`:
  - guarded local-anchor file read with error reporting.

### Track H — Test Contract Hardening (`P1/P2`)
- [x] `tests/test_api_scaffold.py`:
  - assert trace header in unsupported locale/mode validation path,
  - assert disclaimer on trusted-domain-constrained response path.
- [x] `tests/test_chat_service.py`:
  - enforce non-PII audit helper on grounding failure event,
  - add disclaimer/fallback/prompt-leak checks for untrusted-domain rejection,
  - add answer/prompt-leak assertions for trusted-domain acceptance path.
- [x] `tests/test_ingestion_jobs.py`: parametrize internal runtime behavior (`development` and `internal_runtime` or equivalent).
- [x] `tests/test_rate_limiters.py`: capture correct logger namespace.
- [x] `tests/test_canada_courts.py`: assert `court_code` is preserved.
- [x] `tests/test_ingestion_smoke_script.py`: add subprocess timeout and safer payload key assertions including `second_run["succeeded"]`.
- [x] `tests/test_prompt_compatibility.py`: robust spec/loader guards, `sys.modules` registration before `exec_module`.
- [x] `tests/test_legacy_runtime_convergence.py`: avoid runtime module import side effects (`find_spec` + static symbol checks), tighten forbidden import matching.

### Track I — Documentation and Task-Plan Consistency (`P2`)
- [x] `AGENTS.md`:
  - add `tasks/` entry under project structure,
  - fix numbered workflow list nested markdown indentation.
- [x] `tasks/todo.md`:
  - [x] add missing `## Review` stubs for Framework Usage Audit and Rights Matrix task blocks.
  - [x] remove duplicate Source Policy Handoff Audit block.
- [x] `docs/architecture/09-documentation-automation.md`: clarify `docs-fix` only refreshes TOC and manual follow-up requirements.
- [x] `docs/research/README.md`: convert machine-specific absolute links to relative links.
- [x] `docs/research/canada-legal-ai-production-implementation-plan.md`:
  - heading-level hierarchy fixes,
  - terminology/provider naming fixes (`vLex` vs `Lexum/CanLII API`),
  - timeline consistency across sections,
  - abbreviation definition (`Refugee Law Lab (RLL)`),
  - remove Context7 misattribution in section title/wording,
  - explicit freshness threshold cross-reference where ambiguous.
- [x] `docs/research/canada-legal-ai-source-and-ingestion-guide.md`:
  - ensure cross-document links resolve,
  - adjust Phase 1 citation threshold framing/path to 99%,
  - add explicit Refugee Law Lab search-indexing prohibition controls.
- [x] `docs/plans/2026-02-24-canada-legal-readiness-remediation-plan.md`:
  - declare concrete test file paths for tasks,
  - canonical fetch-policy config path contract,
  - final verification gate includes type-check and added test files.

## Verification Gates (Execution Order)
- [x] Gate 1 (Tracks A-B): workflow + secret hygiene checks (`git ls-files`, workflow tests, targeted lint).
- [x] Gate 2 (Tracks C-D-E): runtime/parser/policy tests (`test_api_scaffold`, `test_chat_service`, `test_canada_courts`, `test_ingestion_jobs`, `test_ops_alert_evaluator`).
- [x] Gate 3 (Tracks F-G): tooling/doc-maint tests (`test_doc_maintenance`, script smoke checks, Makefile command sanity).
- [x] Gate 4 (Tracks H-I): remaining targeted tests + docs/task consistency validations.
- [x] Final gate: `ruff`, focused `pytest` matrix, registry validation, ingestion smoke, and any newly added conformance checks.

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
- Continuation update (Track G + Track H closure):
  - `scripts/doc_maintenance/validator.py` now reports explicit file-read errors for cross-file heading anchor validation.
  - `scripts/doc_maintenance/optimizer.py` TOC replacement now keeps stable spacing to prevent idempotence drift.
  - Added regression tests in `tests/test_doc_maintenance.py` for git metadata timeout fallback, TOC idempotence, and cross-file anchor read-error surfacing.
  - Hardened `tests/test_chat_service.py` with additional non-PII/fallback/prompt-leak assertions for trusted and untrusted citation-domain paths.
  - Verification:
    - `./scripts/venv_exec.sh pytest -q tests/test_doc_maintenance.py` -> `13 passed`
    - `./scripts/venv_exec.sh pytest -q tests/test_chat_service.py` -> `10 passed`
    - `./scripts/venv_exec.sh pytest -q tests/test_api_scaffold.py tests/test_chat_service.py tests/test_canada_courts.py tests/test_ingestion_jobs.py tests/test_ops_alert_evaluator.py tests/test_doc_maintenance.py tests/test_repository_hygiene_script.py tests/test_ingestion_smoke_script.py tests/test_rate_limiters.py tests/test_prompt_compatibility.py tests/test_legacy_runtime_convergence.py` -> `96 passed`
    - `./scripts/venv_exec.sh pytest -q` -> `317 passed`
    - `./scripts/venv_exec.sh ruff check scripts/doc_maintenance tests/test_doc_maintenance.py tests/test_chat_service.py` -> pass
    - `make -n quality` and `make -n vercel-env-push-dry-run` -> pass (command sanity).
- Track I consistency verification update:
  - Normalized AGENTS workflow nested indentation to valid markdown list structure while preserving existing guidance.
  - Verified documentation-maintenance flow still executes cleanly after doc consistency pass.
  - Verification:
    - `./scripts/venv_exec.sh python scripts/doc_maintenance/main.py --dry-run --fail-on none` -> pass (53 files audited).
    - `./scripts/venv_exec.sh pytest -q tests/test_doc_maintenance.py` -> `13 passed`.

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

# Task Plan - 2026-02-25 - Fix /api/chat 401 Bearer Auth Regression

## Current Focus
- Resolve frontend/backend bearer-token mismatch that causes `401 Missing or invalid API bearer token` on `/api/chat`.

## Plan
- [x] Add frontend runtime compatibility for backend token env alias (`API_BEARER_TOKEN`) while preserving `IMMCAD_API_BEARER_TOKEN` precedence.
- [x] Add frontend tests for server runtime token resolution and proxy authorization forwarding.
- [x] Update unauthorized UI copy to provide actionable auth/config recovery guidance.
- [x] Run targeted frontend test suite and record results.

## Review
- Implemented frontend runtime token resolution hardening in:
  - `frontend-web/lib/server-runtime-config.ts`
    - `IMMCAD_API_BEARER_TOKEN` remains primary.
    - `API_BEARER_TOKEN` now works as a compatibility fallback.
    - production mode now fails fast when neither token is configured, preventing opaque downstream 401s.
- Updated proxy misconfiguration guidance:
  - `frontend-web/lib/backend-proxy.ts` now returns a 503 config hint that names both accepted bearer token variables.
- Updated unauthorized UX action guidance:
  - `frontend-web/components/chat/constants.ts` now tells operators to configure server token env vars, not just refresh.
- Added regression coverage:
  - `frontend-web/tests/server-runtime-config.contract.test.ts` (primary token, alias fallback, production missing-token guard).
  - `frontend-web/tests/backend-proxy.contract.test.ts` (asserts `Authorization` header forwarding when token is configured).
  - `frontend-web/tests/chat-shell.contract.test.tsx` + fixture update for actionable unauthorized UI flow.
- Verification evidence:
  - `cd frontend-web && npm test -- --run tests/backend-proxy.contract.test.ts tests/server-runtime-config.contract.test.ts tests/chat-shell.contract.test.tsx` -> `3 passed files`, `11 passed tests`.
  - `cd frontend-web && npm run typecheck` -> pass.
  - `cd frontend-web && npm run lint` -> pass.
- Gap remediation pass (cross-stack):
  - Backend settings now support `IMMCAD_API_BEARER_TOKEN` with `API_BEARER_TOKEN` as compatibility alias and reject mismatched dual-variable values in:
    - `src/immcad_api/settings.py`
    - `backend-vercel/src/immcad_api/settings.py`
  - Updated ops auth misconfiguration copy to reflect canonical + alias token names in:
    - `src/immcad_api/main.py`
    - `backend-vercel/src/immcad_api/main.py`
  - Added backend regression tests for canonical token usage + mismatch rejection in:
    - `tests/test_settings.py`
  - Hardened test isolation against ambient bearer-token env vars in:
    - `tests/test_settings.py`
    - `tests/test_api_scaffold.py`
    - `tests/test_export_policy_gate.py`
  - Documentation and env-template alignment updates:
    - `.env.example`
    - `backend-vercel/.env.example`
    - `src/immcad_api/README.md`
    - `backend-vercel/src/immcad_api/README.md`
    - `frontend-web/README.md`
    - `docs/onboarding/developer-onboarding-guide.md`
    - `docs/architecture/api-contracts.md`
    - `docs/architecture/arc42-overview.md`
    - `docs/features/chat-api-scaffold-risk-review.md`
  - Additional verification:
    - `./scripts/venv_exec.sh pytest -q tests/test_settings.py tests/test_api_scaffold.py tests/test_export_policy_gate.py` -> `103 passed`.
    - `./scripts/venv_exec.sh ruff check src/immcad_api/settings.py src/immcad_api/main.py tests/test_settings.py tests/test_api_scaffold.py tests/test_export_policy_gate.py` -> pass.
    - `./scripts/venv_exec.sh python scripts/validate_backend_vercel_source_sync.py` -> pass.

---

# Task Plan - 2026-02-25 - Priority Remediation from Code Review

## Current Focus
- Implement top-priority reliability/security fixes identified in code review for auth hardening and official case-search behavior.

## Plan
- [x] Harden runtime environment detection so hardened safeguards engage when `NODE_ENV=production` or `VERCEL_ENV=production` even if `ENVIRONMENT` is omitted.
- [x] Make official case client fail closed when requested court sources are not configured, so service fallback paths activate.
- [x] Remove SCC over-penalization and expand immigration signal patterns to avoid dropping relevant SCC matches.
- [x] Reduce request-tail latency by parallelizing official source fetch/parse calls per request.
- [x] Add/adjust Python + frontend tests and run lint/type/test/sync validation.

## Review
- Runtime hardening updates:
  - `src/immcad_api/settings.py` and `backend-vercel/src/immcad_api/settings.py` now infer runtime environment from explicit `ENVIRONMENT` first, then `VERCEL_ENV`/`NODE_ENV` fallbacks.
  - `frontend-web/lib/server-runtime-config.ts` now uses hardened-environment detection from `IMMCAD_ENVIRONMENT`/`ENVIRONMENT` with `VERCEL_ENV`/`NODE_ENV` inference.
  - `frontend-web/lib/backend-proxy.ts` scaffold fallback now keys off hardened environment detection instead of `NODE_ENV` only.
- Official case-search correctness updates:
  - `src/immcad_api/sources/official_case_law_client.py` now raises `SourceUnavailableError` when requested court sources are missing from registry.
  - same module now fetches source feeds in parallel with bounded worker pool (`max_workers <= 3`).
  - same module expanded immigration regex patterns and removed SCC negative score penalty that could suppress relevant results.
- Test coverage updates:
  - `tests/test_settings.py`: added `NODE_ENV`-production hardening inference and guard enforcement tests.
  - `tests/test_official_case_law_client.py`: added tests for missing-source failure and SCC asylum query retention.
  - `frontend-web/tests/server-runtime-config.contract.test.ts`: added hardened-mode enforcement when `ENVIRONMENT=production`.
  - `frontend-web/tests/backend-proxy.contract.test.ts`: updated hardened fallback control assertions.
- Verification evidence:
  - `./scripts/venv_exec.sh pytest -q tests/test_settings.py tests/test_official_case_law_client.py tests/test_case_search_service.py tests/test_api_scaffold.py tests/test_export_policy_gate.py` -> `114 passed`.
  - `cd frontend-web && npm test -- --run tests/server-runtime-config.contract.test.ts tests/backend-proxy.contract.test.ts tests/chat-shell.contract.test.tsx` -> `12 passed`.
  - `./scripts/venv_exec.sh ruff check src/immcad_api/settings.py src/immcad_api/sources/official_case_law_client.py src/immcad_api/services/case_search_service.py tests/test_settings.py tests/test_official_case_law_client.py tests/test_case_search_service.py` -> pass.
  - `cd frontend-web && npm run typecheck && npm run lint` -> pass.
  - `./scripts/venv_exec.sh python scripts/validate_backend_vercel_source_sync.py` -> pass.

---

# Task Plan - 2026-02-25 - Official Case Feed Cache + Background Refresh

## Current Focus
- Add in-process official court feed caching with TTL and stale-while-refresh behavior to cut tail latency and reduce per-request upstream dependence.

## Plan
- [x] Add TTL cache state to `OfficialCaseLawClient` keyed by source id, including stale window and background refresh scheduler.
- [x] Use cached records for fresh reads and stale fallback while asynchronous refresh runs.
- [x] Keep fallback correctness: raise `SourceUnavailableError` when no official source can be fetched.
- [x] Add regression tests for cache hit behavior and stale refresh scheduling.
- [x] Sync backend-vercel mirror and run targeted lint/test/sync verification.

## Review
- Implemented in-process official feed cache with per-source freshness tracking in:
  - `src/immcad_api/sources/official_case_law_client.py`
  - `backend-vercel/src/immcad_api/sources/official_case_law_client.py` (synced mirror)
- Added stale-while-refresh behavior with bounded background refresh scheduling while preserving fail-closed semantics when official sources are unavailable.
- Closed a subtle freshness correctness gap by tracking cache timestamps per source (not global), so partial source refreshes do not incorrectly mark all courts as fresh.
- Added runtime configuration for cache windows:
  - `OFFICIAL_CASE_CACHE_TTL_SECONDS`
  - `OFFICIAL_CASE_STALE_CACHE_TTL_SECONDS`
  in:
  - `src/immcad_api/settings.py`
  - `src/immcad_api/main.py`
  - `backend-vercel/src/immcad_api/settings.py`
  - `backend-vercel/src/immcad_api/main.py`
  - `.env.example`
  - `backend-vercel/.env.example`
- Added operator-facing cache docs in:
  - `src/immcad_api/README.md`
  - `backend-vercel/src/immcad_api/README.md`
- Added regression coverage:
  - `tests/test_official_case_law_client.py`
    - fresh cache hit avoids re-fetch
    - stale cache returns immediately and schedules refresh
    - per-source freshness guard for multi-court requests
    - direct TTL constructor guard behavior
  - `tests/test_settings.py`
    - default cache TTL values
    - invalid TTL validation cases
- Verification:
  - `./scripts/venv_exec.sh pytest -q tests/test_official_case_law_client.py tests/test_settings.py` -> `85 passed`
  - `./scripts/venv_exec.sh pytest -q tests/test_case_search_service.py tests/test_api_scaffold.py tests/test_export_policy_gate.py` -> `35 passed`
  - `./scripts/venv_exec.sh pytest -q tests/test_settings.py tests/test_official_case_law_client.py tests/test_case_search_service.py tests/test_api_scaffold.py tests/test_export_policy_gate.py` -> `120 passed`
  - `./scripts/venv_exec.sh ruff check src/immcad_api/settings.py src/immcad_api/main.py src/immcad_api/sources/official_case_law_client.py tests/test_settings.py tests/test_official_case_law_client.py` -> pass
  - `./scripts/venv_exec.sh python scripts/validate_backend_vercel_source_sync.py` -> pass
  - `cd frontend-web && npm test -- --run tests/server-runtime-config.contract.test.ts tests/backend-proxy.contract.test.ts tests/chat-shell.contract.test.tsx` -> `12 passed`
  - `cd frontend-web && npm run typecheck && npm run lint` -> pass

---

# Task Plan - 2026-02-25 - Vercel Env Sync Newline Safety Regression Guard

## Current Focus
- Lock down `scripts/vercel_env_sync.py` parsing behavior so literal `\\n` placeholder cleanup cannot corrupt valid encoded secrets/URLs.

## Plan
- [x] Add focused regression tests for `parse_env_file` literal-newline marker handling.
- [x] Validate preservation of structured values that legitimately contain `\\n` sequences.
- [x] Verify lint and full test suite stability after adding script-level tests.

## Review
- Added script regression tests in:
  - `tests/test_vercel_env_sync.py`
  - Covers:
    - collapsing pure newline markers (`\\n`, `\\n\\n`, quoted variants) to empty strings
    - preserving valid encoded values (PEM-like strings, JSON payloads, URL query values with escaped newline sequences)
    - preserving explicitly empty quoted strings
- Script parser under test:
  - `scripts/vercel_env_sync.py`
- Verification:
  - `./scripts/venv_exec.sh pytest -q tests/test_vercel_env_sync.py` -> `3 passed`
  - `./scripts/venv_exec.sh ruff check tests/test_vercel_env_sync.py scripts/vercel_env_sync.py` -> pass
  - `./scripts/venv_exec.sh pytest -q` -> `300 passed`

---

# Task Plan - 2026-02-25 - Parser Resilience + Ops Workflow Contract Hardening

## Current Focus
- Finalize production-facing parser resiliency for SCC/FC/FCA sources and harden ops workflow contract checks.

## Plan
- [x] Harden `canada_courts` scalar extraction for nested/non-string feed fields.
- [x] Add recursive dedupe behavior for JSON item traversal to prevent duplicate records from mirrored feed structures.
- [x] Convert broader parser failure modes into controlled validation outcomes.
- [x] Strengthen ops workflow tests for cron/script-path drift detection.
- [x] Run targeted + full verification, then sync backend-vercel mirror.

## Review
- Implemented parser resilience updates in:
  - `src/immcad_api/sources/canada_courts.py`
  - `backend-vercel/src/immcad_api/sources/canada_courts.py` (synced mirror)
- Key behavior changes:
  - `_dict_text` now recursively extracts nested scalar text values and avoids coercing booleans.
  - `_iter_json_item_dicts` now traverses recursively with fingerprint-based dedupe to avoid duplicate record extraction in mirrored nested structures.
  - `validate_court_source_payload` now treats `TypeError`/`ValueError` parser-shape failures as controlled `payload_parse_error` validation output.
- Added regression coverage in:
  - `tests/test_canada_courts.py`
    - nested scalar field extraction
    - recursive duplicate item dedupe
    - controlled validation on unexpected parser exceptions
  - `tests/test_ops_alerts_workflow.py`
    - cron expression assertion via regex
    - evaluator script path assertion via command pattern
  - `tests/test_ops_alert_evaluator.py`
    - `/api/` suffix normalization
    - empty-base normalization guard
- Verification:
  - `./scripts/venv_exec.sh pytest -q tests/test_canada_courts.py` -> `12 passed`
  - `./scripts/venv_exec.sh pytest -q tests/test_ops_alert_evaluator.py tests/test_ops_alerts_workflow.py` -> `12 passed`
  - `./scripts/venv_exec.sh pytest -q tests/test_ops_alert_evaluator.py tests/test_ops_alerts_workflow.py tests/test_canada_courts.py` -> `24 passed`
  - `./scripts/venv_exec.sh ruff check src/immcad_api/sources/canada_courts.py tests/test_canada_courts.py tests/test_ops_alert_evaluator.py tests/test_ops_alerts_workflow.py` -> pass
  - `./scripts/venv_exec.sh pytest -q` -> `304 passed`
  - `./scripts/venv_exec.sh python scripts/validate_backend_vercel_source_sync.py` -> pass

---

# Task Plan - 2026-02-25 - Jurisdiction FCA Domain Marker Correction

## Current Focus
- Finalize jurisdiction source-domain allowlist so FCA host validation is correct across canonical host and decisions subdomain variants.

## Plan
- [x] Replace overly specific FCA decisions marker with canonical domain marker.
- [x] Add regression test proving FCA primary host URLs are accepted.
- [x] Run lint/full tests and resync backend-vercel mirror.

## Review
- Updated FCA allow marker in:
  - `src/immcad_api/evaluation/jurisdiction.py`
  - `backend-vercel/src/immcad_api/evaluation/jurisdiction.py` (synced mirror)
- Change details:
  - Replaced `decisions.fca-caf.gc.ca` marker with `fca-caf.gc.ca` so both primary host (`www.fca-caf.gc.ca`) and decisions-subdomain URLs remain valid.
  - Clarified inline hosting note in code comments.
- Added regression coverage:
  - `tests/test_jurisdiction_evaluation.py`
    - new test verifies `_check_registry_source_domains()` accepts FCA primary host URLs.
- Verification:
  - `./scripts/venv_exec.sh pytest -q tests/test_jurisdiction_evaluation.py` -> `4 passed`
  - `./scripts/venv_exec.sh ruff check src/immcad_api/evaluation/jurisdiction.py tests/test_jurisdiction_evaluation.py src/immcad_api/sources/canada_courts.py tests/test_canada_courts.py tests/test_ops_alert_evaluator.py tests/test_ops_alerts_workflow.py` -> pass
  - `./scripts/venv_exec.sh pytest -q` -> `305 passed`
  - `./scripts/venv_exec.sh python scripts/validate_backend_vercel_source_sync.py` -> pass

---

# Task Plan - 2026-02-25 - Registry Wording Normalization + Mirror Sync

## Current Focus
- Normalize SCC/FCA registry instrument wording and keep backend-vercel mirrored assets synchronized.

## Plan
- [x] Update root registry instrument wording for SCC/FCA entries.
- [x] Sync mirrored backend-vercel registry copy.
- [x] Re-run registry validation and full test suite.

## Review
- Updated:
  - `data/sources/canada-immigration/registry.json`
  - `backend-vercel/data/sources/canada-immigration/registry.json`
- Normalization:
  - `SCC_DECISIONS` instrument -> "Supreme Court of Canada decisions feed"
  - `FCA_DECISIONS` instrument -> "Federal Court of Appeal decisions feed"
- Verification:
  - `./scripts/venv_exec.sh python scripts/validate_source_registry.py` -> pass
  - `./scripts/venv_exec.sh pytest -q tests/test_validate_source_registry.py tests/test_jurisdiction_evaluation.py tests/test_canada_courts.py` -> `20 passed`
  - `./scripts/venv_exec.sh pytest -q tests/test_backend_vercel_case_search_assets.py` -> `2 passed`
  - `./scripts/venv_exec.sh pytest -q` -> `305 passed`

---

# Task Plan - 2026-02-25 - Rights Matrix and Source Policy Flag Alignment

## Current Focus
- Eliminate policy-field naming drift and harden restricted-source rights flags to prevent production citation/export mistakes.

## Plan
- [x] Align rights-matrix field naming with runtime policy schema.
- [x] Add regression tests for restricted-source flags (`CANLII_TERMS`, `A2AJ`, `REFUGEE_LAW_LAB`).
- [x] Run targeted and full verification.

## Review
- Updated rights matrix field wording in:
  - `docs/release/source-rights-matrix.md`
  - corrected `citation_in_answers` -> `answer_citation_allowed` to match runtime policy schema.
- Added policy regression coverage in:
  - `tests/test_source_policy.py`
  - verifies `production_ingest_allowed`, `answer_citation_allowed`, and `export_fulltext_allowed` for:
    - `CANLII_TERMS`
    - `A2AJ`
    - `REFUGEE_LAW_LAB`
- Verification:
  - `./scripts/venv_exec.sh pytest -q tests/test_source_policy.py tests/test_validate_source_registry.py` -> `19 passed`
  - `./scripts/venv_exec.sh ruff check tests/test_source_policy.py` -> pass
  - `./scripts/venv_exec.sh pytest -q` -> `311 passed`

---

# Task Plan - 2026-02-25 - Repository Hygiene Script Exit-Code Contract Tests

## Current Focus
- Lock `scripts/check_repository_hygiene.sh` behavior with tests for pass/fail/error paths.

## Plan
- [x] Add regression tests for clean repo pass path.
- [x] Add regression tests for tracked `.env` hard-fail path.
- [x] Add regression tests for git command failure path (`git grep` error handling).
- [x] Run targeted and full verification.

## Review
- Added:
  - `tests/test_repository_hygiene_script.py`
- Coverage added:
  - clean git repo returns success and emits `[OK]` message
  - tracked `.env` returns failure with remediation hint
  - non-git directory returns explicit `git grep` failure path with exit code `2`
- Verification:
  - `./scripts/venv_exec.sh pytest -q tests/test_repository_hygiene_script.py` -> `3 passed`
  - `./scripts/venv_exec.sh ruff check tests/test_repository_hygiene_script.py` -> pass
  - `./scripts/venv_exec.sh pytest -q` -> `314 passed`

---

# Task Plan - 2026-02-25 - Git-Secret Adoption Planning (Repo-Scoped)

## Current Focus
- Define a production-safe `git-secret` adoption plan for IMMCAD that supports encrypted env bundles in git without replacing GitHub/Vercel platform-managed runtime secrets.

## Plan
- [x] Crawl `https://sobolevn.me/git-secret/` and extract setup/CI/CD workflow + operational caveats (GPG key management, `hide`/`reveal`, CI import flow, GPG version compatibility).
- [x] Review IMMCAD secret-handling constraints (`.gitignore`, `scripts/check_repository_hygiene.sh`, `scripts/vercel_env_sync.py`, docs, workflows/tests) to scope integration safely.
- [x] Create detailed implementation plan doc: `docs/plans/2026-02-25-git-secret-adoption-plan.md`.
- [ ] Review/approve rollout scope decision:
- [ ] `git-secret` for encrypted local/team env bundles only (recommended), while production runtime secrets remain in GitHub/Vercel secrets managers.
- [ ] Choose pilot target (recommended: `backend-vercel/.env.preview` -> `backend-vercel/.env.preview.secret`).
- [ ] Execute implementation plan in a dedicated branch/worktree with verification evidence per task.

## Review
- Planning only in this entry; no runtime/workflow code or secret-handling behavior was changed.
- Output created:
  - `docs/plans/2026-02-25-git-secret-adoption-plan.md`
- Post-review plan corrections applied:
  - replaced invalid/unsupported `git-secret-status` target suggestion with `git-secret-list` / `git-secret-changes`
  - added explicit requirement to exclude tracked `*.secret` blobs from regex plaintext secret scans to avoid false positives in `scripts/check_repository_hygiene.sh`
  - strengthened hygiene plan from `.env`-only to tracked plaintext `.env*` detection (excluding templates) and added `git check-ignore` verification for encrypted `.secret` artifacts
  - tightened CI install guidance to avoid deprecated `apt-key` snippets and to log `git-secret`/`gpg` versions for interoperability debugging
- Plan is tailored to current IMMCAD constraints:
  - preserves platform-managed production secrets policy,
  - integrates with existing repository hygiene checks and Vercel env sync workflows,
  - includes optional (gated) CI `git-secret reveal` support only if needed.
