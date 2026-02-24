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
  - add missing `## Review` stubs for Framework Usage Audit and Rights Matrix task blocks,
  - remove duplicate Source Policy Handoff Audit block.
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
