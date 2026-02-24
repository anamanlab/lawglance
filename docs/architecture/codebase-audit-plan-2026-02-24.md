# Codebase Audit Plan (2026-02-24)

## Purpose

Define and execute a best-practice audit program for IMMCAD across architecture, security, reliability, and operational maturity.

## Baseline Evidence (Executed)

- `make verify` -> passed (`0` failures, `2` warnings: `.env` missing, Redis CLI missing).
- `npm run typecheck --prefix frontend-web` -> passed.
- `npm run test --prefix frontend-web` -> passed (`9/9` tests).
- `make quality` -> passed:
  - Ruff lint passed.
  - Pytest passed (`104` tests).
  - Architecture docs validation passed.
  - Source registry validation passed.
  - Legal checklist validation passed.
  - Domain leak scan passed.
  - Jurisdiction eval passed (`100/100`).
  - Jurisdiction suite passed (`18/18`, citation coverage `100%`).
  - Repository hygiene checks passed.

## Prioritized Findings

### High

1. Unauthenticated operational telemetry endpoint.
   - `/ops/metrics` is not behind bearer auth, while auth checks are only applied to `/api/*`.
   - Risk: external metric reconnaissance, abuse pattern discovery.
   - Evidence: `src/immcad_api/main.py:170`, `src/immcad_api/main.py:279`.
   - Recommendation: require auth (or network allowlist) for `/ops/*` and keep telemetry private.

2. Dual runtime architecture with divergence risk.
   - Legacy Streamlit stack owns retrieval/vector/cache logic independently of FastAPI runtime.
   - Risk: policy, prompt, and behavior drift between runtime paths.
   - Evidence: `app.py:121`, `legacy/local_rag/lawglance_main.py:77`, `src/immcad_api/main.py:149`.
   - Recommendation: formally deprecate legacy runtime or convert it to thin API client mode.

### Medium

1. Rate limiter degrades to in-memory on Redis failure.
   - Redis errors silently fall back to local memory limiter.
   - Risk: uneven enforcement in multi-instance deployments, hidden degradation.
   - Evidence: `src/immcad_api/middleware/rate_limit.py:49`.
   - Recommendation: emit explicit degradation telemetry + optionally fail closed in production.

2. Release gate is manual-only.
   - `release-gates` runs only on `workflow_dispatch`.
   - Risk: production promotion without full release-readiness workflow.
   - Evidence: `.github/workflows/release-gates.yml:3`.
   - Recommendation: bind to release tags/branches and make deployment depend on successful gate.

3. Ingestion path not exercised in primary quality gate.
   - `quality-gates` validates many controls, but not ingestion job execution.
   - Risk: ingestion regressions detected late.
   - Evidence: `.github/workflows/quality-gates.yml:1`, `Makefile:60`.
   - Recommendation: add lightweight ingestion smoke in CI (dry-run or checkpointed run).

4. Schema strictness gap for request fields.
   - `locale` and `mode` are free-form strings.
   - Risk: policy-mode ambiguity, inconsistent behavior.
   - Evidence: `src/immcad_api/schemas.py:16`.
   - Recommendation: enforce enum/regex constraints for controlled inputs.

### Low

1. Metadata/identity drift in project config.
   - Package metadata still references `lawglance`.
   - Risk: operator confusion and tooling inconsistency.
   - Evidence: `pyproject.toml:2`.
   - Recommendation: align project metadata and docs to IMMCAD naming.

2. Ops alerting appears documented but not wired.
   - Alert thresholds are specified in docs; automation hooks are not evidenced in repo workflows.
   - Risk: delayed detection, manual-only response.
   - Evidence: `docs/architecture/07-deployment-and-operations.md:50`, `docs/architecture/06-quality-attributes-and-cross-cutting.md:69`.
   - Recommendation: wire `/ops/metrics` scraping and threshold-based alerting.

## 30/60/90 Day Remediation Plan

### 0-30 days (risk containment)

1. Protect `/ops/metrics` and `/healthz` exposure policy by environment.
2. Add explicit production telemetry/log event when rate limiter falls back from Redis.
3. Tighten request schemas (`locale`, `mode`) with explicit allowed values.
4. Add a release policy check that blocks production deploy if `release-gates` did not run.

Exit criteria:
- Unauthenticated access to `/ops/metrics` returns `401`/`403`.
- Rate limiter fallback is observable in logs/metrics and tested.
- Contract tests enforce strict request validation.

### 31-60 days (pipeline hardening)

1. Add ingestion smoke execution to CI (checkpoint-safe cadence).
2. Add dependency/security scanning to PR gates (`pip-audit`, `npm audit`, secret scan).
3. Add automated monitoring rule deployment tied to documented thresholds.

Exit criteria:
- Ingestion smoke runs on PR/main with artifact output.
- Dependency and secret scan failures block merge.
- Alerting rules exist for error/fallback/refusal/latency metrics.

### 61-90 days (architecture convergence)

1. Decide legacy Streamlit disposition (retire vs debug-only thin client).
2. If retained, remove embedded retrieval/LLM logic and call backend API only.
3. Align package/runtime metadata (`lawglance` -> `immcad`) and close naming drift.

Exit criteria:
- Single source of truth for chat orchestration and policy enforcement.
- No runtime path bypasses backend policy/citation controls.
- Architecture docs/ADRs updated to reflect converged runtime.

## Governance and Cadence

Weekly:
- Review open findings and SLA adherence by severity.
- Re-run `make quality` and frontend checks.

Per release:
- Mandatory `release-gates` evidence + legal checklist strict validation.
- Verify artifacts in `artifacts/evals` and runbook link correctness.

Quarterly:
- Re-score architecture/security/ops maturity and refresh this plan.

## Suggested Owners

- Platform/API owner: auth hardening, schema strictness, rate limiting.
- DevEx/CI owner: gate automation, security scans, ingestion smoke.
- Architecture owner: runtime convergence and ADR updates.
- Operations owner: monitoring/alerting and incident readiness.
