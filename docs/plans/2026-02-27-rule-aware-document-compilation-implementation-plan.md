# Rule-Aware Court/Tribunal Document Compilation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a production-safe, rule-aware document compilation workflow that can generate forum-compliant package outputs (ordered record, TOC with page mapping, pagination metadata, and readiness blockers) for Federal Court immigration JR and IRB divisions.

**Architecture:** Move forum logic from hardcoded Python tuples into a versioned rule catalog with source-cited requirements, then add a compilation pipeline: intake storage -> extraction/page map -> rule validation -> package assembly. Keep legal-drafting outputs procedural (non-advisory) and block generation when mandatory rules are unmet.

**Tech Stack:** Python 3.11+, FastAPI, Pydantic, PyMuPDF, pytest, Next.js frontend-web, Redis (optional), YAML/JSON rule catalogs.

---

## Research Baseline (Official Sources Reviewed 2026-02-27)

### 1) Federal Court (Immigration JR)
- Federal Courts Citizenship, Immigration and Refugee Protection Rules (SOR/93-22) require the applicant record (for leave) to contain specific items in order and to have consecutively numbered pages.
- Respondent records in leave stage include affidavit(s) and memorandum, with memorandum length limit in that stage.
- Tribunal record requirements are defined with specific required contents and timing after leave.

Primary source:
- https://laws-lois.justice.gc.ca/eng/regulations/SOR-93-22/

### 2) Federal Courts Rules (General JR Procedure)
- Judicial review hearing-stage records require affidavit(s) and memorandum in applicant/respondent records, plus consecutively numbered pages and prescribed ordering.

Primary source:
- https://laws-lois.justice.gc.ca/eng/regulations/SOR-98-106/

### 3) IRB RPD Rules (SOR/2012-256)
- Document packages require indexed/listed content when multi-document.
- Translation evidence must include translator declaration.
- Disclosure timing and filing window rules are explicit and should be represented as machine-checkable constraints.

Primary source:
- https://laws-lois.justice.gc.ca/eng/regulations/SOR-2012-256/

### 4) IRB RAD Rules (SOR/2012-257)
- Appellant records require structured document lists (index behavior), ordering, and page numbering behavior when multiple documents are filed.
- Translation declaration requirements are explicit.

Primary source:
- https://laws-lois.justice.gc.ca/eng/regulations/SOR-2012-257/

### 5) IRB ID Rules (SOR/2002-229)
- Filing/disclosure obligations include evidence packaging and translation-declaration conditions.

Primary source:
- https://laws-lois.justice.gc.ca/eng/regulations/SOR-2002-229/

### 6) IRB IAD Rules (Current: SOR/2022-277)
- Current IAD regulation defines appeal books/records, memorandum/argument constraints, and page-order/list behavior for compiled filings.
- Legacy SOR/2002-230 is superseded for current-state design.

Primary source:
- https://laws-lois.justice.gc.ca/eng/regulations/SOR-2022-277/

### 7) E-filing Practical Constraints (UI/Output Shape)
- Federal Court and IRB electronic filing guidance should be captured as operational constraints (accepted formats, size limits, splitting/bookmarking expectations where applicable).

Primary sources:
- https://www.fct-cf.gc.ca/en/pages/representing-yourself/e-filing
- https://irb.gc.ca/en/forms/Pages/index.aspx

## Design Principles From Research
- Keep rule provenance in code: each enforceable rule must store source URL + citation reference.
- Separate legal-rule validation from OCR/classification confidence logic.
- Distinguish three layers of readiness:
  - document completeness (required vs conditional docs)
  - package structure (order, index/TOC, pagination)
  - procedural timing (deadlines/service windows)
- Never “assume compliant”: return machine-readable violations with remediation hints.

## Implementation Plan

### Task 1: Introduce Versioned Rule Catalog With Source Citations

**Files:**
- Create: `data/policy/document_compilation_rules.ca.yaml`
- Create: `src/immcad_api/policy/document_compilation_rules.py`
- Create: `tests/test_document_compilation_rules.py`

**Step 1:** Write failing tests for catalog loading and schema validation (forum, proceeding, required docs, conditional docs, order, pagination, timing, source citation metadata).

**Step 2:** Implement typed loader + strict validation (fail-fast on missing source URL, duplicate rule IDs, invalid forums).

**Step 3:** Add canonical initial profiles:
- `federal_court_jr_leave`
- `federal_court_jr_hearing`
- `rpd`
- `rad`
- `id`
- `iad`

**Step 4:** Add regression test that enforces non-empty source URLs for every rule.

**Step 5:** Commit.

### Task 2: Expand Intake Model to Preserve Compilation Inputs

**Files:**
- Modify: `src/immcad_api/schemas.py`
- Modify: `src/immcad_api/services/document_matter_store.py`
- Modify: `src/immcad_api/api/routes/documents.py`
- Create: `tests/test_document_compilation_state.py`

**Step 1:** Add failing tests requiring stored per-file extraction/page metadata needed for compilation (total pages, per-page text char counts, optional file hash).

**Step 2:** Extend intake result/state objects without breaking existing API contracts.

**Step 3:** Persist compilation state in store backends (in-memory + Redis) with backward-safe decoding.

**Step 4:** Add migration-safe decoding test for old records.

**Step 5:** Commit.

### Task 3: Build Rule Evaluation Engine (Beyond Missing Doc Types)

**Files:**
- Create: `src/immcad_api/policy/document_compilation_validator.py`
- Modify: `src/immcad_api/services/document_package_service.py`
- Create: `tests/test_document_compilation_validator.py`

**Step 1:** Write failing tests for three violation classes:
- missing required doc
- missing conditional doc (e.g., translation present without declaration)
- structural violation (order/index/pagination requirements unmet)

**Step 2:** Implement validator returning typed violations:
- `violation_code`
- `severity` (`warning`/`blocking`)
- `rule_id`
- `rule_source_url`
- `remediation`

**Step 3:** Wire validator into readiness and package blocking decisions.

**Step 4:** Commit.

### Task 4: Implement Package Assembly Core (TOC + Page Map + Pagination Metadata)

**Files:**
- Create: `src/immcad_api/services/document_assembly_service.py`
- Create: `src/immcad_api/services/pdf_layout.py`
- Create: `tests/test_document_assembly_service.py`

**Step 1:** Write failing tests for compiled sequence calculation:
- deterministic document order
- TOC entries with start page + end page
- monotonic page numbering across package

**Step 2:** Implement assembly planner first (metadata-only, no PDF mutation yet).

**Step 3:** Add optional PDF mutation path (bookmarks + page labels) behind feature flag.

**Step 4:** Add tests for malformed PDFs and mixed image/PDF packages.

**Step 5:** Commit.

### Task 5: Add Forum-Specific Record Builders

**Files:**
- Create: `src/immcad_api/services/record_builders/federal_court_jr.py`
- Create: `src/immcad_api/services/record_builders/rpd.py`
- Create: `src/immcad_api/services/record_builders/rad.py`
- Create: `src/immcad_api/services/record_builders/id.py`
- Create: `src/immcad_api/services/record_builders/iad.py`
- Create: `tests/test_record_builders.py`

**Step 1:** Write failing tests for each builder output shape:
- required sections
- required doc slots
- ordering constraints

**Step 2:** Implement builders consuming shared rule catalog and returning normalized record sections.

**Step 3:** Ensure builders never generate legal advice text; procedural language only.

**Step 4:** Commit.

### Task 6: API Contract Upgrade for Compilation Output

**Files:**
- Modify: `src/immcad_api/schemas.py`
- Modify: `src/immcad_api/api/routes/documents.py`
- Modify: `docs/architecture/document-intake-api-contracts-draft.md`
- Create: `tests/test_document_compilation_routes.py`

**Step 1:** Write failing contract tests for new package fields:
- `toc_entries[]` with page ranges
- `pagination_summary`
- `rule_violations[]` with source URLs
- `compilation_profile` version/id

**Step 2:** Implement route serialization and strict blocking behavior.

**Step 3:** Keep backwards compatibility for existing frontend fields.

**Step 4:** Commit.

### Task 7: Frontend Readiness + Package UX Enhancements

**Files:**
- Modify: `frontend-web/lib/api-client.ts`
- Modify: `frontend-web/components/chat/types.ts`
- Modify: `frontend-web/components/chat/use-chat-logic.ts`
- Modify: `frontend-web/components/chat/related-case-panel.tsx`
- Create: `frontend-web/tests/document-compilation.contract.test.tsx`

**Step 1:** Add failing tests for rendering rule violations, source-linked reasons, and TOC page mapping.

**Step 2:** Implement UI panels:
- “Rule Violations” (blocking/warning)
- “Compilation TOC” (doc -> page range)
- “Why blocked” with actionable remediation

**Step 3:** Add download action only when backend returns compiled artifact metadata (future-safe).

**Step 4:** Commit.

### Task 8: OCR Reliability + Operational Safeguards

**Files:**
- Modify: `src/immcad_api/services/document_extraction.py`
- Modify: `src/immcad_api/telemetry/request_metrics.py`
- Modify: `docs/release/document-intake-security-compliance-checklist.md`
- Create: `tests/test_document_extraction_limits.py`

**Step 1:** Add failing tests for explicit OCR availability state and confidence output.

**Step 2:** Emit deterministic OCR capability flags and per-file confidence class.

**Step 3:** Add metrics for rule-block rates and compilation failure reasons.

**Step 4:** Update release checklist to mark implemented vs pending controls.

**Step 5:** Commit.

### Task 9: End-to-End Verification Matrix

**Files:**
- Create: `tests/test_document_compilation_e2e.py`
- Modify: `Makefile`
- Modify: `tasks/todo.md`

**Step 1:** Add E2E fixtures per forum (happy path + blocked path + translation conditional path).

**Step 2:** Add command target:
- `make test-document-compilation`

**Step 3:** Verify:
- backend tests
- frontend contract tests
- lint/type checks
- backend-vercel source sync

**Step 4:** Record evidence and close plan.

---

## Scope Guardrails
- Do not auto-file to court/IRB in this phase.
- Do not generate legal advice or strategy recommendations.
- Do not claim legal compliance without source-cited, test-backed checks.
- Keep rule engine deterministic; use AI only for assistive classification/extraction.

## Acceptance Criteria
- Every forum/proceeding profile is source-cited and versioned.
- Package output includes deterministic TOC + page mapping.
- Blocking reasons are rule-specific and actionable.
- Translation/declaration and other conditional rules are enforced consistently.
- Existing upload/readiness flows remain backward-compatible.

## Execution Handoff
Plan complete and saved to `docs/plans/2026-02-27-rule-aware-document-compilation-implementation-plan.md`.

Two execution options:

1. Subagent-Driven (this session) - execute task-by-task with review checkpoints.
2. Parallel Session (separate) - execute via `executing-plans` in a dedicated implementation session.

