# Cloudflare Migration Plan - 2026-02-25

## Objective
- Migrate IMMCAD from Vercel to Cloudflare with a production-safe, reversible rollout.
- Keep current behavior for legal-policy gates, citation trust rules, and API auth.
- Minimize rewrite risk by migrating frontend first, then backend with explicit architecture gate.

## Execution Status (2026-02-25)
- Frontend Cloudflare path: implemented (`frontend-web` OpenNext config + CI deploy workflow).
- Backend edge transitional path: implemented (`backend-cloudflare` Worker proxy + CI deploy workflow).
- Backend native runtime decision: Python Workers path selected for next implementation phase; canary validation is still pending.
- Backend native runtime scaffold landed:
  - `backend-cloudflare/src/entry.py`
  - `backend-cloudflare/wrangler.toml`
  - `backend-cloudflare/pyproject.toml`
  - `.github/workflows/cloudflare-backend-native-deploy.yml`
- Live deployment evidence captured:
  - `immcad-frontend-web` Worker deployed (version `d2cce7e8-094e-489d-b54b-10af2b620e87`)
  - `immcad-backend-proxy` Worker deployed (version `2ef750a9-ae2c-431c-837c-7425fc60063b`)
  - Custom domains configured (`immcad.arkiteto.dpdns.org`, `immcad-api.arkiteto.dpdns.org`)

## Verified Platform Facts (as of 2026-02-25)
- Cloudflare Workers Free plan limits are strict for production traffic and CPU-intensive requests (`100,000 requests/day`, `10ms CPU/request`). Paid Workers removes the daily request cap and raises per-request CPU limits.
- Cloudflare Pages Free has build quotas (`500 builds/month`), and Pages Functions usage counts against Workers quotas.
- Cloudflare currently recommends Workers (OpenNext) for Next.js deployment over static Pages workflows.
- Cloudflare Containers are in beta and currently have known gaps (for example: no native autoscaling/load balancing yet).

## Recommended Target Architecture
- Frontend: `frontend-web` on Cloudflare Workers using `@opennextjs/cloudflare`.
- Backend: `backend-vercel` moved to Cloudflare in two-step evaluation:
  1. Primary path: Cloudflare Containers (lowest code rewrite, but beta risk).
  2. Fallback path: Python Worker + FastAPI package (higher refactor effort, avoids container runtime dependencies).
- Secrets/config: Cloudflare Secrets + env vars through Wrangler.
- Edge controls: Cloudflare WAF/rate limits + app-layer bearer token auth retained.

## Phase 0 - Decision Gate and Prerequisites
1. Confirm account tier decision:
- Use Workers Paid for production readiness (free-tier CPU/request limits are unsuitable for this backend).
2. Create Cloudflare project/environment map:
- `immcad-dev`, `immcad-staging`, `immcad-prod`.
3. Define hard rollback target:
- Keep current Vercel deployments live until Cloudflare cutover is stable for 7 days.
4. Freeze baseline:
- Record current latency/error/throughput and key API contract snapshots before migration.

## Phase 1 - Frontend Migration (Low-Risk First)
1. Add Cloudflare Next.js adapter and Wrangler:
- Install `@opennextjs/cloudflare` and `wrangler`.
2. Add Cloudflare config files:
- `wrangler.jsonc` with `main=.open-next/worker.js`, `assets.directory=.open-next/assets`, `compatibility_flags=["nodejs_compat"]`.
- `open-next.config.ts` using `defineCloudflareConfig()`.
3. Update frontend scripts:
- `preview`: `opennextjs-cloudflare build && opennextjs-cloudflare preview`
- `deploy`: `opennextjs-cloudflare build && opennextjs-cloudflare deploy`
4. Local verification:
- `npm run dev`
- `npm run preview` (Cloudflare runtime parity check)
- Existing unit/integration/e2e suites.
5. Deploy non-prod Workers URL and run smoke tests:
- Chat send/receive
- Related case search
- Export approval route behavior
- Header/security policy parity.

## Phase 2 - Backend Architecture Spike (Mandatory Gate)
1. Build two short proofs of concept (POCs):
- POC-A: Cloudflare Containers for current FastAPI backend.
- POC-B: Python Worker/FastAPI package path.
2. Evaluate against strict criteria:
- p95 latency, cold start behavior, concurrency, operational complexity, CI/CD fit, and policy/test parity.
3. Decision checkpoint:
- If Containers POC meets SLO and risk tolerance, proceed with Containers.
- If not, pivot to Python Worker path.

## Phase 3A - Backend via Cloudflare Containers (Preferred if POC Passes)
1. Add backend container packaging:
- Create `Dockerfile` for `backend-vercel` app entrypoint.
2. Add Worker container orchestrator:
- Durable Object + container binding configuration in `wrangler.jsonc`.
- Route `/api/*`, `/ops/*`, `/healthz` through Worker to container instance.
3. Configure secrets and env:
- Add provider/API keys, bearer token, registry/policy settings via `wrangler secret put`.
4. Add health + readiness checks:
- Container boot probe + upstream timeout/circuit protection.
5. Add load and failure tests:
- Burst test, cold-start test, upstream timeout/retry, and auth failure test.
6. Canary deploy:
- Route limited internal traffic first, then staged % increase.

## Phase 3B - Backend via Python Worker (Fallback if Containers Fails Gate)
1. Initialize Python Worker setup with `pywrangler`.
2. Adapt FastAPI integration to Workers Python runtime.
3. Port env/secrets and auth middleware behavior.
4. Re-run backend policy/citation/jurisdiction suites.
5. Canary deploy and compare to baseline.

## Phase 4 - Platform Security and Compliance Hardening
1. Keep current application-level auth and add Cloudflare edge protections:
- WAF rules, bot protections where applicable, and rate limiting policy.
2. Verify secrets posture:
- No `.env` in build artifacts; only Cloudflare secret bindings.
3. Keep legal-policy invariants:
- Canada-only prompt and source policy checks remain enforced.
- Trusted citation domain enforcement unchanged.

## Phase 5 - CI/CD Migration
1. Add Cloudflare deployment workflow files:
- Frontend deploy workflow for Workers.
- Backend deploy workflow (Containers or Python Worker path).
2. Keep deterministic quality gates before deploy:
- Lint, types, tests, policy validations, source sync validations.
3. Add rollback workflow:
- One-command rollback to previous Worker version.

## Phase 6 - Production Cutover and Rollback Plan
1. Staging sign-off checklist (must pass 100%):
- API contracts
- Auth flows
- Case-search correctness
- Export policy gates
- Error telemetry.
2. DNS cutover plan:
- Move frontend domain first, backend API host second (or maintain separate API host with explicit `IMMCAD_API_BASE_URL`).
3. 24h/72h observation windows:
- Track error rates, p95, policy refusal rates, export-policy denials, and provider fallback frequency.
4. Rollback criteria:
- Any P0 legal-policy regression
- Sustained elevated 5xx/error budget burn
- Unacceptable latency regression vs baseline.

## Immediate Next Steps (Execution Order)
1. Execute backend native runtime implementation (Python Workers path) with auth/policy parity.
2. Run canary + load/perf validation and close `KI-2026-02-25-01` and `KI-2026-02-25-07` when evidence passes.
3. Complete 24h/72h observation windows and finalize Cloudflare-only production sign-off.

## Official References Used
- Cloudflare Workers Next.js (OpenNext) guide:
  https://developers.cloudflare.com/workers/framework-guides/web-apps/nextjs/
- OpenNext Cloudflare adapter docs:
  https://github.com/opennextjs/opennextjs-cloudflare/blob/main/packages/cloudflare/README.md
- Workers limits:
  https://developers.cloudflare.com/workers/platform/limits/
- Workers pricing:
  https://developers.cloudflare.com/workers/platform/pricing/
- Pages limits:
  https://developers.cloudflare.com/pages/platform/limits/
- Cloudflare Containers beta info:
  https://developers.cloudflare.com/containers/beta-info/
- Python Workers overview:
  https://developers.cloudflare.com/workers/languages/python/
