# Cloud-Only Deployment Runbook (2026-02-27)

## Purpose

Operate IMMCAD with zero dependency on VPS, Codespaces uptime, or origin tunnels.

Canonical production topology:

- Frontend: `frontend-web` Cloudflare Worker (`immcad-frontend-web`)
- Backend: `backend-cloudflare` native Python Worker (`immcad-backend-native-python`)
- Frontend server-side proxy target: backend Worker `workers.dev` URL
- Secrets: Cloudflare Worker secrets (managed via GitHub Actions + Wrangler)

Current free-tier constraints validated:

- Native worker bundle gzip size must stay under 3 MiB.
- IMMCAD native runtime now deploys at ~2.34 MiB gzip after SDK slimming.

## Required GitHub Secrets

- `CLOUDFLARE_API_TOKEN`
- `CLOUDFLARE_ACCOUNT_ID`
- `IMMCAD_API_BEARER_TOKEN`
- `GEMINI_API_KEY`
- Optional: `CANLII_API_KEY`, `REDIS_URL`

## Standard CI Deploy Path

Backend deploy workflow (auto on main for backend/runtime paths, and manual):

- `.github/workflows/cloudflare-backend-native-deploy.yml`

Frontend deploy workflow (auto on main for frontend paths, and manual):

- `.github/workflows/cloudflare-frontend-deploy.yml`

## Manual Deployment Commands (Repo-Only)

From repo root:

```bash
make cloudflare-env-validate
make backend-cf-native-sync
make backend-cf-native-secrets-sync
make backend-cf-native-deploy
npm run cf:build --prefix frontend-web
npx --yes wrangler@4.69.0 deploy --config frontend-web/wrangler.jsonc
```

## Post-Deploy Smoke Checks

```bash
curl -fsS https://immcad-backend-native-python.optivoo-edu.workers.dev/healthz

curl -sS -D - -o /tmp/immcad-chat.out \
  -X POST https://immcad.arkiteto.dpdns.org/api/chat \
  -H 'content-type: application/json' \
  --data '{"session_id":"smoke-001","message":"hi"}' | sed -n '1,20p'

curl -sS -D - -o /tmp/immcad-search.out \
  -X POST https://immcad.arkiteto.dpdns.org/api/search/cases \
  -H 'content-type: application/json' \
  --data '{"query":"Express Entry","jurisdiction":"ca"}' | sed -n '1,20p'

curl -sS -D - -o /tmp/immcad-research.out \
  -X POST https://immcad.arkiteto.dpdns.org/api/research/lawyer-cases \
  -H 'content-type: application/json' \
  --data '{"session_id":"smoke-002","matter_summary":"Federal Court procedural fairness"}' | sed -n '1,20p'
```

## Secret State Verification (Cloudflare)

```bash
npx --yes wrangler@4.69.0 secret list --config backend-cloudflare/wrangler.toml
```

Expected baseline:

- `IMMCAD_API_BEARER_TOKEN` and `GEMINI_API_KEY` should be present.
- If `GEMINI_API_KEY` is absent, `/api/chat` serves deterministic safe fallback content (informational only).

## GitHub-Independent Deploy Path (Billing/CI Outage Safe)

From any machine with Wrangler auth, deploy directly to Cloudflare without GitHub Actions:

```bash
bash scripts/deploy_cloudflare_gemini_mvp_no_github.sh
```

Behavior:

- Verifies Wrangler auth.
- Syncs backend/frontend bearer token secrets directly to Cloudflare.
- Loads secrets from `.env` first, then legacy env artifacts (`backend-vercel/.env.production.vercel`, `ops/runtime/.env.backend-origin`) when present.
- Requires a real `GEMINI_API_KEY` (fails fast when placeholder or missing in Cloudflare).
- Requires `IMMCAD_API_BEARER_TOKEN` to be provided (fails fast to prevent accidental token rotation).
- Set `ALLOW_GENERATE_BEARER_TOKEN=true` only for intentional token rotation events.

## Historical Fallback Note

Cloudflare backend proxy + named tunnel workflows are retained for emergency rollback only and are not the canonical production path.
