# Case-Law Conformance Runner Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a CI-ready case-law conformance runner for SCC/FC/FCA with warning-only quality-gates behavior and strict release-gates enforcement.

**Architecture:** Implement a reusable conformance evaluator module under `src/immcad_api/ops/` and keep `scripts/run_case_law_conformance.py` as a thin CLI wrapper. Reuse existing registry and court payload validation primitives to minimize logic duplication and reduce drift.

**Tech Stack:** Python 3.11, `httpx`, pytest, Ruff, GitHub Actions.

---

### Task 1: Add Conformance Script Tests (TDD First)

**Files:**
- Create: `tests/test_case_law_conformance_script.py`
- Reference: `scripts/run_ingestion_smoke.py`
- Reference: `tests/test_ingestion_smoke_script.py`

**Step 1: Write the failing tests**

Cover:
- script writes JSON report
- non-strict mode returns exit code `0` on source failure
- strict mode returns non-zero on source failure
- report contains per-source and overall status fields

**Step 2: Run test to verify it fails**

Run: `./scripts/venv_exec.sh pytest -q tests/test_case_law_conformance_script.py`

Expected: FAIL because script/module do not exist yet.

**Step 3: Commit (optional checkpoint)**

```bash
git add tests/test_case_law_conformance_script.py
git commit -m "test(conformance): add failing script coverage"
```

---

### Task 2: Implement Reusable Conformance Evaluator Module

**Files:**
- Create: `src/immcad_api/ops/case_law_conformance.py`
- Modify: `src/immcad_api/ops/__init__.py` (if needed)

**Step 1: Write minimal implementation**

Implement:
- source selection (`SCC_DECISIONS`, `FC_DECISIONS`, `FCA_DECISIONS`) from registry
- HTTP fetch helper
- payload validation integration (`validate_court_source_payload`)
- per-source result model + overall report model
- threshold evaluation (`max_invalid_ratio`, `min_records`)

**Step 2: Run tests**

Run: `./scripts/venv_exec.sh pytest -q tests/test_case_law_conformance_script.py`

Expected: still FAIL (CLI wrapper not implemented yet), but core import errors resolved.

**Step 3: Commit (optional checkpoint)**

```bash
git add src/immcad_api/ops/case_law_conformance.py src/immcad_api/ops/__init__.py
git commit -m "feat(ops): add case-law conformance evaluator"
```

---

### Task 3: Implement CLI Wrapper

**Files:**
- Create: `scripts/run_case_law_conformance.py`

**Step 1: Write minimal script wrapper**

Implement CLI args:
- `--output`
- `--registry`
- `--timeout-seconds`
- `--strict`
- `--max-invalid-ratio`
- `--min-records`

Behavior:
- write JSON report to output path
- print concise summary
- `--strict` returns non-zero when overall status is `fail`

**Step 2: Run tests**

Run: `./scripts/venv_exec.sh pytest -q tests/test_case_law_conformance_script.py`

Expected: PASS.

**Step 3: Commit (optional checkpoint)**

```bash
git add scripts/run_case_law_conformance.py tests/test_case_law_conformance_script.py
git commit -m "feat(ops): add case-law conformance CLI"
```

---

### Task 4: Wire CI Workflows (Warning-Only vs Strict)

**Files:**
- Modify: `.github/workflows/quality-gates.yml`
- Modify: `.github/workflows/release-gates.yml`
- Modify: `tests/test_quality_gates_workflow.py`
- Modify: `tests/test_release_gates_workflow.py`

**Step 1: Write/extend failing workflow tests**

Add assertions for:
- conformance step names present
- quality gate run command without `--strict`
- release gate run command with `--strict`
- conformance report artifact upload paths

**Step 2: Run tests to verify failure**

Run: `./scripts/venv_exec.sh pytest -q tests/test_quality_gates_workflow.py tests/test_release_gates_workflow.py`

Expected: FAIL before workflow edits.

**Step 3: Update workflows**

Add:
- quality-gates step: non-strict conformance run + artifact upload
- release-gates step: strict conformance run + artifact upload

**Step 4: Re-run tests**

Run: `./scripts/venv_exec.sh pytest -q tests/test_quality_gates_workflow.py tests/test_release_gates_workflow.py`

Expected: PASS.

---

### Task 5: Lint + Runtime Verification

**Files:**
- Lint: `src/immcad_api/ops/case_law_conformance.py`, `scripts/run_case_law_conformance.py`, `tests/test_case_law_conformance_script.py`

**Step 1: Run Ruff**

Run: `./scripts/venv_exec.sh ruff check src/immcad_api/ops/case_law_conformance.py scripts/run_case_law_conformance.py tests/test_case_law_conformance_script.py tests/test_quality_gates_workflow.py tests/test_release_gates_workflow.py`

Expected: PASS.

**Step 2: Run full targeted test set**

Run: `./scripts/venv_exec.sh pytest -q tests/test_case_law_conformance_script.py tests/test_quality_gates_workflow.py tests/test_release_gates_workflow.py`

Expected: PASS.

**Step 3: Smoke the script (non-strict)**

Run: `./scripts/venv_exec.sh python scripts/run_case_law_conformance.py --output /tmp/case-law-conformance.json`

Expected: JSON artifact written; exit code `0` in non-strict mode even if sources warn/fail.

**Step 4: Commit**

```bash
git add src/immcad_api/ops/case_law_conformance.py src/immcad_api/ops/__init__.py \
  scripts/run_case_law_conformance.py \
  .github/workflows/quality-gates.yml .github/workflows/release-gates.yml \
  tests/test_case_law_conformance_script.py tests/test_quality_gates_workflow.py tests/test_release_gates_workflow.py \
  docs/plans/2026-02-24-case-law-conformance-runner-design.md \
  docs/plans/2026-02-24-case-law-conformance-runner-implementation-plan.md
git commit -m "feat(ci): add case-law conformance runner gate"
```
