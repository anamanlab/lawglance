# Research Precedent Retrieval (Backend-First) Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Improve backend precedent retrieval quality and reliability through intent-gated auto research, stronger query planning/ranking, and refined case-query validation behavior.

**Architecture:** Keep current source clients and route structure, but add a graded case-query assessment layer, stronger lawyer-research planning/ranking signals, and an optional chat response `research_preview` contract produced only when precedent intent is detected. Maintain deterministic fallback/status behavior and non-breaking optional response fields.

**Tech Stack:** Python 3.11+, FastAPI, Pydantic, pytest, existing IMMCAD services/routes/schemas.

---

## Execution Rules
- Use `@test-driven-development` for every behavior change.
- If a test fails unexpectedly, apply `@systematic-debugging` before code changes.
- Before completion claims, run `@verification-before-completion` checks and capture evidence in `tasks/todo.md`.

### Task 1: Add Graded Case-Query Assessment Primitives

**Files:**
- Modify: `src/immcad_api/api/routes/case_query_validation.py`
- Test: `tests/test_case_query_validation.py`

**Step 1: Write the failing tests**

```python
from immcad_api.api.routes.case_query_validation import assess_case_query


def test_case_query_assessment_reports_specific_query_with_no_hints() -> None:
    assessment = assess_case_query("Federal Court JR on H&C refusal 2024 FC 101")
    assert assessment.is_specific is True
    assert assessment.hints == []


def test_case_query_assessment_reports_broad_query_with_refinement_hints() -> None:
    assessment = assess_case_query("help with immigration")
    assert assessment.is_specific is False
    assert "court" in " ".join(assessment.hints).lower()
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src uv run pytest -q tests/test_case_query_validation.py`
Expected: FAIL with `ImportError` or missing `assess_case_query` symbol.

**Step 3: Write minimal implementation**

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class CaseQueryAssessment:
    is_specific: bool
    hints: list[str]


def assess_case_query(query: str) -> CaseQueryAssessment:
    is_specific = is_specific_case_query(query)
    if is_specific:
        return CaseQueryAssessment(is_specific=True, hints=[])
    return CaseQueryAssessment(
        is_specific=False,
        hints=[
            "Add a court (FC, FCA, SCC) or citation.",
            "Add issue terms (procedural fairness, inadmissibility, etc.).",
        ],
    )
```

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src uv run pytest -q tests/test_case_query_validation.py`
Expected: PASS.

**Step 5: Commit**

```bash
git add tests/test_case_query_validation.py src/immcad_api/api/routes/case_query_validation.py
git commit -m "feat(case-query): add graded query assessment hints"
```

### Task 2: Wire Graded Assessment into Case/Lawyer Research Routes

**Files:**
- Modify: `src/immcad_api/api/routes/cases.py`
- Modify: `src/immcad_api/api/routes/lawyer_research.py`
- Test: `tests/test_lawyer_research_api.py`
- Test: `tests/test_api_scaffold.py`

**Step 1: Write the failing tests**

```python
def test_lawyer_research_endpoint_includes_refinement_hint_for_broad_query() -> None:
    response = client.post("/api/research/lawyer-cases", json={... broad payload ...})
    assert response.status_code == 422
    assert "Add" in response.json()["error"]["message"]


def test_case_search_endpoint_includes_refinement_hint_for_broad_query() -> None:
    response = client.post("/api/search/cases", json={... broad payload ...})
    assert response.status_code == 422
    assert "citation" in response.json()["error"]["message"].lower()
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src uv run pytest -q tests/test_lawyer_research_api.py tests/test_api_scaffold.py -k broad`
Expected: FAIL because current message does not include refinement hints.

**Step 3: Write minimal implementation**

```python
assessment = assess_case_query(payload.query)
if not assessment.is_specific:
    hint_text = " ".join(assessment.hints)
    return _error_response(..., message=f"Case-law query is too broad. {hint_text}", ...)
```

Apply same pattern for `payload.matter_summary` in lawyer research route.

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src uv run pytest -q tests/test_lawyer_research_api.py tests/test_api_scaffold.py -k broad`
Expected: PASS.

**Step 5: Commit**

```bash
git add src/immcad_api/api/routes/cases.py src/immcad_api/api/routes/lawyer_research.py tests/test_lawyer_research_api.py tests/test_api_scaffold.py
git commit -m "feat(api): include query refinement hints on case-law validation errors"
```

### Task 3: Strengthen Lawyer Research Query Expansion

**Files:**
- Modify: `src/immcad_api/services/lawyer_research_planner.py`
- Test: `tests/test_lawyer_research_planner.py`
- Test: `tests/test_lawyer_case_research_service.py`

**Step 1: Write the failing tests**

```python
def test_build_research_queries_includes_citation_and_posture_variants() -> None:
    queries = build_research_queries("2024 FC 101 judicial review on procedural fairness", court="fc")
    assert any("2024 fc 101" in query.lower() for query in queries)
    assert any("judicial review" in query.lower() for query in queries)
    assert len(queries) >= 4
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src uv run pytest -q tests/test_lawyer_research_planner.py`
Expected: FAIL on missing richer query variants.

**Step 3: Write minimal implementation**

```python
# Add citation/docket extraction + structured variant generation
# Keep dedupe and max-length safety.
queries.append(f"{citation_fragment} {target_court} precedent")
queries.append(f"{issue_fragment} {procedural_posture_fragment} immigration")
```

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src uv run pytest -q tests/test_lawyer_research_planner.py tests/test_lawyer_case_research_service.py -k planner`
Expected: PASS.

**Step 5: Commit**

```bash
git add src/immcad_api/services/lawyer_research_planner.py tests/test_lawyer_research_planner.py tests/test_lawyer_case_research_service.py
git commit -m "feat(research): expand lawyer query planner variants for precedent retrieval"
```

### Task 4: Improve Precedent Relevance Ranking Signals

**Files:**
- Modify: `src/immcad_api/services/lawyer_case_research_service.py`
- Test: `tests/test_lawyer_case_research_service.py`

**Step 1: Write the failing tests**

```python
def test_research_ranking_prioritizes_court_and_citation_match() -> None:
    response = service.research(request)
    assert response.cases[0].citation == "2024 FC 101"


def test_research_ranking_prefers_issue_aligned_case_over_token_only_case() -> None:
    response = service.research(request)
    assert "procedural fairness" in response.cases[0].relevance_reason.lower()
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src uv run pytest -q tests/test_lawyer_case_research_service.py -k ranking`
Expected: FAIL due current token-only ranking bias.

**Step 3: Write minimal implementation**

```python
# Extend _score_case with weighted signals:
# - exact citation/docket match bonus
# - court-target match bonus
# - issue-tag alignment bonus
# - recency tie-break
```

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src uv run pytest -q tests/test_lawyer_case_research_service.py`
Expected: PASS.

**Step 5: Commit**

```bash
git add src/immcad_api/services/lawyer_case_research_service.py tests/test_lawyer_case_research_service.py
git commit -m "feat(research): improve precedent relevance ranking signals"
```

### Task 5: Add Intent-Gated Auto Research Preview to Chat Contract

**Files:**
- Modify: `src/immcad_api/schemas.py`
- Modify: `src/immcad_api/services/chat_service.py`
- Modify: `src/immcad_api/main.py`
- Modify: `src/immcad_api/api/routes/chat.py` (only if response model wiring needs adjustment)
- Test: `tests/test_chat_service.py`
- Test: `tests/test_api_scaffold.py`

**Step 1: Write the failing tests**

```python
def test_chat_response_includes_auto_research_preview_for_precedent_intent() -> None:
    response = chat_service.handle_chat(request, trace_id="trace-1")
    assert response.research_preview is not None
    assert response.research_preview.retrieval_mode == "auto"
    assert response.research_preview.cases


def test_chat_response_skips_research_preview_for_non_precedent_prompt() -> None:
    response = chat_service.handle_chat(request, trace_id="trace-2")
    assert response.research_preview is None
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src uv run pytest -q tests/test_chat_service.py tests/test_api_scaffold.py -k research_preview`
Expected: FAIL because schema/service do not expose `research_preview`.

**Step 3: Write minimal implementation**

```python
class ChatResearchPreview(BaseModel):
    retrieval_mode: Literal["auto", "manual"]
    query: str
    source_status: dict[str, str]
    cases: list[LawyerCaseSupport]

class ChatResponse(BaseModel):
    ...
    research_preview: ChatResearchPreview | None = None
```

Inject `LawyerCaseResearchService` into `ChatService` and populate `research_preview` only when intent gate returns true and research succeeds.

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src uv run pytest -q tests/test_chat_service.py tests/test_api_scaffold.py -k "research_preview or case_law_query"`
Expected: PASS.

**Step 5: Commit**

```bash
git add src/immcad_api/schemas.py src/immcad_api/services/chat_service.py src/immcad_api/main.py src/immcad_api/api/routes/chat.py tests/test_chat_service.py tests/test_api_scaffold.py
git commit -m "feat(chat): add intent-gated auto precedent research preview"
```

### Task 6: Regression and Fallback Safety Sweep

**Files:**
- Test: `tests/test_case_search_service.py`
- Test: `tests/test_lawyer_research_api.py`
- Test: `tests/test_chat_service.py`

**Step 1: Write failing regression tests for fallback/degraded safety**

```python
def test_chat_still_returns_answer_when_research_preview_subflow_fails() -> None:
    response = chat_service.handle_chat(request)
    assert response.answer
    assert response.research_preview is None


def test_lawyer_research_returns_source_status_when_official_unavailable_canlii_used() -> None:
    response = client.post("/api/research/lawyer-cases", json=payload)
    assert response.status_code == 200
    assert response.json()["source_status"]["canlii"] in {"used", "not_used"}
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src uv run pytest -q tests/test_case_search_service.py tests/test_lawyer_research_api.py tests/test_chat_service.py -k "fallback or degraded or source_status"`
Expected: FAIL where behavior is missing.

**Step 3: Write minimal implementation**

```python
# Guard chat preview subflow errors and preserve chat response path.
# Keep existing source fallback behavior deterministic.
```

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src uv run pytest -q tests/test_case_search_service.py tests/test_lawyer_research_api.py tests/test_chat_service.py`
Expected: PASS.

**Step 5: Commit**

```bash
git add tests/test_case_search_service.py tests/test_lawyer_research_api.py tests/test_chat_service.py src/immcad_api/services/chat_service.py src/immcad_api/services/case_search_service.py src/immcad_api/api/routes/lawyer_research.py
git commit -m "test(research): lock fallback and degraded-mode retrieval safety"
```

### Task 7: Verification + Task Log Closure

**Files:**
- Modify: `tasks/todo.md`

**Step 1: Run backend quality checks**

Run:
- `make lint`
- `PYTHONPATH=src uv run pytest -q tests/test_case_query_validation.py tests/test_lawyer_research_planner.py tests/test_lawyer_case_research_service.py tests/test_lawyer_research_api.py tests/test_chat_service.py tests/test_case_search_service.py tests/test_api_scaffold.py`

Expected: PASS.

**Step 2: Run broader backend confidence pass**

Run: `make test`
Expected: PASS (or document exact failing unrelated tests if pre-existing).

**Step 3: Update task review evidence**

Add in `tasks/todo.md`:
- completed checklist,
- key behavior changes,
- exact verification command outputs.

**Step 4: Commit review log update**

```bash
git add tasks/todo.md
git commit -m "docs(tasks): record backend precedent retrieval verification evidence"
```

