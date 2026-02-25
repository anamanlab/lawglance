# Deep Production Readiness Audit Plan (Pre-Deploy)

> Status (2026-02-25): Contains historical Vercel-era audit checkpoints.
> For active Cloudflare migration readiness, use:
> - `docs/plans/2026-02-25-cloudflare-migration-plan.md`
> - `docs/release/pre-deploy-command-sheet-2026-02-25.md`
> - `make release-preflight`

## Objective
Perform a full pre-deploy systems audit so the next backend/frontend deployment can be executed with minimal risk and no surprise blockers.

## Scope
- Backend runtime (`src/immcad_api`, `backend-vercel/src/immcad_api`)
- Frontend runtime (`frontend-web`)
- Policy and legal-source controls (`config/source_policy.yaml`, registry, export gate)
- CI/CD and deployment safety (GitHub Actions, Cloudflare config, deploy process)
- Operations readiness (health, metrics, alerts, incident/rollback docs)
- Release process hygiene (tasks, known issues, PR readiness, evidence trail)

## Audit Phases

### Phase 0 - Baseline Snapshot
- Capture git/branch/dirty-tree state and classify changes (intended vs unrelated).
- Reconfirm open PR status and latest merged PR.
- Reconfirm active frontend/backend production aliases and latest deployment IDs.
- Freeze this snapshot in `tasks/todo.md` and `docs/release/known-issues.md`.

### Phase 1 - Backend Deep Audit
- API contract verification:
  - `POST /api/chat`
  - `POST /api/search/cases`
  - `POST /api/export/cases`
  - `GET /healthz`
  - `GET /ops/metrics`
- Auth and hardening checks:
  - bearer enforcement behavior in hardened aliases/environments
  - rate limiting and trace IDs
  - fail-closed behavior for missing source assets
- Export gate checks:
  - source policy allow/deny
  - trusted host validation (exact + dot-bounded subdomain)
  - non-PDF payload rejection
  - consent enforcement path and known gap documentation
- Data/source checks:
  - source registry consistency
  - source-policy parity and backend mirror sync
  - official-source-first fallback behavior

### Phase 2 - Frontend Deep Audit
- Proxy contract checks for `/api/chat`, `/api/search/cases`, `/api/export/cases`.
- UI behavior checks:
  - chat response rendering and citation flow
  - related-case search workflow
  - export confirmation UX and error states
- Runtime config checks:
  - hardened mode handling
  - backend URL and token wiring
  - fallback behavior only where allowed

### Phase 3 - Security and Compliance Audit
- Secrets and artifact hygiene:
  - tracked `.env*` leakage checks
  - stale prebuilt artifact checks
  - deploy-context exclusions
- Legal/policy guardrails:
  - Canada-only runtime prompt and policy behavior
  - explicit classification of residual legacy non-Canada references (runtime vs archival)
  - not-legal-advice positioning consistency in user-visible paths

### Phase 4 - CI/CD and Deploy Process Audit
- Validate quality gates and test matrix coverage.
- Validate deployment configs (`backend-vercel/vercel.json`, `.python-version`, `.vercelignore`, frontend build path).
- Validate redeploy runbook for quota, rollback, and smoke order.
- Pre-build a deterministic deploy checklist with exact commands.

### Phase 5 - Operations and Recovery Audit
- Validate observability contracts (`/ops/metrics` fields used by alerting).
- Validate incident runbooks and rollback criteria are executable.
- Validate production smoke script/command set for both unauthenticated and authenticated checks.

## Required Verification Commands (Audit Run)
- `make quality`
- `make source-registry-validate`
- `make backend-vercel-sync-validate`
- `uv run pytest -q tests/test_api_scaffold.py tests/test_export_policy_gate.py tests/test_source_policy.py tests/test_settings.py tests/test_case_search_service.py tests/test_official_case_law_client.py`
- `npm run typecheck --prefix frontend-web`
- `npm run test --prefix frontend-web`
- `npm run build --prefix frontend-web`
- `uv run python scripts/scan_domain_leaks.py`
- `bash scripts/check_repository_hygiene.sh`

## Deliverables
- Updated `tasks/todo.md` with completed audit checklist and evidence.
- Updated `docs/release/known-issues.md` with severity, owner, due date, and acceptance/defer rationale.
- Updated release readiness summary with explicit go/no-go decision gates.
- Final pre-deploy command sheet for backend + frontend redeploy and smoke verification.

## Exit Criteria
- All critical/high findings are either fixed or explicitly accepted with owner and due date.
- No unresolved P0 blocker except external quota/timing constraints.
- Backend/frontend deployment command path is verified and reproducible.
- Authenticated smoke test plan is ready with exact token/env requirements.
- We can execute deploy + smoke in one run without needing new design decisions.

## Risk Ranking Template
- `P0` blocks deploy
- `P1` deploy allowed only with explicit leadership acceptance
- `P2` post-deploy follow-up allowed
- `P3` backlog improvement
