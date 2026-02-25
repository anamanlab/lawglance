# Lawyer Case Research Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Deliver a grounded lawyer-focused case research workflow that retrieves relevant case law, resolves PDF/document availability, and returns deterministic evidence-rich outputs.

**Architecture:** Add a dedicated lawyer-research orchestration service that builds structured matter queries, retrieves official-first case data, resolves document availability, and returns a strict contract for UI rendering and exports. Integrate this flow through a new API route and frontend panel while preserving existing policy hardening and citation trust behavior.

**Tech Stack:** FastAPI, Pydantic, existing IMMCAD retrieval services (`CaseSearchService`, `OfficialCaseLawClient`, `CanLIIClient`), React/Next.js frontend, pytest, vitest.

---

### Task 1: Define Lawyer Research API Contract

**Skills:** @test-driven-development @documentation

**Files:**
- Modify: `src/immcad_api/schemas.py`
- Modify: `frontend-web/lib/api-client.ts`
- Modify: `frontend-web/components/chat/types.ts`
- Test: `tests/test_lawyer_research_schemas.py`
- Test: `frontend-web/tests/api-client.contract.test.ts`

**Step 1: Write the failing backend schema test**

```python
# tests/test_lawyer_research_schemas.py
from immcad_api.schemas import LawyerCaseResearchRequest


def test_lawyer_case_research_request_accepts_valid_payload():
    payload = LawyerCaseResearchRequest(
        session_id="session-123456",
        matter_summary="Appeal based on procedural fairness in FC immigration decision",
        jurisdiction="ca",
        limit=5,
    )
    assert payload.limit == 5
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest -q tests/test_lawyer_research_schemas.py`
Expected: FAIL with import/name error for `LawyerCaseResearchRequest`.

**Step 3: Implement minimal schema models**

```python
# src/immcad_api/schemas.py
class LawyerCaseResearchRequest(BaseModel):
    session_id: str = Field(min_length=8, max_length=128)
    matter_summary: str = Field(min_length=10, max_length=12000)
    jurisdiction: str = Field(default="ca", max_length=16)
    court: str | None = Field(default=None, max_length=32)
    limit: int = Field(default=10, ge=1, le=25)
```

**Step 4: Add response models and frontend types**

```python
# src/immcad_api/schemas.py
class LawyerCaseSupport(BaseModel):
    case_id: str
    title: str
    citation: str
    court: str | None = None
    decision_date: date
    url: str
    document_url: str | None = None
    pdf_status: Literal["available", "unavailable"]
    relevance_reason: str
    summary: str | None = None


class LawyerCaseResearchResponse(BaseModel):
    matter_profile: dict[str, list[str] | str | None]
    cases: list[LawyerCaseSupport]
    source_status: dict[str, str]
```

```ts
// frontend-web/lib/api-client.ts
export type LawyerCaseResearchRequestPayload = {
  session_id: string;
  matter_summary: string;
  jurisdiction?: string;
  court?: string;
  limit?: number;
};
```

**Step 5: Run tests and commit**

Run:
- `uv run pytest -q tests/test_lawyer_research_schemas.py`
- `npm run test --prefix frontend-web -- tests/api-client.contract.test.ts`

Expected: PASS

Commit:
```bash
git add src/immcad_api/schemas.py tests/test_lawyer_research_schemas.py frontend-web/lib/api-client.ts frontend-web/components/chat/types.ts frontend-web/tests/api-client.contract.test.ts
git commit -m "feat(research): add lawyer case research request/response contract"
```

### Task 2: Build Matter Extractor + Query Planner

**Skills:** @test-driven-development @prompt-engineering-patterns

**Files:**
- Create: `src/immcad_api/services/lawyer_research_planner.py`
- Test: `tests/test_lawyer_research_planner.py`

**Step 1: Write failing planner tests**

```python
# tests/test_lawyer_research_planner.py
from immcad_api.services.lawyer_research_planner import build_research_queries


def test_build_research_queries_expands_matter_into_multiple_queries():
    queries = build_research_queries(
        "FC appeal on procedural fairness and inadmissibility finding",
        court="fc",
    )
    assert len(queries) >= 3
    assert any("procedural fairness" in query.lower() for query in queries)
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest -q tests/test_lawyer_research_planner.py`
Expected: FAIL with missing module/function.

**Step 3: Implement minimal planner**

```python
# src/immcad_api/services/lawyer_research_planner.py
def build_research_queries(matter_summary: str, court: str | None = None) -> list[str]:
    normalized = matter_summary.strip()
    queries = [normalized]
    if court:
        queries.append(f"{normalized} {court} precedent")
    queries.append(f"{normalized} immigration judicial review")
    return list(dict.fromkeys(query for query in queries if query.strip()))
```

**Step 4: Add structured matter-profile extraction**

```python
# src/immcad_api/services/lawyer_research_planner.py
def extract_matter_profile(matter_summary: str) -> dict[str, list[str] | str | None]:
    text = matter_summary.lower()
    issue_tags = []
    if "procedural fairness" in text:
        issue_tags.append("procedural_fairness")
    if "inadmiss" in text:
        issue_tags.append("inadmissibility")
    return {
        "issue_tags": issue_tags,
        "target_court": "fc" if "federal court" in text or " fc " in f" {text} " else None,
        "fact_keywords": [token for token in text.split() if len(token) > 4][:12],
    }
```

**Step 5: Run tests and commit**

Run: `uv run pytest -q tests/test_lawyer_research_planner.py`
Expected: PASS

Commit:
```bash
git add src/immcad_api/services/lawyer_research_planner.py tests/test_lawyer_research_planner.py
git commit -m "feat(research): add matter extractor and multi-query planner"
```

### Task 3: Implement Lawyer Case Research Orchestrator

**Skills:** @test-driven-development @error-handling-patterns

**Files:**
- Create: `src/immcad_api/services/lawyer_case_research_service.py`
- Modify: `src/immcad_api/services/__init__.py`
- Test: `tests/test_lawyer_case_research_service.py`

**Step 1: Write failing orchestrator tests**

```python
# tests/test_lawyer_case_research_service.py
from immcad_api.services.lawyer_case_research_service import LawyerCaseResearchService


def test_orchestrator_merges_results_and_deduplicates():
    service = LawyerCaseResearchService(...)
    response = service.research(...)
    assert len(response.cases) > 0
    assert len({case.citation for case in response.cases}) == len(response.cases)
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest -q tests/test_lawyer_case_research_service.py`
Expected: FAIL with missing service.

**Step 3: Implement minimal service wiring**

```python
# src/immcad_api/services/lawyer_case_research_service.py
class LawyerCaseResearchService:
    def __init__(self, *, case_search_service: CaseSearchService) -> None:
        self.case_search_service = case_search_service

    def research(self, request: LawyerCaseResearchRequest) -> LawyerCaseResearchResponse:
        queries = build_research_queries(request.matter_summary, court=request.court)
        merged: list[CaseSearchResult] = []
        for query in queries:
            result = self.case_search_service.search(
                CaseSearchRequest(query=query, jurisdiction=request.jurisdiction, court=request.court, limit=request.limit)
            )
            merged.extend(result.results)
        # dedupe + rank placeholder
        ...
```

**Step 4: Add deterministic ranking and evidence reasons**

```python
# src/immcad_api/services/lawyer_case_research_service.py
# score by token overlap, court match, citation recency
# attach relevance_reason string per case
```

**Step 5: Run tests and commit**

Run: `uv run pytest -q tests/test_lawyer_case_research_service.py`
Expected: PASS

Commit:
```bash
git add src/immcad_api/services/lawyer_case_research_service.py src/immcad_api/services/__init__.py tests/test_lawyer_case_research_service.py
git commit -m "feat(research): add lawyer case research orchestrator"
```

### Task 4: Add PDF/Document Availability Resolver

**Skills:** @test-driven-development @security-practices

**Files:**
- Create: `src/immcad_api/services/case_document_resolver.py`
- Test: `tests/test_case_document_resolver.py`
- Modify: `src/immcad_api/services/lawyer_case_research_service.py`

**Step 1: Write failing resolver tests**

```python
# tests/test_case_document_resolver.py
from immcad_api.services.case_document_resolver import resolve_pdf_status


def test_resolve_pdf_status_marks_unavailable_when_document_url_missing():
    status = resolve_pdf_status(document_url=None, source_url="https://decisions.fct-cf.gc.ca")
    assert status == "unavailable"
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest -q tests/test_case_document_resolver.py`
Expected: FAIL with missing resolver.

**Step 3: Implement minimal resolver**

```python
# src/immcad_api/services/case_document_resolver.py
def resolve_pdf_status(document_url: str | None, source_url: str) -> str:
    if not document_url:
        return "unavailable"
    # host trust + extension/content hint checks
    return "available"
```

**Step 4: Integrate resolver into orchestrator response mapping**

```python
# src/immcad_api/services/lawyer_case_research_service.py
pdf_status = resolve_pdf_status(document_url=result.document_url, source_url=str(source_entry.url))
```

**Step 5: Run tests and commit**

Run:
- `uv run pytest -q tests/test_case_document_resolver.py`
- `uv run pytest -q tests/test_lawyer_case_research_service.py`

Expected: PASS

Commit:
```bash
git add src/immcad_api/services/case_document_resolver.py src/immcad_api/services/lawyer_case_research_service.py tests/test_case_document_resolver.py tests/test_lawyer_case_research_service.py
git commit -m "feat(research): resolve case document pdf availability"
```

### Task 5: Add Lawyer Research API Route

**Skills:** @test-driven-development @api-security-best-practices

**Files:**
- Create: `src/immcad_api/api/routes/lawyer_research.py`
- Modify: `src/immcad_api/api/routes/__init__.py`
- Modify: `src/immcad_api/main.py`
- Test: `tests/test_lawyer_research_api.py`

**Step 1: Write failing API contract test**

```python
# tests/test_lawyer_research_api.py
from fastapi.testclient import TestClient
from immcad_api.main import create_app


def test_lawyer_research_endpoint_returns_structured_cases():
    client = TestClient(create_app())
    response = client.post("/api/research/lawyer-cases", json={...})
    assert response.status_code == 200
    assert "cases" in response.json()
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest -q tests/test_lawyer_research_api.py`
Expected: FAIL with 404.

**Step 3: Implement route**

```python
# src/immcad_api/api/routes/lawyer_research.py
@router.post("/research/lawyer-cases", response_model=LawyerCaseResearchResponse)
def lawyer_case_research(payload: LawyerCaseResearchRequest, request: Request):
    ...
```

**Step 4: Wire router into app**

```python
# src/immcad_api/main.py
app.include_router(build_lawyer_research_router(...))
```

**Step 5: Run tests and commit**

Run:
- `uv run pytest -q tests/test_lawyer_research_api.py`
- `uv run pytest -q tests/test_api_scaffold.py`

Expected: PASS

Commit:
```bash
git add src/immcad_api/api/routes/lawyer_research.py src/immcad_api/api/routes/__init__.py src/immcad_api/main.py tests/test_lawyer_research_api.py
git commit -m "feat(api): add lawyer case research endpoint"
```

### Task 6: Frontend Lawyer Research Flow

**Skills:** @test-driven-development @frontend-design

**Files:**
- Create: `frontend-web/components/chat/lawyer-research-panel.tsx`
- Modify: `frontend-web/components/chat/chat-shell-container.tsx`
- Modify: `frontend-web/lib/api-client.ts`
- Modify: `frontend-web/components/chat/types.ts`
- Test: `frontend-web/tests/chat-shell.contract.test.tsx`
- Test: `frontend-web/tests/api-client.contract.test.ts`

**Step 1: Write failing frontend contract tests**

```ts
// frontend-web/tests/chat-shell.contract.test.tsx
it("renders lawyer research results with pdf status badges", async () => {
  ...
  expect(screen.getByText("PDF available")).toBeInTheDocument();
});
```

**Step 2: Run test to verify it fails**

Run: `npm run test --prefix frontend-web -- tests/chat-shell.contract.test.tsx`
Expected: FAIL (missing UI component/contract).

**Step 3: Implement minimal API client method**

```ts
// frontend-web/lib/api-client.ts
async function researchLawyerCases(payload: LawyerCaseResearchRequestPayload) {
  return postJson<LawyerCaseResearchResponsePayload>(options, "/research/lawyer-cases", payload);
}
```

**Step 4: Implement panel and integrate into chat shell**

```tsx
// frontend-web/components/chat/lawyer-research-panel.tsx
// render title, citation, relevance reason, pdf status, link
```

**Step 5: Run tests and commit**

Run:
- `npm run test --prefix frontend-web -- tests/chat-shell.contract.test.tsx tests/api-client.contract.test.ts`
- `npm run typecheck --prefix frontend-web`

Expected: PASS

Commit:
```bash
git add frontend-web/components/chat/lawyer-research-panel.tsx frontend-web/components/chat/chat-shell-container.tsx frontend-web/lib/api-client.ts frontend-web/components/chat/types.ts frontend-web/tests/chat-shell.contract.test.tsx frontend-web/tests/api-client.contract.test.ts
git commit -m "feat(frontend): add lawyer case research panel and api integration"
```

### Task 7: Observability + Guardrails + Docs

**Skills:** @documentation @reliability-engineering

**Files:**
- Modify: `src/immcad_api/telemetry/request_metrics.py` (or relevant telemetry module)
- Modify: `tests/test_api_scaffold.py`
- Modify: `docs/architecture/api-contracts.md`
- Modify: `docs/development-environment.md`

**Step 1: Write failing telemetry test**

```python
# tests/test_api_scaffold.py
# assert lawyer research metrics fields are present in /ops/metrics snapshot
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest -q tests/test_api_scaffold.py -k lawyer`
Expected: FAIL (missing metrics fields).

**Step 3: Implement metrics fields**

```python
# add counters: retrieval_candidates_count, relevant_cases_count,
# pdf_available_count, pdf_unavailable_count, source_errors
```

**Step 4: Update docs/contracts**

```markdown
# docs/architecture/api-contracts.md
Add /api/research/lawyer-cases request/response examples and evidence-state definitions.
```

**Step 5: Run full verification and commit**

Run:
- `uv run pytest -q tests/test_lawyer_research_schemas.py tests/test_lawyer_research_planner.py tests/test_lawyer_case_research_service.py tests/test_case_document_resolver.py tests/test_lawyer_research_api.py tests/test_api_scaffold.py`
- `npm run test --prefix frontend-web -- tests/chat-shell.contract.test.tsx tests/api-client.contract.test.ts`
- `make quality`

Expected: PASS

Commit:
```bash
git add src/immcad_api/telemetry docs/architecture/api-contracts.md docs/development-environment.md tests/test_api_scaffold.py
git commit -m "chore(research): add lawyer research telemetry and documentation"
```

### Task 8: Release Readiness Validation

**Skills:** @reliability-engineering @requesting-code-review

**Files:**
- Modify: `docs/release/known-issues.md`
- Modify: `tasks/todo.md`
- Test: `tests/test_quality_gates_workflow.py`
- Test: `tests/test_release_gates_workflow.py`

**Step 1: Add failing regression if workflow gating is missing new tests**

```python
# tests/test_quality_gates_workflow.py
# assert new lawyer research tests are covered by CI commands
```

**Step 2: Run tests to confirm failure**

Run: `uv run pytest -q tests/test_quality_gates_workflow.py tests/test_release_gates_workflow.py`
Expected: FAIL until workflow includes coverage.

**Step 3: Update workflows if needed**

```yaml
# .github/workflows/quality-gates.yml
# include new backend/frontend lawyer research tests in gate command blocks
```

**Step 4: Update issue tracker/task plan evidence**

```markdown
# docs/release/known-issues.md
Close migration/readiness items only after evidence commands pass.
```

**Step 5: Run final validation and commit**

Run:
- `uv run pytest -q tests/test_quality_gates_workflow.py tests/test_release_gates_workflow.py`
- `make quality`
- `npm run cf:build --prefix frontend-web`

Expected: PASS

Commit:
```bash
git add .github/workflows/quality-gates.yml .github/workflows/release-gates.yml tests/test_quality_gates_workflow.py tests/test_release_gates_workflow.py docs/release/known-issues.md tasks/todo.md
git commit -m "chore(research): enforce lawyer research readiness gates"
```
