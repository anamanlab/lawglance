# Production Deep Audit Implementation Plan

> Status (2026-02-25): This plan contains legacy Vercel verification steps and is retained for historical traceability.
> Execute Cloudflare-first audit flow from:
> - `docs/release/pre-deploy-command-sheet-2026-02-25.md`
> - `docs/plans/2026-02-25-cloudflare-migration-plan.md`
> - `scripts/release_preflight.sh`

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Produce a zero-assumption, evidence-backed pre-deploy audit that surfaces all remaining production risks, closes high-priority gaps, and prepares a deterministic go/no-go packet for the next deploy window.

**Architecture:** This plan treats readiness as a layered system audit: release controls, runtime safety, legal-policy correctness, API behavior, frontend behavior, CI/workflow determinism, and operations. Each task generates explicit artifacts and pass/fail criteria so we can make a deployment decision without interpretation drift.

**Tech Stack:** Python/FastAPI backend (`src/immcad_api`, `backend-vercel` mirror), Next.js frontend (`frontend-web`), Cloudflare Workers + Wrangler deployments (legacy Vercel references are transitional), pytest, Ruff, mypy, repo maintenance scripts, GitHub Actions workflows.

---

### Task 1: Baseline Freeze and Audit Scope Lock

**Files:**
- Modify: `tasks/todo.md`
- Modify: `docs/release/known-issues.md`
- Create: `artifacts/release/predeploy-audit-scope-2026-02-25.md`

**Step 1: Capture current baseline state**

Run:
```bash
git status --short --branch
gh pr list --state open --json number,title,headRefName,baseRefName,updatedAt,url
```
Expected:
- Branch/tracked changes snapshot captured.
- Open PR status captured (if none, explicit `[]` recorded).

**Step 2: Snapshot deployment state for backend and frontend**

Run:
```bash
vercel --version
vercel whoami
```
Expected:
- CLI availability and authenticated account recorded.

**Step 3: Record scope boundaries and exclusions**

Write:
- What this audit includes/excludes.
- Which known concurrent edits are out of scope.
- Required evidence artifacts for sign-off.

**Step 4: Commit scope packet**

Run:
```bash
git add tasks/todo.md docs/release/known-issues.md artifacts/release/predeploy-audit-scope-2026-02-25.md
git commit -m "docs(release): lock pre-deploy deep-audit scope and evidence contract"
```

### Task 2: Deployment Path and Runtime Integrity Audit

**Files:**
- Verify: `backend-vercel/.python-version`
- Verify: `backend-vercel/vercel.json`
- Verify: `backend-vercel/.vercelignore`
- Verify: `scripts/check_repository_hygiene.sh`
- Verify/Test: `tests/test_backend_vercel_deploy_config.py`, `tests/test_repository_hygiene_script.py`

**Step 1: Validate backend deploy configuration contract**

Run:
```bash
./scripts/venv_exec.sh pytest -q tests/test_backend_vercel_deploy_config.py tests/test_repository_hygiene_script.py
bash -n scripts/check_repository_hygiene.sh
```
Expected:
- Tests pass.
- Hygiene script syntax valid.

**Step 2: Confirm no stale prebuilt artifact risks in workspace**

Run:
```bash
bash scripts/check_repository_hygiene.sh
```
Expected:
- `[OK] Repository hygiene checks passed.`

**Step 3: Validate deploy path policy decision**

Record:
- Source-based deploy command to use.
- Explicit prohibition of stale `--prebuilt` path unless freshly generated and audited.

### Task 3: Secrets and Configuration Hygiene Audit

**Files:**
- Verify: `.gitignore`, `backend-vercel/.gitignore`
- Verify: `scripts/check_repository_hygiene.sh`
- Verify: `docs/release/git-secret-runbook.md`
- Create: `artifacts/release/predeploy-secret-hygiene-2026-02-25.md`

**Step 1: Validate tracked-file secret policy**

Run:
```bash
git ls-files '.env-backups/**'
bash scripts/check_repository_hygiene.sh
```
Expected:
- No tracked backup secrets.
- Hygiene script passes.

**Step 2: Validate runtime secret manager separation**

Check docs and scripts for:
- Cloudflare/GitHub secrets as runtime source of truth.
- `git-secret` documented as optional/non-replacement flow.

**Step 3: Document unresolved secret-risk gaps**

Write:
- Remaining operational risks.
- Required owner + target date in `known-issues`.

### Task 4: Canada Domain and Legal Safety Audit

**Files:**
- Verify: `src/immcad_api/policy/prompts.py`
- Verify: `config/prompts.yaml`
- Verify/Test: `scripts/scan_domain_leaks.py`, `tests/test_domain_leak_scanner.py`
- Verify: `config/source_policy.yaml`, `data/sources/canada-immigration/registry.json`
- Create: `artifacts/release/predeploy-legal-safety-2026-02-25.md`

**Step 1: Run domain leak guardrails**

Run:
```bash
./scripts/venv_exec.sh python scripts/scan_domain_leaks.py
./scripts/venv_exec.sh pytest -q tests/test_domain_leak_scanner.py
```
Expected:
- No runtime-domain leaks.
- Scanner behavior deterministic in dirty worktree.

**Step 2: Validate source policy + registry consistency**

Run:
```bash
./scripts/venv_exec.sh python scripts/validate_source_registry.py
./scripts/venv_exec.sh python scripts/validate_backend_vercel_source_sync.py
```
Expected:
- Source registry and backend mirror are in sync.

**Step 3: Validate legal-safety posture**

Run:
```bash
./scripts/venv_exec.sh python scripts/generate_jurisdiction_eval_report.py
./scripts/venv_exec.sh python scripts/run_jurisdictional_test_suite.py
```
Expected:
- Jurisdiction pass with explicit score and citation coverage artifact.

### Task 5: Backend API and Export Policy Deep Audit

**Files:**
- Verify: `src/immcad_api/main.py`, `src/immcad_api/settings.py`
- Verify: `src/immcad_api/api/routes/cases.py`, `src/immcad_api/services/chat_service.py`
- Verify/Test: `tests/test_api_scaffold.py`, `tests/test_chat_service.py`, `tests/test_export_policy_gate.py`, `tests/test_settings.py`
- Create: `artifacts/release/predeploy-backend-api-2026-02-25.md`

**Step 1: Run targeted backend safety tests**

Run:
```bash
./scripts/venv_exec.sh pytest -q \
  tests/test_api_scaffold.py \
  tests/test_chat_service.py \
  tests/test_export_policy_gate.py \
  tests/test_settings.py
```
Expected:
- API scaffold, auth, prompt safety, and export-policy gates pass.

**Step 2: Validate unresolved API risks**

Review and document:
- Client-asserted `user_approved` limitation.
- Any remaining auth edge cases and policy reason consistency.

### Task 6: Frontend Contract and Production Behavior Audit

**Files:**
- Verify: `frontend-web/components/chat/chat-shell-container.tsx`
- Verify/Test: `frontend-web/tests/*.test.ts*`
- Verify: `frontend-web/lib/server-runtime-config.ts`
- Create: `artifacts/release/predeploy-frontend-2026-02-25.md`

**Step 1: Run frontend verification serially**

Run:
```bash
npm run build --prefix frontend-web
npm run typecheck --prefix frontend-web
npm run test --prefix frontend-web
```
Expected:
- Build, typecheck, and contract tests pass.
- No transient `.next/types` race issues.

**Step 2: Validate user-visible production controls**

Verify in tests/code:
- Explicit “Find related cases” action model.
- Export confirmation UX.
- Scope/legal disclaimer presence.

### Task 7: CI Workflow and Release Gate Determinism Audit

**Files:**
- Verify: `.github/workflows/quality-gates.yml`
- Verify: `.github/workflows/release-gates.yml`
- Verify/Test: `tests/test_quality_gates_workflow.py`, `tests/test_release_gates_workflow.py`, `tests/test_ops_alerts_workflow.py`
- Create: `artifacts/release/predeploy-ci-determinism-2026-02-25.md`

**Step 1: Validate workflow gate tests**

Run:
```bash
./scripts/venv_exec.sh pytest -q \
  tests/test_quality_gates_workflow.py \
  tests/test_release_gates_workflow.py \
  tests/test_ops_alerts_workflow.py
```
Expected:
- Workflow contract tests pass.

**Step 2: Verify gate sequencing**

Confirm:
- Frontend build precedes frontend typecheck (or equivalent deterministic strategy).
- Source sync and legal checklist validations remain in gate path.

### Task 8: Full-System Verification and Risk Register Update

**Files:**
- Verify: `Makefile`
- Modify: `docs/release/known-issues.md`
- Modify: `docs/release/lead-engineering-readiness-audit-2026-02-25.md`
- Modify: `tasks/todo.md`

**Step 1: Run full quality gate**

Run:
```bash
make quality
make verify
```
Expected:
- Quality and verify pass; warnings captured explicitly.

**Step 2: Update known issues and decision log**

Record:
- Closed issues with evidence.
- Open issues with severity/owner/target.
- Explicit deferrals (for example mypy scope expansion).

**Step 3: Publish go/no-go packet**

Include:
- Deployment state snapshot.
- Required commands for deploy window.
- Rollback candidate deployment IDs.
- Final sign-off recommendation.

### Task 9: Deployment Window Execution Checklist (When Quota Opens)

**Files:**
- Modify: `tasks/todo.md`
- Create: `artifacts/release/deploy-window-execution-2026-02-25.md`

**Step 1: Backend deploy**

Run:
```bash
vercel --cwd backend-vercel deploy --prod --yes
```
Expected:
- READY deployment ID captured.

**Step 2: Frontend deploy (if same-SHA sync required)**

Run:
```bash
vercel --cwd frontend-web deploy --prod --yes
```
Expected:
- READY deployment ID captured.

**Step 3: Production smoke checks**

Run auth-aware checks for:
- `/healthz`
- `/ops/metrics`
- `/api/chat`
- `/api/search/cases`
- `/api/export/cases`

Expected:
- Statuses and policy behavior match hardened expectations.

**Step 4: Finalize release readiness verdict**

Criteria:
- No open P0 issues.
- Smoke checks green.
- Evidence artifacts complete.
