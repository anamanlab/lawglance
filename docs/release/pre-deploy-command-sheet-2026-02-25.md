# Pre-Deploy Command Sheet (2026-02-25)

## Purpose
Deterministic Cloudflare-first deploy sequence for frontend and backend proxy, with explicit preflight and smoke verification.

## 1) Preflight (repo + auth + hygiene)

```bash
git checkout main
git pull --ff-only origin main

git status --short
gh pr list --state open --limit 30

make release-preflight

# Optional standalone visibility into free-plan fit (frontend/proxy/native dry-run sizes)
make cloudflare-free-preflight

# Optional standalone edge-contract guard (proxy headers/error envelope/frontend compatibility)
make cloudflare-edge-contract-preflight
```

## 2) Quality Gates

```bash
make quality
make source-registry-validate
make backend-runtime-sync-validate
make cloudflare-env-validate
```

```bash
npm run build --prefix frontend-web
npm run typecheck --prefix frontend-web
npm run test --prefix frontend-web
```

## 3) Backend Proxy Deploy (Cloudflare Worker, transitional)

Set backend origin explicitly for deployment:

```bash
npx --yes wrangler@4.68.1 deploy \
  --config backend-cloudflare/wrangler.backend-proxy.jsonc \
  --var BACKEND_ORIGIN:https://backend-origin.example \
  --keep-vars
```

Verify deployment history:

```bash
npx --yes wrangler@4.68.1 deployments list \
  --config backend-cloudflare/wrangler.backend-proxy.jsonc \
  --name immcad-backend-proxy
```

## 4) Frontend Deploy (Cloudflare Worker via OpenNext)

Build and deploy:

```bash
make frontend-cf-build

npx --yes wrangler@4.68.1 deploy \
  --config frontend-web/wrangler.jsonc \
  --var IMMCAD_API_BASE_URL:https://immcad-api.arkiteto.dpdns.org \
  --var IMMCAD_ENVIRONMENT:production \
  --keep-vars
```

Verify deployment history:

```bash
npx --yes wrangler@4.68.1 deployments list \
  --config frontend-web/wrangler.jsonc \
  --name immcad-frontend-web
```

## 4b) Native Backend Canary (Manual Gate)

```bash
make backend-cf-native-sync
make backend-cf-native-deploy
```

If deploy fails with platform constraints (for example `code: 10027` size limit),
record the evidence in `docs/release/known-issues.md` and continue using proxy path.

## 5) Smoke Checks (Workers + custom domains)

```bash
export IMMCAD_API_BEARER_TOKEN='<prod-token>'
```

Backend health (custom domain):

```bash
curl -fsS https://immcad-api.arkiteto.dpdns.org/healthz
```

Backend auth-protected endpoint:

```bash
curl -fsS -X POST https://immcad-api.arkiteto.dpdns.org/api/chat \
  -H "content-type: application/json" \
  -H "authorization: Bearer ${IMMCAD_API_BEARER_TOKEN}" \
  --data '{"session_id":"prod-smoke-20260225","message":"Give one leading SCC immigration reasonableness case with citation only."}'
```

Frontend worker endpoint checks:

```bash
curl -I https://immcad-frontend-web.optivoo-edu.workers.dev

curl -fsS -X POST https://immcad-frontend-web.optivoo-edu.workers.dev/api/search/cases \
  -H "content-type: application/json" \
  -H "authorization: Bearer ${IMMCAD_API_BEARER_TOKEN}" \
  --data '{"query":"H&C reasonableness standard","limit":3}'
```

If local DNS cache is stale for custom frontend domain, verify via public resolver:

```bash
dig @1.1.1.1 +short immcad.arkiteto.dpdns.org
```

Optional backend latency canary (authenticated):

```bash
export IMMCAD_API_BASE_URL=https://immcad-api.arkiteto.dpdns.org
export IMMCAD_API_BEARER_TOKEN='<prod-token>'
REQUESTS=20 CONCURRENCY=5 MAX_P95_SECONDS=2.5 make backend-cf-perf-smoke
```

Cloudflare free-tier API quota projection check (authenticated):

```bash
export IMMCAD_API_BASE_URL=https://immcad-api.arkiteto.dpdns.org
export IMMCAD_API_BEARER_TOKEN='<prod-token>'
make ops-alert-eval
```

Full free-tier runtime validation (health + search + chat case-law citations + lawyer-research + CanLII):

```bash
export IMMCAD_FRONTEND_URL=https://immcad.arkiteto.dpdns.org
make free-tier-runtime-validate
```

Review `artifacts/ops/ops-alert-eval.json` for:
- `cloudflare_free_api_projected_daily_request_utilization_warn`
- `cloudflare_free_api_projected_daily_request_utilization_fail`

## 6) Go/No-Go Checklist

- `make release-preflight` passed from a clean worktree.
- `make cloudflare-free-preflight` passes in proxy mode and records native status (warning accepted on free tier if staying on proxy path).
- `make cloudflare-edge-contract-preflight` passes (or is already covered by `make release-preflight`) so edge/header/error contract drift is blocked before deploy.
- Backend proxy deploy is successful and points to intended origin.
- Frontend deploy is successful and serves `200` at worker URL.
- Native backend canary attempt result is recorded (success path or blocker evidence).
- `/healthz`, `/api/chat`, `/api/search/cases` return expected responses with auth token.
- Optional perf smoke passes (`make backend-cf-perf-smoke`) and p95 remains within threshold.
- Full runtime validation bundle passes (`make free-tier-runtime-validate`).
- `make ops-alert-eval` passes (or only approved warnings) and Cloudflare free-tier API request projection remains below fail threshold.
- `docs/release/known-issues.md` is updated with accepted residual risks and latest evidence.
- Rollback target versions are recorded before go-live approval.

## 7) Rollback (Cloudflare Worker versions)

List versions:

```bash
npx --yes wrangler@4.68.1 deployments list \
  --config frontend-web/wrangler.jsonc \
  --name immcad-frontend-web

npx --yes wrangler@4.68.1 deployments list \
  --config backend-cloudflare/wrangler.backend-proxy.jsonc \
  --name immcad-backend-proxy
```

Rollback to a known-good version ID:

```bash
npx --yes wrangler@4.68.1 rollback <frontend-version-id> \
  --config frontend-web/wrangler.jsonc

npx --yes wrangler@4.68.1 rollback <backend-version-id> \
  --config backend-cloudflare/wrangler.backend-proxy.jsonc
```

Re-run Section 5 smoke checks after rollback.
