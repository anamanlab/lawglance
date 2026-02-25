# Lead Engineering Readiness Audit (2026-02-25)

## Scope

This audit reviews production readiness for case-law research and case PDF export, with emphasis on:

- Cloudflare-first deploy posture (frontend worker + backend edge proxy),
- hardened runtime behavior across backend/frontend,
- export approval and source-policy controls,
- release/process hygiene and decision logging.

## Evidence Run

- `make quality` -> pass (`374 passed`).
- `make verify` -> pass (warnings only).
- `npm run typecheck --prefix frontend-web` -> pass.
- `npm run test --prefix frontend-web` -> pass.
- `npm run build --prefix frontend-web` -> pass.
- `./scripts/venv_exec.sh mypy` -> pass (`17 source files` in configured gate scope).
- `./scripts/venv_exec.sh pytest -q tests/test_quality_gates_workflow.py tests/test_release_gates_workflow.py` -> pass.

Cloudflare deployment and smoke evidence (UTC, 2026-02-25):

- Backend proxy deployed:
  - Worker: `immcad-backend-proxy`
  - Version: `2ef750a9-ae2c-431c-837c-7425fc60063b`
  - URL: `https://immcad-backend-proxy.optivoo-edu.workers.dev`
- Frontend deployed:
  - Worker: `immcad-frontend-web`
  - Version: `d2cce7e8-094e-489d-b54b-10af2b620e87`
  - URL: `https://immcad-frontend-web.optivoo-edu.workers.dev`
- Custom domains configured and externally resolvable via public resolvers:
  - `immcad.arkiteto.dpdns.org`
  - `immcad-api.arkiteto.dpdns.org`
- Smoke checks:
  - `GET /healthz` on backend custom domain -> `200`
  - `POST /api/chat` on backend custom domain -> `200` (authenticated)
  - `POST /api/chat` and `POST /api/search/cases` via frontend workers.dev -> `200` (authenticated)
  - `POST /api/chat` via frontend custom domain (resolver override) -> `200`

## What Is Working Now

1. Cloudflare frontend deploy path is production-usable.
- OpenNext + Wrangler deploy and smoke checks are green.
- Workers and custom-domain endpoints both return expected responses.

2. Backend edge ingress migration is operational.
- Backend proxy worker is live and routes `/api/*`, `/ops/*`, `/healthz`.
- Frontend server-side API calls now target Cloudflare backend custom domain.

3. Policy and export gates remain enforced.
- Source-policy and export approval behavior remain active in backend route logic.
- Hardened environment alias behavior remains consistent across backend and frontend.

4. CI/release controls remain deterministic.
- Workflow order and typed gate checks remain enforced with tests.
- Cloudflare deploy runbook now includes clean-worktree preflight guard.

## Gaps and Risks

1. P0 migration completion blocker remains open.
- Backend runtime is still transitional: Cloudflare proxy -> legacy backend origin.
- Full Cloudflare-native backend runtime (Python Worker or containerized runtime) is not complete yet.
- Native Python Worker canary deploy attempt currently fails on plan limits (`code: 10027`, bundle size exceeds free-plan Worker script limit), so backend cutover requires dependency slimming and/or alternative runtime path.

2. P1 backend runtime performance risk remains open.
- Before full Cloudflare-native cutover, synchronous heavy backend paths need load/perf proof or async hardening for Cloudflare limits.
- Perf smoke harness is available (`make backend-cf-perf-smoke`), but production-grade load evidence is still pending.

3. P1 issue-tracking governance risk remains open.
- GitHub Issues are disabled; team must keep `docs/release/known-issues.md` current or risk losing defect triage continuity.

4. P2 DNS propagation/caching operational nuance.
- Some local resolvers can lag and retain `NXDOMAIN` during custom-domain propagation.
- Public resolver checks (`1.1.1.1`, `8.8.8.8`) should be part of cutover verification.

## Decisions Logged

1. Cloudflare is the primary deploy platform for frontend and edge ingress.
2. Backend runtime remains in transitional proxy mode until native runtime migration exits canary gates.
3. `make release-preflight` (clean worktree + hygiene + Wrangler auth) is now required before production deploy execution.
4. Legacy Vercel operational docs are treated as historical only; Cloudflare-first command sheet is canonical.

## Production Readiness Verdict

Partially production-ready.

- Ready now for Cloudflare frontend + backend proxy operation.
- Not yet fully migration-complete for final Cloudflare-native backend sign-off due one P0 open item (native backend runtime cutover).

## Prioritized Next Steps

1. Complete backend native runtime migration (Python Worker or containerized path) and canary validation.
2. Execute Cloudflare-native backend load/perf validation and close runtime risk.
3. Keep `docs/release/known-issues.md` and release evidence updated after each deploy window until P0 closes.
