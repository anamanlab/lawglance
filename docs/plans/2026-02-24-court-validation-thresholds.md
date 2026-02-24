# Court Validation Thresholds Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add configurable court payload validation thresholds (invalid ratio + minimum valid records) and optional year-window enforcement to ingestion jobs.

**Architecture:** Introduce a court payload validation config and keep parsing/record-level validation in `src/immcad_api/sources/canada_courts.py`. Ingestion jobs consume the summary/config and decide success/failure while reporting validation counts.

**Tech Stack:** Python 3.11, pytest.

---

### Task 1: Test-First Court Validation Rules

**Files:**
- Create: `tests/test_canada_courts.py`
- Modify: `tests/test_ingestion_jobs.py`

**Step 1: Write failing tests**
- Add coverage for year-window acceptance/rejection in court record validation.
- Add ingestion tests for tolerated invalid ratio and above-threshold failure.

**Step 2: Run tests to verify they fail**
- Run: `scripts/venv_exec.sh pytest -q tests/test_canada_courts.py tests/test_ingestion_jobs.py`

### Task 2: Implement Court Parser + Validation Module

**Files:**
- Create: `src/immcad_api/sources/canada_courts.py`
- Modify: `src/immcad_api/sources/__init__.py`

**Step 1: Implement parser and validator**
- Port SCC/FC/FCA parsing helpers.
- Add `CourtPayloadValidationConfig` and year-window-aware validation.

**Step 2: Re-run tests**
- Run: `scripts/venv_exec.sh pytest -q tests/test_canada_courts.py`

### Task 3: Integrate Thresholds into Ingestion Jobs + CLI

**Files:**
- Modify: `src/immcad_api/ingestion/jobs.py`
- Modify: `scripts/run_ingestion_jobs.py`
- Modify: `tests/test_ingestion_jobs.py`

**Step 1: Enforce configurable thresholds**
- Apply court validation only for supported court sources.
- Fail on zero records, below minimum valid count, or invalid ratio above threshold.
- Preserve strict defaults.

**Step 2: Expose CLI options**
- Add CLI flags for invalid ratio, minimum valid records, expected year, and year window.

**Step 3: Verify**
- Run: `scripts/venv_exec.sh pytest -q tests/test_canada_courts.py tests/test_ingestion_jobs.py`

