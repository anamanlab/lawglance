# Backend Cloudflare Migration Scaffold

This directory contains migration artifacts for moving IMMCAD backend traffic onto Cloudflare in a staged, low-risk way.

## Current Scope
- Stage 1 (implemented here): Cloudflare Worker edge proxy in front of the existing backend origin.
- Stage 2 (in progress): Cloudflare-native backend runtime scaffold via Python Workers (`src/entry.py`, `wrangler.toml`, `pyproject.toml`) with dedicated deploy workflow.

## Artifacts
- `backend-cloudflare/src/worker.ts`: request proxy Worker with strict path allowlist.
- `backend-cloudflare/wrangler.backend-proxy.jsonc`: Wrangler config for the backend proxy Worker.
- `backend-cloudflare/Dockerfile`: container image definition for backend runtime spike testing.
- `backend-cloudflare/src/entry.py`: Python Worker entrypoint bridging to FastAPI ASGI app.
- `backend-cloudflare/wrangler.toml`: native Python Worker runtime config (`python_workers` compatibility flag).
- `backend-cloudflare/pyproject.toml`: native Python Worker dependency + toolchain configuration.

## Why This Helps
- Moves ingress and edge security controls to Cloudflare immediately.
- Avoids a risky all-at-once backend runtime rewrite.
- Preserves existing API behavior while we complete backend architecture POC work.

## Local Commands
```bash
# Build backend runtime container spike image
docker build -f backend-cloudflare/Dockerfile -t immcad-backend-spike:local .

# Deploy edge proxy worker (requires Cloudflare credentials)
npx --yes wrangler@4.68.1 deploy --config backend-cloudflare/wrangler.backend-proxy.jsonc

# Free-plan readiness preflight (frontend + proxy bundle checks, native status report)
cd ..
make cloudflare-free-preflight

# Native Python Worker local/dev toolchain (requires uv)
cd ..
bash scripts/sync_backend_cloudflare_native_source.sh

cd backend-cloudflare
uv sync --dev
uv run pywrangler dev

# or via Makefile helpers
cd ..
make backend-cf-native-dev

# Native Python Worker deploy
make backend-cf-native-deploy
```

`make backend-cf-native-deploy` automatically syncs source/config/data into
`backend-cloudflare/` before deployment.

Optional latency canary after deploy:

```bash
export IMMCAD_API_BASE_URL=https://<native-worker-domain>
export IMMCAD_API_BEARER_TOKEN=<token>
REQUESTS=20 CONCURRENCY=5 MAX_P95_SECONDS=2.5 make backend-cf-perf-smoke
```

Direct commands:

```bash
cd ..
bash scripts/sync_backend_cloudflare_native_source.sh

cd backend-cloudflare
uv sync --dev
uv run pywrangler deploy
```

## Required Cloudflare Secrets/Vars
- `CLOUDFLARE_API_TOKEN`
- `CLOUDFLARE_ACCOUNT_ID`
- `IMMCAD_BACKEND_ORIGIN` (GitHub Actions secret used to inject `BACKEND_ORIGIN` at deploy time)
- Optional edge proxy runtime tunables:
  - `BACKEND_REQUEST_TIMEOUT_MS` (default `15000`, bounded `1000..60000`)
  - `BACKEND_RETRY_ATTEMPTS` (default `1`, bounded `0..2`, idempotent methods only)

## Production Notes
- Stage 1 proxy remains transitional until native Python Worker canary validation passes.
- Native worker deploy workflow: `.github/workflows/cloudflare-backend-native-deploy.yml` (manual trigger).
- Current blocker from live canary attempt: Cloudflare script bundle-size limit (`code: 10027`) on free plan for this backend package size.
- Backend proxy workflow now runs a free-plan readiness gate (`scripts/check_cloudflare_free_plan_readiness.sh`) before deploy.
- Keep `/ops/*` auth and existing application-level policy controls enabled in the backend.
