# Canada Legal Readiness Remediation Plan

**Goal:** Close production-readiness gaps for SCC/FC/FCA ingestion and policy enforcement with release-blocking verification gates.

**Architecture:** Keep the existing ingestion + policy architecture, but add a conformance layer that probes real endpoints and validates payload quality before release. Move court validation from brittle all-or-nothing rules to configurable acceptance thresholds backed by metrics and CI gates.

**Tech Stack:** Python 3.11, FastAPI, httpx, pytest, Ruff, GitHub Actions.

---

## Immediate Execution Order (Senior Lead Sequence)

1. **Phase 0 - Release safety first (Day 0-1)**
   - Finalize secret/backups hygiene and workflow dedupe/concurrency.
   - Require workflow test gate pass before runtime changes continue.
2. **Phase 1 - Ingestion correctness (Day 1-2)**
   - Complete SCC/FC/FCA parser hardening and registry/source consistency.
   - Require parser + ingestion + registry test pass.
3. **Phase 2 - Runtime/API safety (Day 2-3)**
   - Close auth/prompt/citation/export-policy safety gaps with targeted contract tests.
4. **Phase 3 - Tooling/docs alignment + final gate (Day 3-4)**
   - Finish Makefile/doc-maintenance hardening and documentation consistency.
   - Run full typed + lint + targeted pytest + registry/smoke verification gate.

---

### Task 1: Stabilize SCC/FC/FCA Source Definitions

**Files:**
- Modify: `data/sources/canada-immigration/registry.json`
- Modify: `src/immcad_api/sources/canada_courts.py`
- Test: `tests/test_canada_courts.py`

**Step 1: Write failing tests for current FCA endpoint behavior**
- Add test coverage for endpoint URL validity and parser behavior when feed endpoint returns non-feed content or 404.

**Step 2: Run tests to confirm failure**
- Run: `scripts/venv_exec.sh pytest -q tests/test_canada_courts.py`
- Expected: failure that demonstrates current FCA URL/feed assumptions are invalid.

**Step 3: Implement corrected source definition and parser resilience**
- Update FCA source URL to the validated live endpoint path.
- Handle Decisia response variants explicitly (feed vs HTML/error payloads) with deterministic error messages.

**Step 4: Re-run tests**
- Run: `scripts/venv_exec.sh pytest -q tests/test_canada_courts.py`
- Expected: PASS.

---

### Task 2: Make Court Validation Production-Safe (Threshold + Year Window)

**Files:**
- Modify: `src/immcad_api/sources/canada_courts.py`
- Modify: `src/immcad_api/ingestion/jobs.py`
- Modify: `scripts/run_ingestion_jobs.py`
- Test: `tests/test_ingestion_jobs.py`

**Step 1: Write failing tests for thresholded validation**
- Add tests for: accepted payload with small invalid ratio, rejected payload above threshold, and optional year-window enforcement.

**Step 2: Run tests to confirm failure**
- Run: `scripts/venv_exec.sh pytest -q tests/test_ingestion_jobs.py`
- Expected: new tests fail.

**Step 3: Implement configurable validation controls**
- Add validation config (max invalid ratio, minimum valid records, optional expected year/window).
- Pass config from CLI to ingestion executor.

**Step 4: Re-run tests**
- Run: `scripts/venv_exec.sh pytest -q tests/test_ingestion_jobs.py tests/test_canada_courts.py`
- Expected: PASS.

---

### Task 3: Add Case-Law Conformance Runner + CI Release Gate

**Files:**
- Create: `scripts/run_case_law_conformance.py`
- Create: `tests/test_case_law_conformance_script.py`
- Modify: `.github/workflows/quality-gates.yml`
- Modify: `.github/workflows/release-gates.yml`
- Test (pre-existing): `tests/test_quality_gates_workflow.py`
- Test (pre-existing): `tests/test_release_gates_workflow.py`

**Step 1: Write failing script tests**
- Cover command exit codes, output schema, and strict-mode failure behavior.

**Step 2: Run tests to confirm failure**
- Run: `scripts/venv_exec.sh pytest -q tests/test_case_law_conformance_script.py`
- Expected: FAIL.

**Step 3: Implement conformance script**
- Probe SCC/FC/FCA endpoints.
- Validate parseability and quality thresholds.
- CI secrets: explicitly inject credentials only when needed (`${{ secrets.DECISIA_API_KEY }}`, `${{ secrets.SCC_API_KEY }}`, `${{ secrets.FC_API_KEY }}`, `${{ secrets.FCA_API_KEY }}`).
- Emit JSON artifact with per-source status and metadata only (HTTP status code, safe header subset, parse stats, timestamp); never include raw response body/tokens/session data.

**Step 4: Wire CI gates**
- Add workflow steps that run conformance in strict mode and fail pipeline on red status.

**Step 5: Verify**
- Run:
  - `scripts/venv_exec.sh python scripts/run_case_law_conformance.py --strict --output /tmp/case-law-conformance.json`
  - `scripts/venv_exec.sh pytest -q tests/test_case_law_conformance_script.py tests/test_quality_gates_workflow.py tests/test_release_gates_workflow.py`

---

### Task 4: Add Source-Level Throttling and Retry Budgets

**Files:**
- Create: `src/immcad_api/ingestion/source_fetch_policy.py`
- Modify: `src/immcad_api/ingestion/jobs.py`
- Create: `config/fetch_policy.yaml` (canonical fetch-policy config path; load via shared `CONFIG_FETCH_POLICY_PATH` constant/env override so runtime/tests use the same file)
- Test: `tests/test_ingestion_jobs.py`

**Step 1: Write failing tests**
- Add coverage for per-source retry ceilings, backoff behavior, and terminal failure classification.

**Step 2: Run tests**
- Run: `scripts/venv_exec.sh pytest -q tests/test_ingestion_jobs.py`
- Expected: FAIL.

**Step 3: Implement throttling + retry policies**
- Define source-specific policies for SCC/FC/FCA.
- Apply policies in fetch execution path.

**Step 4: Re-run tests**
- Run: `scripts/venv_exec.sh pytest -q tests/test_ingestion_jobs.py`
- Expected: PASS.

---

### Task 5: Wire Export Policy Gate to API Surface

**Files:**
- Modify: `src/immcad_api/api/routes/cases.py` (or concrete export/download router if present)
- Modify: `src/immcad_api/main.py`
- Modify: `src/immcad_api/policy/source_policy.py` (if helper signature changes)
- Create: `tests/test_export_policy_gate.py`

**Step 1: Write failing API tests**
- Cover allowed export, blocked export, and unknown-source export behavior with `policy_reason`.

**Step 2: Run tests**
- Run: `scripts/venv_exec.sh pytest -q tests/test_export_policy_gate.py`
- Expected: FAIL for new export-gate expectations.

**Step 3: Implement gate wiring**
- Add `EXPORT_POLICY_GATE_ENABLED` feature flag in `main.py` (default `false`).
- Call `is_source_export_allowed` in export/download path.
- When flag is `false`, preserve legacy export behavior.
- When flag is `true`, return policy-aware error envelope for blocked exports (`403` with `policy_reason`) so clients can distinguish policy blocks.
- Rollout/deprecation: announce change, run 30-day opt-in testing window with flag default `false`, then 60-day gradual enforcement before considering a default flip.

**Step 4: Re-run tests**
- Run: `scripts/venv_exec.sh pytest -q tests/test_export_policy_gate.py`
- Expected: PASS.

---

### Task 6: Publish Pilot Scorecard + Ops Metrics

**Files:**
- Modify: `src/immcad_api/main.py` (`/ops/metrics`)
- Create: `scripts/build_case_law_scorecard.py`
- Create: `artifacts/ingestion/` scorecard output contract docs
- Test: `tests/test_ops_alert_evaluator.py` and/or new scorecard tests

**Step 1: Write failing tests**
- Validate scorecard schema and `/ops/metrics` exposure for invalid-record/freshness indicators.

**Step 2: Run tests**
- Run: `scripts/venv_exec.sh pytest -q tests/test_ops_alert_evaluator.py`
- Expected: FAIL for new metrics contract.

**Step 3: Implement metrics + scorecard**
- Surface per-source: `records_invalid`, `records_valid`, `records_total`, freshness lag, endpoint health.

**Step 4: Verify**
- Run:
  - `scripts/venv_exec.sh python scripts/build_case_law_scorecard.py --ingestion-report /tmp/ingestion-scheduled.json --output /tmp/case-law-scorecard.json`
  - `scripts/venv_exec.sh pytest -q tests/test_ops_alert_evaluator.py`

---

### Final Verification Gate

Run and require all green before implementation is considered complete:

```bash
scripts/venv_exec.sh mypy src tests
scripts/venv_exec.sh ruff check src/immcad_api scripts tests
scripts/venv_exec.sh pytest -q \
  tests/test_canada_registry.py \
  tests/test_validate_source_registry.py \
  tests/test_source_policy.py \
  tests/test_canada_courts.py \
  tests/test_case_law_conformance_script.py \
  tests/test_quality_gates_workflow.py \
  tests/test_release_gates_workflow.py \
  tests/test_ingestion_jobs.py \
  tests/test_ingestion_smoke_script.py \
  tests/test_export_policy_gate.py \
  tests/test_build_case_law_scorecard.py \
  tests/test_ops_alert_evaluator.py \
  tests/test_ops_alerts_workflow.py \
  tests/test_jurisdiction_suite.py
scripts/venv_exec.sh python scripts/validate_source_registry.py
scripts/venv_exec.sh python scripts/run_ingestion_smoke.py --output /tmp/ingestion-smoke-report.json --state-path /tmp/ingestion-smoke-state.json
scripts/venv_exec.sh python scripts/run_case_law_conformance.py --strict --output /tmp/case-law-conformance.json
```
