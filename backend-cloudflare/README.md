# Backend Cloudflare Migration Scaffold

This directory contains migration artifacts for moving IMMCAD backend traffic onto Cloudflare in a staged, low-risk way.

## Current Scope
- Stage 1 (implemented here): Cloudflare Worker edge proxy in front of the existing backend origin.
- Stage 2 (planned): Replace origin with Cloudflare-native backend runtime (Containers or Python Worker path).

## Artifacts
- `backend-cloudflare/src/worker.ts`: request proxy Worker with strict path allowlist.
- `backend-cloudflare/wrangler.backend-proxy.jsonc`: Wrangler config for the backend proxy Worker.
- `backend-cloudflare/Dockerfile`: container image definition for backend runtime spike testing.

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
```

## Required Cloudflare Secrets/Vars
- `CLOUDFLARE_API_TOKEN`
- `CLOUDFLARE_ACCOUNT_ID`
- `IMMCAD_BACKEND_ORIGIN` (GitHub Actions secret used to inject `BACKEND_ORIGIN` at deploy time)

## Production Notes
- This scaffold is transitional; production cutover still requires backend runtime POC decision and canary validation.
- Keep `/ops/*` auth and existing application-level policy controls enabled in the backend.
