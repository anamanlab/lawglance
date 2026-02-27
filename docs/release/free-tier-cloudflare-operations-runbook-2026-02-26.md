# Free-Tier Cloudflare Operations Runbook (2026-02-26)

## Purpose
Keep IMMCAD production-safe while staying on free-tier constraints:

- Cloudflare frontend Worker + backend proxy Worker
- Backend origin hosted outside Cloudflare-native Python Workers
- Named tunnel connector from origin host

This runbook defines the operational baseline and the minimal checks required for every restart/cutover.

## Free-Tier Baseline

1. Keep backend mode on proxy path (`CLOUDFLARE_BACKEND_MODE=proxy`).
2. Keep Cloudflare native backend as optional canary only (bundle-size constrained on free tier).
3. Use named tunnel host for backend origin connectivity.
4. Use platform-managed secrets, never plaintext committed secrets.

## Required Secrets (Runtime)

- Backend origin runtime:
  - `CANLII_API_KEY`
  - `IMMCAD_API_BEARER_TOKEN` (or `API_BEARER_TOKEN` alias)
  - provider keys as needed (`OPENAI_API_KEY`, `GEMINI_API_KEY`)
- Cloudflare Worker runtime:
  - only Worker-consumed secrets/vars
- CI/CD:
  - `CLOUDFLARE_API_TOKEN`
  - `CLOUDFLARE_ACCOUNT_ID`
  - `IMMCAD_API_BASE_URL`
  - `IMMCAD_FRONTEND_URL`
  - `IMMCAD_API_BEARER_TOKEN`

## Standard Runtime Lifecycle (Codespaces Recovery Mode)

Start:

```bash
make backend-cf-codespace-runtime-start
```

Health:

```bash
make backend-cf-codespace-runtime-health
```

Stop:

```bash
make backend-cf-codespace-runtime-stop
```

Targeted chat retrieval validation:

```bash
export IMMCAD_API_BASE_URL=https://immcad-api.arkiteto.dpdns.org
export IMMCAD_API_BEARER_TOKEN='<token>'
make chat-case-law-smoke
```

Full free-tier runtime validation bundle:

```bash
export IMMCAD_API_BASE_URL=https://immcad-api.arkiteto.dpdns.org
export IMMCAD_FRONTEND_URL=https://immcad.arkiteto.dpdns.org
export IMMCAD_API_BEARER_TOKEN='<token>'
make free-tier-runtime-validate
```

## Release / Deploy Safety Gates

Always run:

```bash
make release-preflight
make cloudflare-free-preflight
```

CanLII + runtime validation (live):

```bash
make canlii-key-verify
make canlii-live-smoke
make free-tier-runtime-validate
```

## Permanent Host Cutover (Still Free-Tier Compatible)

Goal: remove dependency on Codespaces uptime while preserving current Cloudflare topology.

1. Provision a stable host (free-tier capable) with persistent process supervision.
2. Install dependencies (`python`, project `.venv`, `cloudflared`).
3. Copy runtime env to host and set strict file permissions.
4. Start backend on `127.0.0.1:8002`.
5. Start `cloudflared tunnel run --token-file ...` for existing named tunnel.
6. Run:
   - `make free-tier-runtime-validate`
   - `make chat-case-law-smoke`
   - `make canlii-live-smoke`
7. Shut down Codespaces recovery runtime only after host validation passes.

No Cloudflare Worker redeploy is required if the named tunnel hostname remains unchanged.

## Secret Rotation Checklist

Rotate after any suspected exposure:

1. Rotate `CANLII_API_KEY`.
2. Rotate bearer token(s).
3. Update backend runtime env.
4. Update CI secrets.
5. Re-run:
   - `make canlii-key-verify`
   - `make free-tier-runtime-validate`

## Incident Quick Commands

```bash
curl -fsS https://immcad-api.arkiteto.dpdns.org/healthz
make backend-cf-codespace-runtime-health
make free-tier-runtime-validate
```

If runtime is down:

```bash
make backend-cf-codespace-runtime-stop
make backend-cf-codespace-runtime-start
make backend-cf-codespace-runtime-health
```

## Incident Pattern: `/api/chat` returns `530` (`error code: 1033`)

This indicates Cloudflare cannot resolve the configured named tunnel host for backend origin.

Confirm signature:

```bash
curl -sS -D - -o /tmp/immcad-chat.out \
  -X POST https://immcad.arkiteto.dpdns.org/api/chat \
  -H 'content-type: application/json' \
  --data '{"message":"ping","session_id":"incident-check"}' \
  | sed -n '1,20p'
head -n 3 /tmp/immcad-chat.out
```

If body contains `error code: 1033`, recover in this order:

1. Restore runtime env + tunnel token on origin host.
2. Restart named-tunnel runtime.
3. Re-run health/smoke checks.

```bash
make backend-origin-env-recover-from-vercel
# if needed: export TUNNEL_TOKEN='...'; printf '%s' "$TUNNEL_TOKEN" > /tmp/immcad_named_tunnel.token; chmod 600 /tmp/immcad_named_tunnel.token
make backend-cf-codespace-runtime-start
make backend-cf-codespace-runtime-health
```

If tunnel recovery is blocked and legal/ops approves temporary fallback, point backend proxy origin to a known healthy backend and redeploy proxy Worker.

Required:

- update `IMMCAD_BACKEND_ORIGIN` GitHub Actions secret
- run `Cloudflare Backend Proxy Deploy` workflow

Then re-check:

```bash
curl -fsS https://immcad-api.arkiteto.dpdns.org/healthz
curl -sS -D - -o /tmp/immcad-chat-recheck.out \
  -X POST https://immcad.arkiteto.dpdns.org/api/chat \
  -H 'content-type: application/json' \
  --data '{"message":"hello","session_id":"incident-recheck"}' \
  | sed -n '1,20p'
```
