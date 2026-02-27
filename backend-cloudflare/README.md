# Backend Cloudflare Migration Scaffold

This directory contains Cloudflare backend runtime and fallback proxy artifacts.

## Current Scope
- Canonical production path: Cloudflare-native backend runtime via Python Worker (`src/entry.py`, `wrangler.toml`, `pyproject.toml`).
- Historical emergency fallback: Cloudflare Worker edge proxy (`src/worker.ts`, `wrangler.backend-proxy.jsonc`).

## Artifacts
- `backend-cloudflare/src/worker.ts`: request proxy Worker with strict path allowlist.
- `backend-cloudflare/wrangler.backend-proxy.jsonc`: Wrangler config for the backend proxy Worker.
- `backend-cloudflare/Dockerfile`: container image definition for backend runtime spike testing.
- `backend-cloudflare/src/entry.py`: Python Worker entrypoint bridging to FastAPI ASGI app.
- `backend-cloudflare/wrangler.toml`: native Python Worker runtime config (`python_workers` compatibility flag).
- `backend-cloudflare/pyproject.toml`: native Python Worker dependency + toolchain configuration.

## Why This Helps
- Removes dependency on VPS/temp machine uptime and origin tunnels for normal production operation.
- Makes deployment reproducible from repository + Cloudflare + GitHub Actions.
- Keeps an emergency rollback path available without coupling day-to-day ops to it.

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
- Native worker deploy workflow: `.github/workflows/cloudflare-backend-native-deploy.yml` (push + manual trigger).
- Workflow syncs runtime secrets to Cloudflare Worker before deploy.
- Backend proxy workflow remains available for emergency fallback and is scoped to proxy-specific files.
- Keep `/ops/*` auth and existing application-level policy controls enabled in the backend.
