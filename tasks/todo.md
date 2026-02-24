# Task Plan - 2026-02-24 - Court Validation Thresholds

## Current Focus
- Tune court ingestion payload validation to tolerate small invalid record ratios and support year-window checks.

## Plan
- [x] Add failing tests for tolerant invalid-ratio handling and year-window validation behavior.
- [x] Implement `canada_courts` parsing/validation module in this worktree with threshold-friendly summary helpers.
- [x] Integrate court payload validation into ingestion jobs with configurable thresholds.
- [x] Expose threshold/year-window knobs in `scripts/run_ingestion_jobs.py`.
- [x] Run targeted and impacted tests.

## Review
- Added `src/immcad_api/sources/canada_courts.py` with SCC/FC/FCA payload parsing, record validation, `CourtPayloadValidationConfig`, and year-window support.
- Integrated court payload validation into `src/immcad_api/ingestion/jobs.py` with configurable invalid-ratio and minimum-valid-record thresholds and per-source record counts in results.
- Added CLI knobs in `scripts/run_ingestion_jobs.py` for court validation tuning.
- Added/expanded tests in `tests/test_canada_courts.py` and `tests/test_ingestion_jobs.py`.
- Verification:
  - `./scripts/venv_exec.sh pytest -q tests/test_canada_courts.py tests/test_ingestion_jobs.py` -> PASS (`11 passed`)
  - `make test` -> PASS (`112 passed`)
  - `./scripts/venv_exec.sh ruff check ...` on changed Python files -> PASS
  - `make lint` still fails due pre-existing repo-wide issues unrelated to this feature (legacy files/notebooks, existing scripts)

---

# Task Plan - 2026-02-24 - Architecture Documentation Generator

## Current Focus
- Generate a comprehensive architecture documentation synthesis for the current codebase, while preserving and improving the existing `docs/architecture` corpus.

## Plan
- [x] Inventory existing architecture docs and automation to avoid duplication.
- [x] Capture current architecture evidence (entrypoints, services, APIs, ingestion, ops) from codebase files.
- [x] Add a new architecture analysis/governance synthesis doc mapping to C4 + arc42 + ADR + automation.
- [x] Update architecture indexes/README files (including TOC cleanup and new links).
- [x] Validate architecture docs with the repository validation script.

## Review
- Added `docs/architecture/10-architecture-analysis-and-governance.md` as an evidence-based synthesis doc covering current runtime topology, framework choices, data flows, governance, automation, and backlog.
- Added `docs/architecture/adr/ADR-006-architecture-documentation-as-code-governance.md` to formalize architecture docs as code + CI governance.
- Updated `docs/architecture/README.md` with a coverage map, new doc link, and TOC cleanup.
- Updated `docs/architecture/adr/README.md` with current ADR index, review cadence, and TOC cleanup.
- Updated `docs/architecture/adr/ADR-000-template.md` to remove duplicate TOC entries and add an optional implementation checklist.
- Updated `scripts/validate_architecture_docs.sh` to require the new architecture synthesis doc.
- Verification:
  - `bash scripts/validate_architecture_docs.sh` -> PASS (`ADR count: 6`, `Mermaid diagrams: 8`)
