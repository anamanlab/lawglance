# Canada Document Intake + Filing Readiness Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Ship a production-safe document intake workflow where clients can bulk upload documents, the system performs OCR/quality understanding, organizes files, generates filing artifacts (TOC/index + cover letter/disclosure draft), and blocks final package readiness when rule-critical issues remain.

**Architecture:** Add a new document-intake domain slice to the existing FastAPI backend with deterministic rule-checking for Federal Court and IRB divisions. Implement a pipeline: upload -> extraction/OCR -> classification -> quality/rule checks -> package generation. Expose this via new `/api/documents/*` routes and integrate a frontend intake panel for drag-and-drop multi-file upload with clear error states and review workflow.

**Tech Stack:** Python 3.11+, FastAPI, Pydantic, PyMuPDF, existing provider stack, pytest, Next.js frontend, Vitest.

---

## Execution Rules
- Use `@test-driven-development` for all behavior changes.
- If any test fails unexpectedly, apply `@systematic-debugging` before implementation edits.
- Before completion claims, run `@verification-before-completion` and capture evidence in `tasks/todo.md`.

### Task 1: Add Filing Rule Catalog + Readiness Policy Engine

**Files:**
- Create: `src/immcad_api/policy/document_requirements.py`
- Modify: `src/immcad_api/policy/__init__.py`
- Test: `tests/test_document_requirements.py`

**Step 1: Write the failing tests**

```python
from immcad_api.policy.document_requirements import (
    FilingForum,
    evaluate_readiness,
)


def test_fc_rule_309_requires_decision_affidavit_memorandum() -> None:
    readiness = evaluate_readiness(
        forum=FilingForum.FEDERAL_COURT_JR,
        classified_doc_types={"notice_of_application", "decision_under_review"},
    )
    assert readiness.is_ready is False
    assert "affidavit" in " ".join(readiness.missing_required_items).lower()


def test_rpd_requires_translation_declaration_when_translation_present() -> None:
    readiness = evaluate_readiness(
        forum=FilingForum.RPD,
        classified_doc_types={"identity_document", "translation"},
    )
    assert readiness.is_ready is False
    assert any("translator" in item.lower() for item in readiness.missing_required_items)
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src uv run pytest -q tests/test_document_requirements.py`
Expected: FAIL with missing module/symbols.

**Step 3: Write minimal implementation**

```python
class FilingForum(str, Enum):
    FEDERAL_COURT_JR = "federal_court_jr"
    RPD = "rpd"
    RAD = "rad"
    IAD = "iad"
    ID = "id"

@dataclass(frozen=True)
class ReadinessResult:
    is_ready: bool
    missing_required_items: tuple[str, ...]
    warnings: tuple[str, ...] = ()

def evaluate_readiness(...):
    # deterministic required-item set per forum
    ...
```

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src uv run pytest -q tests/test_document_requirements.py`
Expected: PASS.

**Step 5: Commit**

```bash
git add src/immcad_api/policy/document_requirements.py src/immcad_api/policy/__init__.py tests/test_document_requirements.py
git commit -m "feat(policy): add filing readiness requirements engine"
```

### Task 2: Add Intake Schemas and API Contracts

**Files:**
- Modify: `src/immcad_api/schemas.py`
- Test: `tests/test_document_intake_schemas.py`

**Step 1: Write the failing tests**

```python
from immcad_api.schemas import DocumentIntakeResult, DocumentReadinessResponse


def test_document_intake_result_requires_quality_and_classification() -> None:
    result = DocumentIntakeResult(
        file_id="file-1",
        original_filename="scan.pdf",
        normalized_filename="affidavit-smith-2026-01-01.pdf",
        classification="affidavit",
        quality_status="needs_review",
        issues=["ocr_low_confidence"],
    )
    assert result.classification == "affidavit"


def test_readiness_response_exposes_blocking_issues() -> None:
    response = DocumentReadinessResponse(
        matter_id="matter-1",
        forum="federal_court_jr",
        is_ready=False,
        missing_required_items=["memorandum"],
        blocking_issues=["illegible_pages"],
    )
    assert response.is_ready is False
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src uv run pytest -q tests/test_document_intake_schemas.py`
Expected: FAIL with undefined schema types.

**Step 3: Write minimal implementation**

Add Pydantic models:
- `DocumentIntakeInitRequest`
- `DocumentIntakeResult`
- `DocumentIssue`
- `DocumentReadinessResponse`
- `DocumentPackageResponse`

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src uv run pytest -q tests/test_document_intake_schemas.py`
Expected: PASS.

**Step 5: Commit**

```bash
git add src/immcad_api/schemas.py tests/test_document_intake_schemas.py
git commit -m "feat(schemas): add document intake and readiness contracts"
```

### Task 3: Implement Backend Intake Pipeline Service (Extraction + OCR Signals + Classification)

**Files:**
- Create: `src/immcad_api/services/document_intake_service.py`
- Create: `src/immcad_api/services/document_extraction.py`
- Modify: `src/immcad_api/services/__init__.py`
- Test: `tests/test_document_intake_service.py`

**Step 1: Write the failing tests**

```python
from immcad_api.services.document_intake_service import DocumentIntakeService


def test_pipeline_flags_image_only_pdf_for_ocr_review(tmp_path) -> None:
    service = DocumentIntakeService(...)
    result = service.process_file(...)
    assert "ocr_required" in result.issues


def test_pipeline_assigns_normalized_filename_from_classification(tmp_path) -> None:
    service = DocumentIntakeService(...)
    result = service.process_file(...)
    assert result.normalized_filename.endswith(".pdf")
    assert "affidavit" in result.normalized_filename
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src uv run pytest -q tests/test_document_intake_service.py`
Expected: FAIL with missing service module.

**Step 3: Write minimal implementation**

Implement service pipeline:
- `extract_text_and_page_signals(pdf_bytes)` using PyMuPDF.
- If extractable text is too low, emit `ocr_required` or `ocr_low_confidence` issue.
- Lightweight deterministic classifier (keyword/rule-based MVP) for doc type.
- Filename normalizer: `<doc-type>-<party-or-source>-<date>-<shortid>.pdf`.

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src uv run pytest -q tests/test_document_intake_service.py`
Expected: PASS.

**Step 5: Commit**

```bash
git add src/immcad_api/services/document_intake_service.py src/immcad_api/services/document_extraction.py src/immcad_api/services/__init__.py tests/test_document_intake_service.py
git commit -m "feat(intake): add document extraction quality checks and naming"
```

### Task 4: Implement TOC/Disclosure/Cover-Letter Draft Package Builder

**Files:**
- Create: `src/immcad_api/services/document_package_service.py`
- Test: `tests/test_document_package_service.py`

**Step 1: Write the failing tests**

```python
from immcad_api.services.document_package_service import DocumentPackageService


def test_package_builder_generates_toc_ordered_by_rule_priority() -> None:
    service = DocumentPackageService(...)
    package = service.build_package(...)
    assert package.table_of_contents[0].document_type == "notice_of_application"


def test_package_builder_generates_cover_letter_draft_with_missing_items_note() -> None:
    service = DocumentPackageService(...)
    package = service.build_package(...)
    assert "missing" in package.cover_letter_draft.lower()
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src uv run pytest -q tests/test_document_package_service.py`
Expected: FAIL due missing service.

**Step 3: Write minimal implementation**

Implement `build_package` returning:
- ordered TOC entries,
- disclosure checklist aligned to selected forum,
- cover letter draft template with unresolved issue section,
- readiness summary from policy engine.

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src uv run pytest -q tests/test_document_package_service.py`
Expected: PASS.

**Step 5: Commit**

```bash
git add src/immcad_api/services/document_package_service.py tests/test_document_package_service.py
git commit -m "feat(packaging): add toc disclosure and cover-letter draft builder"
```

### Task 5: Add Document Intake API Routes

**Files:**
- Create: `src/immcad_api/api/routes/documents.py`
- Modify: `src/immcad_api/api/routes/__init__.py`
- Modify: `src/immcad_api/main.py`
- Test: `tests/test_document_routes.py`

**Step 1: Write the failing tests**

```python
def test_documents_intake_accepts_multipart_upload(client) -> None:
    response = client.post("/api/documents/intake", files={...}, data={"forum": "federal_court_jr"})
    assert response.status_code == 200
    assert response.json()["results"]


def test_documents_package_blocks_when_blocking_issues_present(client) -> None:
    response = client.post("/api/documents/matters/matter-1/package")
    assert response.status_code == 409
    assert response.json()["error"]["policy_reason"] == "document_package_not_ready"
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src uv run pytest -q tests/test_document_routes.py`
Expected: FAIL because routes are not registered.

**Step 3: Write minimal implementation**

Routes:
- `POST /api/documents/intake` (multipart, multi-file)
- `GET /api/documents/matters/{matter_id}/readiness`
- `POST /api/documents/matters/{matter_id}/package`

Ensure:
- trace-id headers,
- consistent `ErrorEnvelope` shape,
- threadpool wrapping for CPU-heavy parsing.

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src uv run pytest -q tests/test_document_routes.py`
Expected: PASS.

**Step 5: Commit**

```bash
git add src/immcad_api/api/routes/documents.py src/immcad_api/api/routes/__init__.py src/immcad_api/main.py tests/test_document_routes.py
git commit -m "feat(api): add document intake readiness and package routes"
```

### Task 6: Add Secure Upload Controls and Audit Events

**Files:**
- Modify: `src/immcad_api/settings.py`
- Modify: `src/immcad_api/main.py`
- Modify: `src/immcad_api/telemetry/request_metrics.py`
- Test: `tests/test_document_upload_security.py`

**Step 1: Write the failing tests**

```python
def test_upload_rejects_unsupported_content_type(client) -> None:
    response = client.post("/api/documents/intake", files={"files": ("payload.exe", b"MZ", "application/octet-stream")})
    assert response.status_code == 422


def test_upload_rejects_oversized_payload(client, monkeypatch) -> None:
    monkeypatch.setenv("DOCUMENT_UPLOAD_MAX_BYTES", "1024")
    response = client.post(...)
    assert response.status_code in {413, 422}
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src uv run pytest -q tests/test_document_upload_security.py`
Expected: FAIL with missing guards.

**Step 3: Write minimal implementation**

Add guardrails:
- file type allowlist (`application/pdf`, image types for OCR intake),
- max bytes limit,
- per-request file count cap,
- structured audit event for each file: ingest status, issue summary, trace id.

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src uv run pytest -q tests/test_document_upload_security.py`
Expected: PASS.

**Step 5: Commit**

```bash
git add src/immcad_api/settings.py src/immcad_api/main.py src/immcad_api/telemetry/request_metrics.py tests/test_document_upload_security.py
git commit -m "feat(security): add upload size type limits and intake audit events"
```

### Task 7: Add Frontend Upload + Review Panel

**Files:**
- Create: `frontend-web/components/documents/document-intake-panel.tsx`
- Create: `frontend-web/components/documents/document-readiness-card.tsx`
- Modify: `frontend-web/components/chat/chat-shell.tsx`
- Modify: `frontend-web/lib/api-client.ts`
- Modify: `frontend-web/components/chat/types.ts`
- Test: `frontend-web/tests/document-intake-panel.ui.test.tsx`
- Test: `frontend-web/tests/api-client.contract.test.ts`

**Step 1: Write the failing tests**

```tsx
test("supports drag-and-drop multi-file upload with minimal required fields", async () => {
  render(<DocumentIntakePanel ... />);
  expect(screen.getByText(/drag and drop/i)).toBeInTheDocument();
  await user.upload(screen.getByLabelText(/upload documents/i), [fileA, fileB]);
  expect(await screen.findByText(/2 files uploaded/i)).toBeInTheDocument();
});

test("renders blocking readiness issues clearly", async () => {
  render(<DocumentReadinessCard readiness={mockNotReady} />);
  expect(screen.getByText(/not ready/i)).toBeInTheDocument();
  expect(screen.getByText(/missing required items/i)).toBeInTheDocument();
});
```

**Step 2: Run test to verify it fails**

Run: `cd frontend-web && npm run test -- --run tests/document-intake-panel.ui.test.tsx tests/api-client.contract.test.ts`
Expected: FAIL due missing components/client methods.

**Step 3: Write minimal implementation**

Implement frontend UX:
- forum selector + drag/drop area,
- batch upload progress,
- per-document status (ok/needs_review/failed),
- readiness card and package generation button.

API client methods:
- `uploadMatterDocuments(...)`
- `getMatterReadiness(...)`
- `buildMatterPackage(...)`

**Step 4: Run test to verify it passes**

Run: `cd frontend-web && npm run test -- --run tests/document-intake-panel.ui.test.tsx tests/api-client.contract.test.ts`
Expected: PASS.

**Step 5: Commit**

```bash
git add frontend-web/components/documents/document-intake-panel.tsx frontend-web/components/documents/document-readiness-card.tsx frontend-web/components/chat/chat-shell.tsx frontend-web/lib/api-client.ts frontend-web/components/chat/types.ts frontend-web/tests/document-intake-panel.ui.test.tsx frontend-web/tests/api-client.contract.test.ts
git commit -m "feat(frontend): add document intake upload and readiness panel"
```

### Task 8: End-to-End Readiness Flow and Regression Checks

**Files:**
- Create: `tests/test_document_intake_e2e_flow.py`
- Modify: `tasks/todo.md` (verification evidence)

**Step 1: Write the failing tests**

```python
def test_e2e_document_flow_upload_to_package_ready(client) -> None:
    intake = client.post("/api/documents/intake", ...)
    assert intake.status_code == 200

    readiness = client.get(f"/api/documents/matters/{matter_id}/readiness")
    assert readiness.status_code == 200

    package = client.post(f"/api/documents/matters/{matter_id}/package")
    assert package.status_code in {200, 409}
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src uv run pytest -q tests/test_document_intake_e2e_flow.py`
Expected: FAIL before full route/service wiring is complete.

**Step 3: Write minimal implementation adjustments**

Fix integration gaps across route/service/package builder and ensure deterministic response envelopes.

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src uv run pytest -q tests/test_document_intake_e2e_flow.py`
Expected: PASS.

**Step 5: Commit**

```bash
git add tests/test_document_intake_e2e_flow.py
git commit -m "test(intake): add e2e upload readiness package flow"
```

### Task 9: Final Verification Gate

**Files:**
- Modify: `tasks/todo.md` (review evidence section)

**Step 1: Run backend targeted tests**

Run:
`PYTHONPATH=src uv run pytest -q tests/test_document_requirements.py tests/test_document_intake_schemas.py tests/test_document_intake_service.py tests/test_document_package_service.py tests/test_document_routes.py tests/test_document_upload_security.py tests/test_document_intake_e2e_flow.py`
Expected: PASS.

**Step 2: Run backend lint checks for touched files**

Run:
`uv run ruff check src/immcad_api/policy/document_requirements.py src/immcad_api/services/document_intake_service.py src/immcad_api/services/document_extraction.py src/immcad_api/services/document_package_service.py src/immcad_api/api/routes/documents.py src/immcad_api/schemas.py src/immcad_api/settings.py tests/test_document_requirements.py tests/test_document_intake_schemas.py tests/test_document_intake_service.py tests/test_document_package_service.py tests/test_document_routes.py tests/test_document_upload_security.py tests/test_document_intake_e2e_flow.py`
Expected: PASS.

**Step 3: Run frontend checks**

Run:
- `cd frontend-web && npm run test -- --run tests/document-intake-panel.ui.test.tsx tests/api-client.contract.test.ts`
- `cd frontend-web && npm run lint`
- `cd frontend-web && npm run typecheck`

Expected: PASS.

**Step 4: Update review evidence**

Add command outputs and results to `tasks/todo.md` under the active task section.

**Step 5: Commit**

```bash
git add tasks/todo.md
git commit -m "chore(verification): record document intake readiness verification evidence"
```

---

## Scope Guardrails (Keep V1 Lean)
- Do not implement cloud object storage in V1; keep storage abstraction ready but local/dev-backed initially.
- Do not auto-file to court/IRB in V1.
- Do not generate legal advice; generate structured procedural drafts only.
- Prefer deterministic rules for readiness gates over model-only judgments.

## Risks and Mitigations
1. OCR quality variability on scanned uploads.
- Mitigation: page-level quality scoring, `needs_review` status, and explicit re-upload prompts.
2. Over-classification errors for uncommon document types.
- Mitigation: confidence thresholds + “unclassified” fallback and manual override path.
3. Procedural rule drift over time.
- Mitigation: isolate requirement catalog in one policy module with date/version metadata and regression tests.

