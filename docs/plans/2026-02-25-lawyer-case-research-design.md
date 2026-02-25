# Lawyer Case Research Design - 2026-02-25

## Goal
Build a grounded legal research assistant workflow for lawyers that can reliably retrieve relevant Canadian case law, resolve downloadable documents when available, and explain why each case is relevant to a specific scenario.

## Decisions Confirmed
- Mode: Lawyer workflow with grounded research behavior (no fabricated authority, no false representation promises).
- Scope: Official-court-first retrieval (SCC, FC, FCA), with CanLII as supplemental metadata discovery when needed.
- Export behavior: Comprehensive mode.
  - Return relevant cases even when PDF is unavailable.
  - Always show citation, case identity, and where the user can find the decision.

## Architecture
1. Intent and matter extraction
- Identify lawyer research intent from user requests.
- Extract a structured matter profile from prompt content:
  - issue tags,
  - target court,
  - procedural posture (appeal/judicial review/etc.),
  - fact keywords,
  - requested remedy.

2. Case retrieval orchestrator
- Generate multiple legal search queries from the matter profile.
- Query official sources first using existing SCC/FC/FCA source registry entries.
- Optionally query CanLII metadata if official recall is sparse.
- Merge and de-duplicate candidates.

3. Relevance and evidence resolver
- Rank by issue overlap, court fit, and procedural similarity.
- Resolve document support status per case:
  - `pdf_available`,
  - `pdf_unavailable`,
  - official decision link/citation-only fallback.
- Never fabricate URL, citation, or case metadata.

4. Grounded legal explainer
- Produce per-case summaries and "why this helps" rationale tied only to retrieved evidence.
- Include confidence and evidence status for each case.

5. Lawyer output bundle
- Return a deterministic structured payload for frontend rendering and export tooling:
  - top cases,
  - relevance reasons,
  - citation fidelity,
  - document availability state,
  - next-step guidance.

## Data Flow
1. User submits matter query.
2. System builds structured matter profile.
3. System generates expanded legal queries.
4. Official-source retrieval executes.
5. Supplemental CanLII metadata retrieval executes when needed.
6. Candidate results are normalized, de-duplicated, and ranked.
7. Document/PDF status is resolved for each selected case.
8. Grounded synthesis generates lawyer-facing case support output.

## Safety and Policy
- No synthetic case-law fallback in hardened environments.
- No fabricated citations, titles, or links in any environment.
- Source policy and host validation are enforced for export/download paths.
- If PDF is unavailable:
  - still provide case name, neutral citation, court, and official source link,
  - provide a transparent reason.
- If sources partially fail:
  - return partial results with source-status metadata.
- If all sources fail:
  - return structured `SOURCE_UNAVAILABLE` response with trace ID.

## Testing Strategy
1. Backend unit tests
- matter extraction,
- query expansion,
- ranking logic,
- document resolver state transitions.

2. Backend integration tests
- official-source retrieval path,
- official+CanLII merge path,
- partial and full outage handling,
- policy-gated export behavior.

3. Frontend contract tests
- case cards with relevance rationale,
- explicit PDF availability states,
- fallback citation/link display when PDF missing.

4. Quality gates
- deterministic response schema checks,
- no-fabrication regression tests,
- trusted-domain and host-validation tests.

## MVP Acceptance Criteria
- Users can ask complex lawyer-style case-support questions and receive relevant cases.
- Every returned case has verifiable citation metadata.
- Every returned case has explicit evidence state (`pdf_available` or `pdf_unavailable`).
- When PDF unavailable, user still receives actionable case identifiers and official location links.
- Responses include grounded rationale for relevance per case.

## Out of Scope (Current MVP)
- Guaranteed litigation outcomes.
- Autonomous legal representation behavior.
- Unbounded web scraping beyond approved source/policy controls.

## Approval Record
- Architecture: approved.
- Data flow: approved.
- Safety/policy: approved.
- Testing/success criteria: approved.
