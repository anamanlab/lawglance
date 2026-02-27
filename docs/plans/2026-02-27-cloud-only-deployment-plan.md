# Cloud-Only Deployment Baseline Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Remove VPS/temp-machine runtime dependency and make IMMCAD deployable end-to-end from repo + Cloudflare + GitHub Actions only.

**Architecture:** Frontend runs on Cloudflare Workers (OpenNext) and proxies `/api/*` to Cloudflare-native backend Python Worker over HTTPS (`workers.dev`). Backend secrets are managed in Cloudflare Worker secrets and synchronized from GitHub Secrets during CI deploy.

**Tech Stack:** Cloudflare Workers, Wrangler, Python Workers (`pywrangler`), GitHub Actions, Next.js/OpenNext, FastAPI.

---

## Cloudflare Official References Used

- Workers limits (script size / plan constraints): https://developers.cloudflare.com/workers/platform/limits/
- Service bindings (worker-to-worker best practice): https://developers.cloudflare.com/workers/runtime-apis/bindings/service-bindings/
- Wrangler environments/config behavior: https://developers.cloudflare.com/workers/wrangler/configuration/
- Deploying Workers with GitHub Actions: https://developers.cloudflare.com/workers/ci-cd/external-cicd/github-actions/
- Workers secrets management: https://developers.cloudflare.com/workers/configuration/secrets/
- Python Workers: https://developers.cloudflare.com/workers/languages/python/

## Task 1: Cloud-only backend deployment pipeline

**Files:**
- Modify: `.github/workflows/cloudflare-backend-native-deploy.yml`
- Test: `tests/test_cloudflare_backend_native_deploy_workflow.py`

**Steps:**
1. Add `push` trigger paths for backend runtime/config changes.
2. Require production provider/runtime secrets in workflow preflight.
3. Sync backend worker secrets (`wrangler secret put`) in workflow before deploy.
4. Update workflow contract tests.

## Task 2: Deterministic backend Worker hardened vars

**Files:**
- Modify: `backend-cloudflare/wrangler.toml`
- Modify: `scripts/validate_cloudflare_env_configuration.py`
- Test: `tests/test_validate_cloudflare_env_configuration.py`

**Steps:**
1. Add hardened runtime vars required by backend settings in production.
2. Add validator checks for cloud-only baseline and forbidden legacy fallback default.
3. Add/adjust unit tests for new validation behavior.

## Task 3: Frontend upstream migration to backend native Worker

**Files:**
- Modify: `frontend-web/wrangler.jsonc`
- Verify: live `/api/chat`, `/api/search/cases`, `/api/research/lawyer-cases`, `/api/export/cases/approval`

**Steps:**
1. Set `IMMCAD_API_BASE_URL` to backend native Worker URL.
2. Remove production `IMMCAD_API_BASE_URL_FALLBACK` default.
3. Deploy frontend Worker and verify API routes.

## Task 4: Ops and docs baseline update

**Files:**
- Modify: `docs/development-environment.md`
- Create: `docs/release/cloud-only-deployment-runbook-2026-02-27.md`
- Modify: `tasks/todo.md`

**Steps:**
1. Mark backend native as canonical production path.
2. Demote proxy/tunnel flow to historical emergency fallback.
3. Add cloud-only runbook with CI and manual fallback deployment commands.
4. Record verification results in `tasks/todo.md`.

## Task 5: Verification and deployment evidence

**Verification commands:**
- `./scripts/venv_exec.sh pytest -q tests/test_cloudflare_backend_native_deploy_workflow.py tests/test_cloudflare_backend_proxy_deploy_workflow.py tests/test_validate_cloudflare_env_configuration.py`
- `./scripts/venv_exec.sh python scripts/validate_cloudflare_env_configuration.py`
- `npm run test --prefix frontend-web -- tests/backend-proxy.contract.test.ts tests/server-runtime-config.contract.test.ts`
- `npm run typecheck --prefix frontend-web`
- `npm run lint --prefix frontend-web`

**Deployment commands:**
- `make backend-cf-native-secrets-sync`
- `make backend-cf-native-deploy`
- `npm run cf:build --prefix frontend-web`
- `npx wrangler@4.68.1 deploy --config frontend-web/wrangler.jsonc`

**Live smoke checks:**
- `GET /healthz` on backend native Worker
- `POST /api/chat` via frontend
- `POST /api/search/cases` via frontend
- `POST /api/research/lawyer-cases` via frontend
- `POST /api/export/cases/approval` via frontend
