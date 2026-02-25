# Production Finalization Go-Live Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Close the remaining production blockers, redeploy backend and frontend safely, and complete a verifiable go-live readiness sign-off for IMMCAD.

**Architecture:** Production traffic should flow through `frontend-web` (Next.js on Vercel) to `backend-vercel` (`/api/index.py` -> FastAPI in `src/immcad_api`). Legal-source rights and export/download behavior are controlled by source registry + source policy config and enforced in backend case-search/export routes.

**Tech Stack:** Vercel CLI, Next.js, FastAPI, Python 3.11/3.12 runtime packaging, GitHub Actions, pytest, Ruff, Makefile quality gates.

---

## Verified State (2026-02-25)

- No open PRs: PR `#33` is merged (`2026-02-25T18:16:36Z`).
- Latest frontend production deploy is healthy (`dpl_9YbaotuCWvMXptmWS3x4TPo6tTn8`, `2026-02-25 01:29:16 UTC`).
- Latest backend production deploy attempt failed (`dpl_G7S9EGK8p2DgXv7jscjqYvynwFxc`, `2026-02-25 01:32:31 UTC`).
- Latest backend successful production deploy is older (`dpl_7q6JDuNMy8wefcBVxns76VV4hbho`, `2026-02-25 00:41:36 UTC`).
- Backend Vercel failure cause is confirmed: invalid prebuilt function runtime `python3.11` in `backend-vercel/.vercel/output/functions/index.func/.vc-config.json`.
- Export host validation regression is fixed in both runtime paths (`src/immcad_api/...` and `backend-vercel/src/immcad_api/...`) with regression tests.
- Runtime/quality verification is green for touched production-safety paths (`pytest`, `ruff`, source-registry sync validators).
- Active backend/frontend aliases still resolve to READY deployments.
- Fresh backend/frontend redeploy attempts were blocked by Vercel free-plan deployment quota (`api-deployments-free-per-day`).
- Live smoke checks currently confirm `/healthz` availability; authenticated endpoints require valid production bearer tokens that are not present in this local environment.

## Remaining Blockers Before Go-Live Sign-Off

1. Backend/frontend redeploy completion after quota reset
- Scope: `backend-vercel/.vercel/output/functions/index.func/.vc-config.json`, backend deploy process
- Problem: source deploy commands are currently blocked by plan quota even though config/runtime hardening is complete.
- Fix direction:
  - Wait for quota window reset.
  - Redeploy backend and frontend from source (no stale prebuilt artifacts).
- Validation:
  - `vercel inspect <new-backend-deployment-url>` and `vercel inspect <new-frontend-deployment-url>` show `READY`
  - New deployment timestamps are newer than `2026-02-25 01:32:31 UTC`

2. Authenticated production smoke verification
- Scope: `/api/chat`, `/api/search/cases`, `/ops/metrics`, export flow
- Problem: local environment currently lacks valid production bearer token(s), so only unauthenticated checks can be executed from this workspace.
- Fix direction:
  - Run smoke with valid production token in a secure shell/session.
  - Capture endpoint evidence and trace IDs.
- Validation:
  - `/healthz` -> `200`
  - `/ops/metrics` -> `200` with token
  - `/api/chat` and `/api/search/cases` -> `200` with token

3. Typed-gate scope decision
- Scope: quality gate policy (`mypy` coverage breadth)
- Problem: current mypy gate remains narrowly scoped by design.
- Fix direction:
  - Explicitly accept scoped mypy for this release, or
  - schedule/execute broader typing expansion as immediate follow-up.
- Validation:
  - Decision recorded in release notes/known issues with owner + due date.

## Execution Status

- Completed:
  - Export host validation fix + regressions (`tests/test_export_policy_gate.py`).
  - Backend deploy hardening (`backend-vercel/.python-version`, `.vercelignore`, hygiene checks, deploy config tests).
  - India->Canada runtime prompt migration (`config/prompts.yaml` compatibility text + runtime prompt files already Canada-safe).
- Pending:
  - Quota-unblocked redeploy
  - Token-authenticated smoke pass
  - Final go/no-go sign-off

## Step-by-Step Execution Plan

### Task 1: Sync to merged main and create a release-fix branch

**Files:** none (git only)

1. Checkout and sync:
```bash
git checkout main
git pull --ff-only origin main
git checkout -b fix/prod-final-export-host-and-backend-redeploy
```
2. Confirm tree is clean:
```bash
git status --short
```

### Task 2: Patch export host validation for official subdomains

**Files:**
- Modify: `src/immcad_api/api/routes/cases.py`
- Modify: `backend-vercel/src/immcad_api/api/routes/cases.py`
- Modify: `tests/test_export_policy_gate.py`

1. Implement host validation that allows only:
- exact host match, or
- a dot-bounded subdomain of the configured host (e.g., `www.decisions.scc-csc.ca`)

2. Add regression test(s):
- one accepted `www.*` official URL/redirect case
- one rejected sibling/attacker host case (e.g., `evildecisions.scc-csc.ca.example.com`)

3. Run focused tests:
```bash
uv run pytest -q tests/test_export_policy_gate.py tests/test_api_scaffold.py
```

### Task 3: Re-run backend policy/runtime gates (fast path)

**Files:** none (verification)

1. Validate key backend behavior and policy config:
```bash
uv run pytest -q tests/test_settings.py tests/test_source_policy.py tests/test_case_search_service.py tests/test_official_case_law_client.py
```
2. Validate registry and backend-vercel sync:
```bash
make source-registry-validate
make backend-vercel-sync-validate
```

### Task 4: Fix backend deploy artifact/runtime packaging path

**Files:**
- Inspect/update generated artifact: `backend-vercel/.vercel/output/functions/index.func/.vc-config.json`
- (Process) backend deploy workflow / CLI usage

1. Decide deploy mode (recommended: explicit and reproducible):
- `Option A (preferred if using prebuilt)`: regenerate backend prebuilt output locally, verify runtime, then deploy prebuilt.
- `Option B`: deploy from source path without relying on stale `.vercel/output`.

2. Before deploy, verify runtime in prebuilt output (if present):
```bash
rg -n '"runtime": "python3\\.[0-9]+"' backend-vercel/.vercel/output/functions/index.func/.vc-config.json
```

3. Deploy backend and capture URL:
```bash
vercel deploy backend-vercel --prod --yes
```
or (if intentionally using fresh prebuilt output)
```bash
cd backend-vercel && vercel build --prod && vercel deploy --prebuilt --prod --yes
```

4. Verify backend deployment:
```bash
vercel inspect <backend-deployment-url> --format=json
vercel inspect <backend-deployment-url> --logs
```

### Task 5: Backend post-deploy smoke (production endpoint)

**Files:** none (runtime validation)

1. Health check:
```bash
curl -fsS https://<backend-domain>/healthz
```
2. Ops metrics (with bearer token if configured):
```bash
IMMCAD_API_BASE_URL=https://<backend-domain> IMMCAD_API_BEARER_TOKEN=<token> make ops-alert-eval
```
3. Case-search smoke:
```bash
IMMCAD_API_BASE_URL=https://<backend-domain> IMMCAD_API_BEARER_TOKEN=<token> make canlii-live-smoke
```

### Task 6: Frontend redeploy after backend verification

**Files:**
- Env/config in Vercel project for `frontend-web` (external)
- Optional docs/env references if values changed

1. Confirm frontend env vars point to correct backend (`IMMCAD_API_BASE_URL`, `NEXT_PUBLIC_IMMCAD_API_BASE_URL` semantics per `frontend-web/README.md`).
2. Deploy frontend:
```bash
vercel deploy frontend-web --prod --yes
```
3. Verify frontend deployment:
```bash
vercel inspect <frontend-deployment-url> --format=json
```

### Task 7: End-to-end production verification and sign-off

**Files:** none (verification + docs/task update)

1. Verify chat, case search, and export UX manually in production UI:
- Chat returns grounded/citation-bearing response.
- Related case search returns official Canadian cases.
- Export PDF succeeds for allowed official source.
- Export is blocked with clear message for disallowed source/policy.

2. Confirm CI state for the release-fix PR:
```bash
gh pr checks <new-pr-number>
```

3. Update tracking docs:
- `tasks/todo.md` (mark completed items + capture evidence)
- Optional: docs/runbook entries if deploy process changed

## Rollback / Safe Recovery

1. If backend redeploy fails:
- Keep current frontend on existing backend alias.
- Re-promote last known good backend deployment (the most recent `READY` deployment) and re-verify `/healthz`.

2. If frontend redeploy fails:
- Keep backend live, re-promote previous frontend deployment alias, and verify `/api/chat` proxy connectivity.

3. If export regression fix causes unintended widening:
- Disable export path usage operationally (or temporarily disable export in UI) while keeping search/chat live.
- Revert the host-check patch and redeploy backend.

## Production Readiness Exit Criteria

- Backend production deployment is `READY` and newer than the last failed backend attempt.
- Frontend production deployment is `READY` and wired to the verified backend.
- Export host validation regression is fixed with regression tests passing.
- Source-policy/registry validators pass.
- CI checks for the release-fix PR are green.
- India-era references are triaged (runtime-facing fixed; legacy/docs explicitly labeled or scheduled).
