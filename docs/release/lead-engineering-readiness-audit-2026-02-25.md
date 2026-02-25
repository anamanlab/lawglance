# Lead Engineering Readiness Audit (2026-02-25)

## Scope

This audit reviews production readiness for case-law research and case PDF export, with emphasis on:

- hardened runtime behavior across backend/frontend,
- CanLII fallback behavior ("asset, not blocker"),
- export approval and source-policy controls,
- execution hygiene (`AGENTS.md`, `tasks/lessons.md`, `tasks/todo.md`),
- known risks and decision logging.

## Evidence Run

- `make quality` -> pass (`374 passed`)
- `make verify` -> pass (warnings only)
- `npm run typecheck --prefix frontend-web` -> pass
- `npm run test --prefix frontend-web` -> pass (`53 passed`)
- `npm run build --prefix frontend-web` -> pass
- `pytest -q tests/test_backend_vercel_deploy_config.py tests/test_repository_hygiene_script.py tests/test_domain_leak_scanner.py tests/test_export_policy_gate.py` -> pass (`31 passed`)
- `./scripts/venv_exec.sh mypy` -> pass (`17 source files` in configured gate scope)
- `./scripts/venv_exec.sh pytest -q tests/test_quality_gates_workflow.py tests/test_release_gates_workflow.py` -> pass (`17 passed`)
- Production smoke checks on active deployments:
  - Prior authenticated smoke evidence (`vercel curl`) showed `GET /healthz` -> `200`, `GET /ops/metrics` -> `401` (expected auth), frontend root load -> `200`.
  - Current unauthenticated direct `curl` from this environment hits Vercel Authentication wall (`401` HTML auth challenge), so future smoke runs must use authenticated bypass/protection flow.

## What Is Working Now

1. Hardened aliases are consistently enforced.
- Backend and frontend both treat aliases like `production-us-east`, `prod_blue`, `ci-smoke` as hardened:
  - `src/immcad_api/settings.py`
  - `src/immcad_api/main.py`
  - `frontend-web/lib/server-runtime-config.ts`
  - `frontend-web/tests/server-runtime-config.contract.test.ts`

2. CanLII is non-blocking in hardened mode when official sources are available.
- Hardened mode disables scaffold fallback and requires official case-search assets/config:
  - `src/immcad_api/main.py`
  - `tests/test_api_scaffold.py`

3. Case PDF export is policy-gated and user-triggered in UX.
- UI requires explicit confirmation before export request:
  - `frontend-web/components/chat/chat-shell-container.tsx`
- Backend enforces:
  - `user_approved` requirement,
  - source registry and source policy checks,
  - host allowlist checks (request + redirect),
  - payload size limit,
  - PDF payload validation:
    - `src/immcad_api/api/routes/cases.py`
    - `tests/test_export_policy_gate.py`

4. Export host validation regression is fixed.
- Official `www.*` subdomain URLs are accepted; lookalike domains are rejected:
  - `src/immcad_api/api/routes/cases.py`
  - `backend-vercel/src/immcad_api/api/routes/cases.py`
  - `tests/test_export_policy_gate.py`

5. Backend runtime mirror parity is restored.
- `backend-vercel/src/immcad_api` is synchronized with `src/immcad_api`, and parity gate now passes:
  - `make backend-vercel-sync-validate`
  - `make quality`

## Gaps and Risks

1. P0 deployment blocker remains open.
- Source-based production deploy attempts for both backend and frontend are currently blocked by Vercel free-plan quota (`api-deployments-free-per-day`).
- Local fixes and readiness gates are in place, but rollout remains operationally blocked until quota resets and successful deploy evidence is captured.
- Release is not fully production-ready until a fresh backend production deploy is verified healthy (frontend same-SHA deploy optional but recommended).

2. Type-check coverage is improved but still intentionally scoped.
- `mypy` gate now validates 17 production-critical files (runtime entrypoints, export path, chat/case services, and related tests).
- Full-repo typing is still out of scope for this release cut; additional expansion can continue post-deploy.

3. Approval attestation remains mixed-mode.
- Hardened environments now require server-issued signed approval tokens (`/api/export/cases/approval`) for export.
- Non-hardened compatibility mode can still accept direct `user_approved=true`.
- This is acceptable for backward compatibility, but should be converged to token-only behavior across all environments.

4. Process hygiene risk.
- `tasks/todo.md` had duplicate active 2026-02-25 sections; this was cleaned to reduce conflicting execution signals.
- GitHub Issues are disabled; a repo-local tracker is now required to avoid issue-loss.
- Multi-agent dirty-worktree scans can fail on unrelated untracked files unless scanners are tracked-file aware (now addressed for domain leak scan).

5. CI guardrails are stronger, but deployment evidence still missing.
- Workflows now enforce deterministic frontend order (`build -> typecheck -> test`) and explicit backend `mypy` gating.
- Readiness remains operationally blocked until quota reset allows fresh production deploy evidence capture.

## Decisions Logged

1. Keep CanLII as metadata/search support, not as a hard dependency for hardened production behavior.
2. Keep CanLII full-text export disabled until legal/compliance approval is explicit.
3. Treat all production/prod/ci aliases as hardened across backend and frontend.
4. Prefer source-based backend deploys (or freshly generated audited prebuilt output) to avoid stale artifact drift.
5. Maintain a canonical in-repo issue register at `docs/release/known-issues.md` while GitHub Issues remain disabled.
6. Pin Vercel Python runtime via `.python-version` for official runtime selection instead of `vercel.json` runtime overrides.
7. Enforce backend mirror sync as a release gate before deploy approval.
8. Enforce deterministic frontend workflow order (`build -> typecheck -> test`) in quality/release gates.
9. Expand `mypy` release gate scope to production-critical modules and keep parity-safe typing fixes in both `src` and `backend-vercel/src`.
10. Enforce backend `mypy` execution in both quality and release workflows with workflow tests to prevent regression.

## Production Readiness Verdict

Not fully production-ready yet for final go-live sign-off due one P0 operational blocker (backend production redeploy confirmation), currently gated by Vercel quota.  
Code-level and local gate readiness is strong; operational release readiness needs quota reset, final backend deploy verification, and post-deploy smoke evidence.

## Prioritized Next Steps

1. Redeploy backend and frontend from trusted source-based paths after quota reset and verify READY status with deployment ID evidence.
2. Run production smoke checks for `/healthz`, `/api/chat`, `/api/search/cases`, `/api/export/cases`, and `/ops/metrics`.
3. Close or defer with sign-off:
   - converge non-hardened export approval to token-only flow (if required by policy),
   - keep `docs/release/known-issues.md` current.
