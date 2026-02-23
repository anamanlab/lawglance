# PRD: IMMCAD Production Readiness and CanLII Legal Research

## 1. Introduction / Overview

This PRD defines a single master feature initiative to finalize IMMCAD for production readiness while adding a new legal research capability for Canadian immigration case law using CanLII.

The work combines:

- Remaining MVP hardening tasks already identified in the repository backlog (including ingestion recovery runbook and release artifact verification gates)
- Retrieval-grounded chat citations (replacing scaffold-only citation behavior in real deployments)
- Production release controls (quality, legal/compliance, observability, rollback readiness)
- A new CanLII-based legal research feature to assist:
  - Lawyers
  - CICC licensees (formerly RCICs)
  - Self-represented applicants seeking immigration information and case-law guidance

This PRD is written as a phased epic with small, verifiable user stories so a junior developer or AI agent can execute incrementally.

Important boundary: IMMCAD remains an informational and research-assistance product, not legal representation or legal advice.

## 2. Goals

- Deliver a production-ready IMMCAD release process with explicit evidence-based gates.
- Ensure `/api/chat` responses are grounded with real retrieval-derived citations (no scaffold-only citation path in production).
- Add a CanLII case-law legal research workflow for immigration-related case research (not only fallback behavior).
- Preserve Canada-only jurisdiction scope and prevent India-domain leakage in production responses and docs.
- Improve operational safety with runbooks, artifact validation, smoke checks, observability, and rollback procedures.
- Support a controlled production launch using the current bearer-token access model, with a path to stronger user auth/role gating later.

## 3. User Stories

### US-001: Integrate retrieval-grounded citations into chat service
**Description:** As an IMMCAD user, I want factual chat responses to include real citations from retrieved Canadian immigration sources so that I can verify the information.

**Acceptance Criteria:**
- [ ] Chat request flow retrieves relevant source context from the configured Canada corpus before provider generation.
- [ ] Citation objects returned in `/api/chat` are derived from retrieved documents/metadata, not synthetic scaffold placeholders.
- [ ] Citation-required enforcement still refuses/degrades appropriately when grounded citations are unavailable.
- [ ] Production mode blocks synthetic scaffold citations entirely.
- [ ] Typecheck/lint passes.
- [ ] Targeted tests for grounded citation paths and missing-context behavior pass.

### US-002: Add retrieval failure behavior and explicit user-safe fallback handling
**Description:** As a user, I want clear behavior when retrieval fails or returns insufficient context so that I am not misled by ungrounded legal information.

**Acceptance Criteria:**
- [ ] Retrieval failure and low-context scenarios produce a defined response path (refusal or constrained response) with a consistent reason code.
- [ ] Error and degraded paths preserve trace IDs.
- [ ] No provider-generated factual legal answer is returned without passing citation policy checks.
- [ ] Typecheck/lint passes.
- [ ] Tests cover retrieval timeout, empty results, and provider success with missing citations.

### US-003: Remove/disable scaffold behavior in production deployment paths
**Description:** As a release owner, I want production configuration to reject scaffold-only behaviors so that users cannot receive non-authoritative placeholder responses.

**Acceptance Criteria:**
- [ ] Production/CI configuration fails fast if scaffold provider is enabled unexpectedly (or is clearly feature-flagged and disabled by default).
- [ ] Production/CI configuration fails fast if scaffold synthetic citations are enabled.
- [ ] Documentation and `.env.example` clearly differentiate local scaffold mode vs production-safe mode.
- [ ] Typecheck/lint passes.
- [ ] Tests validate environment guardrails.

### US-004: Expand jurisdictional evaluation dataset and thresholds for release gating
**Description:** As a release manager, I want a larger evaluation suite with explicit pass thresholds so that release decisions are evidence-based.

**Acceptance Criteria:**
- [ ] Jurisdictional test suite dataset includes at least 50 cases covering grounded responses, policy refusals, and out-of-scope prompts.
- [ ] Dataset includes cases designed to catch India-domain leakage and non-Canada legal framing.
- [ ] Thresholds are encoded and enforced in scripts/CI (citation coverage, policy accuracy, leak rate).
- [ ] Evaluation reports remain machine-readable (`json`) and human-readable (`md`).
- [ ] Typecheck/lint passes.
- [ ] Tests for evaluation script behavior pass.

### US-005: Add ingestion checkpoint recovery runbook (existing backlog US-004)
**Description:** As an on-call engineer, I want a clear checkpoint recovery runbook so that ingestion jobs can be resumed safely after failure or checkpoint corruption.

**Acceptance Criteria:**
- [ ] Runbook documents checkpoint file location(s), expected structure, and common failure modes.
- [ ] Runbook documents corruption recovery and replay procedures with exact commands.
- [ ] Runbook includes a post-recovery verification checklist (artifact checks, sample source status checks).
- [ ] Runbook identifies when to discard/rebuild checkpoints vs resume.
- [ ] Typecheck/lint passes (if docs validation scripts apply).

### US-006: Add release artifact verification gate (existing backlog US-005)
**Description:** As a release manager, I want an automated artifact verification step so that legal/compliance sign-off is based on actual generated evidence files.

**Acceptance Criteria:**
- [ ] A script validates required release artifacts exist and are non-empty/readable.
- [ ] Script validates JSON artifacts parse successfully.
- [ ] `release-gates` workflow runs the artifact verification step before final completion/upload.
- [ ] Failure output identifies missing/invalid artifact paths clearly.
- [ ] Typecheck/lint passes.
- [ ] Tests for artifact verification script pass.

### US-007: Harden release gates for production readiness evidence
**Description:** As an engineering lead, I want release gates to include all required quality and safety checks so that production releases are consistent and auditable.

**Acceptance Criteria:**
- [ ] Release workflow requires quality checks, jurisdiction eval report, jurisdiction suite, smoke tests, and repository hygiene checks.
- [ ] Release workflow validates legal review checklist in strict mode for production release runs.
- [ ] Release workflow uploads release evidence artifacts in a consistent artifact bundle.
- [ ] Release workflow failure messages identify which gate failed.
- [ ] Typecheck/lint passes.
- [ ] Dry-run or workflow validation test/documented execution passes.

### US-008: Add production rollback and cutover runbook
**Description:** As an operator, I want a rollback and cutover procedure so that production incidents can be mitigated quickly during launch.

**Acceptance Criteria:**
- [ ] Runbook documents pre-release checklist, cutover steps, and rollback trigger conditions.
- [ ] Runbook documents which config flags must be set for production-safe mode.
- [ ] Runbook includes smoke-test commands and expected results.
- [ ] Runbook includes ownership/escalation contacts/roles (team role labels, not personal secrets).
- [ ] Typecheck/lint passes (if docs validation scripts apply).

### US-009: Define case-law legal research API contract for CanLII search
**Description:** As a frontend integrator, I want a stable API contract for case-law research search so that I can build reliable legal research UI workflows.

**Acceptance Criteria:**
- [ ] API contract defines request fields for query, jurisdiction, court, date range, pagination, and result limits.
- [ ] API contract defines response schema for normalized case metadata and provenance fields.
- [ ] Error envelope and trace ID behavior are consistent with existing API conventions.
- [ ] Contract docs are added/updated in architecture/API documentation.
- [ ] Typecheck/lint passes.
- [ ] Tests validate schema serialization and error envelope shape.

### US-010: Implement CanLII case search service for legal research (FCT required, extensible coverage)
**Description:** As a legal researcher, I want case search results from CanLII so that I can find relevant immigration case law efficiently.

**Acceptance Criteria:**
- [ ] Case search service performs live CanLII-backed queries for Federal Court (`fct`) at minimum.
- [ ] Service normalizes results into a stable schema (case ID, title, citation, decision date, URL, court).
- [ ] Service supports pagination/offset behavior and bounded limits.
- [ ] Service returns explicit degraded/error responses when CanLII is unavailable (not misleading placeholder results for production research mode).
- [ ] Implementation is designed to add FCA/SCC/other courts without breaking the contract.
- [ ] Typecheck/lint passes.
- [ ] Tests cover live-response parsing, empty results, and CanLII failure behavior with mocks.

### US-011: Add case detail retrieval and grounded AI summary for research assistance
**Description:** As a lawyer, CICC licensee, or self-represented applicant, I want a grounded summary of a selected case so that I can quickly understand relevance before reading the full decision.

**Acceptance Criteria:**
- [ ] API supports fetching case detail (or sufficient metadata/text source) for a selected CanLII result.
- [ ] AI-generated summary is grounded in retrieved case content/metadata and includes source citation(s)/links to the case.
- [ ] Summary response clearly states informational/research-assistance disclaimer and does not present legal advice.
- [ ] If grounding material is insufficient, the API returns a constrained response or refuses summary generation.
- [ ] Typecheck/lint passes.
- [ ] Tests cover grounded summary success and insufficient-context refusal/degraded paths.

### US-012: Add legal research search UI in Streamlit
**Description:** As a user performing case-law research, I want a dedicated search interface for case research so that I can search CanLII without overloading the chat flow.

**Acceptance Criteria:**
- [ ] UI provides a clear legal research entry point (e.g., tab/section) separate from general chat.
- [ ] UI supports search query input and court/jurisdiction filters.
- [ ] UI displays loading, empty, error, and success states with trace-aware messages where applicable.
- [ ] UI labels the feature as legal research assistance and not legal advice.
- [ ] Typecheck/lint passes.
- [ ] Verify in browser using dev-browser skill.

### US-013: Add case results list and detail summary UI
**Description:** As a legal researcher, I want to view a list of cases and inspect a selected case summary so that I can evaluate relevance quickly.

**Acceptance Criteria:**
- [ ] Results list shows normalized metadata (title, citation, court, decision date, link).
- [ ] Selecting a result loads case summary/details in the UI.
- [ ] UI displays source links and provenance clearly.
- [ ] UI handles degraded/unavailable summary cases without crashing and preserves user trust messaging.
- [ ] Typecheck/lint passes.
- [ ] Verify in browser using dev-browser skill.

### US-014: Add production observability for chat and case research flows
**Description:** As an operator, I want traceable metrics and logs for chat and case research paths so that I can detect failures, latency spikes, and policy issues in production.

**Acceptance Criteria:**
- [ ] Structured logs include trace IDs for chat and case research error/degraded paths.
- [ ] Metrics capture request counts, error counts, and latency for chat and case research endpoints.
- [ ] Provider fallback and retrieval failures are observable with distinct event labels.
- [ ] Documentation defines how to inspect logs/metrics during incident triage.
- [ ] Typecheck/lint passes.
- [ ] Tests cover critical logging/metrics instrumentation paths where practical.

### US-015: Define controlled production access policy using current bearer-token model
**Description:** As a release owner, I want a clearly documented access model for initial production rollout so that exposure is controlled while stronger auth is planned.

**Acceptance Criteria:**
- [ ] PRD-aligned docs explicitly state initial production access uses bearer-token service auth for controlled rollout.
- [ ] Access model documents intended users (lawyers, CICC licensees, self-represented applicants) and rollout limitations.
- [ ] Security checklist documents risks/mitigations of bearer-token access and conditions for broader exposure.
- [ ] Follow-on requirement for role-based user auth is tracked as a future phase (not silently omitted).
- [ ] Typecheck/lint passes (if docs validation scripts apply).

### US-016: Execute production readiness sign-off checklist and release evidence pack
**Description:** As product and engineering stakeholders, we want a final sign-off package so that the project can be confidently released to production.

**Acceptance Criteria:**
- [ ] Final release evidence pack includes eval reports, suite reports, smoke output summary, legal checklist status, and artifact validation result.
- [ ] Release checklist confirms no scaffold synthetic citations in production config and no placeholder research responses in production research mode.
- [ ] Legal/compliance reviewer sign-off step is recorded (process evidence or checklist state).
- [ ] Engineering sign-off confirms rollback procedure and cutover checklist reviewed.
- [ ] Typecheck/lint passes.

## 4. Functional Requirements

- FR-1: The system must retrieve relevant Canadian immigration sources before generating factual chat responses in production mode.
- FR-2: The system must require valid citations for non-refusal factual chat responses.
- FR-3: The system must refuse or constrain responses when retrieval context is insufficient for grounded answers.
- FR-4: The system must preserve trace IDs across success, degraded, and error responses for chat and case research APIs.
- FR-5: The system must prevent synthetic scaffold citations in production and CI production-like modes.
- FR-6: The system must provide an automated evaluation suite with explicit thresholds for citation coverage, policy refusal accuracy, and jurisdiction leakage.
- FR-7: The release process must validate that required evaluation artifacts exist, are readable, and JSON artifacts parse successfully.
- FR-8: The project must provide an ingestion checkpoint recovery runbook with replay and verification steps.
- FR-9: The project must provide a release cutover and rollback runbook for production deployment.
- FR-10: The system must expose a dedicated legal research API contract for CanLII-backed case search (separate from chat fallback behavior).
- FR-11: The legal research API must support, at minimum, Federal Court (`fct`) immigration case search.
- FR-12: The legal research API must return normalized case metadata including title, citation, court, decision date, and source URL.
- FR-13: The legal research API must support pagination and bounded result limits.
- FR-14: The legal research API must return explicit degraded/error behavior when CanLII is unavailable in production research mode.
- FR-15: The system must support a grounded AI summary workflow for selected cases when sufficient source content is available.
- FR-16: The system must disclose legal research assistance limitations and legal-advice boundaries in case research UI/API responses.
- FR-17: The UI must provide a dedicated legal research workflow (search, results, case selection, summary view).
- FR-18: The system must emit structured logs and operational metrics for chat and legal research flows.
- FR-19: The release process must require legal/compliance checklist validation before production release sign-off.
- FR-20: The system must preserve Canada-only legal domain scope and block/flag India-domain leakage in code, prompts, and release artifacts.
- FR-21: Initial production release may use bearer-token service authentication for controlled rollout, but the release docs must explicitly state rollout limitations and future auth requirements.
- FR-22: All production readiness gates must be executable and documented such that another engineer can reproduce them.

## 5. Non-Goals (Out of Scope)

- Full public user account system with role-based user authentication/authorization in this release (tracked as follow-on work).
- Formal legal advice, legal representation, or automated legal strategy recommendations.
- Guaranteed coverage of every Canadian court/tribunal in the first legal research release.
- Full French-language UI/localization for this release (English-first remains in scope).
- Research memo export (PDF/DOCX), collaborative annotations, or case comparison workspace unless explicitly added in a later PRD.
- Replacing all legacy modules (`lawglance_main.py`, `chains.py`) in this release if they are not on the active runtime path.

## 6. Design Considerations (Optional)

- Provide a clear UI distinction between:
  - General chat (informational guidance)
  - Legal research (case-law search and summaries)
- Use plain-language disclaimers that are understandable for self-represented users while remaining accurate for professionals.
- Make provenance obvious:
  - Case title
  - Neutral citation (when available)
  - Court
  - Decision date
  - Direct CanLII link
- Show explicit error/degraded states (e.g., CanLII unavailable, insufficient text to summarize) instead of silently substituting placeholders.
- Reuse existing IMMCAD UI framing and disclaimer placement patterns where possible.

## 7. Technical Considerations (Optional)

- Current runtime is API-first (`app.py` -> FastAPI `/api/chat`), so new legal research capabilities should follow the same API-first pattern.
- Current chat service already enforces policy and citation rules; retrieval grounding should be integrated into service flow before provider generation.
- Existing `CanLIIClient` and case search service provide a starting point but must be hardened for production research behavior (no misleading deterministic placeholders in production research mode).
- Provider routing already includes fallback and circuit-breaker behavior; retrieval and citation logic should not weaken policy guarantees.
- Production config should explicitly disable scaffold provider/synthetic citations by default and fail fast on unsafe settings.
- Observability should extend existing trace ID and audit logging patterns to retrieval and legal research paths.
- CI and release gates should generate and validate machine-readable evidence artifacts to support legal/compliance review.
- Court coverage should be implemented with extensible normalization so additional CanLII courts/tribunals can be added without breaking clients.

## 8. Success Metrics

### Production Readiness Gate (required to mark this PRD complete)

- CI/quality gates are green on release branch:
  - Ruff/lint checks pass
  - Test suite passes
  - Domain leak scanner passes
  - Jurisdiction evaluation report generation passes
  - Jurisdiction behavior suite passes
  - Repository hygiene checks pass
- Release gates are green:
  - Legal review checklist strict validation passes
  - Artifact verification script passes
  - Smoke tests pass
  - Required release evidence artifacts are uploaded and readable
- Jurisdiction/evaluation thresholds are met:
  - Jurisdictional suite dataset size `>= 50`
  - Citation coverage for grounded factual responses `>= 95%`
  - Policy refusal accuracy `= 100%` on defined refusal test set
  - India-domain leak rate `= 0%` in release-evaluated outputs
- Production safety thresholds are met:
  - Scaffold synthetic citations disabled in production
  - No placeholder/scaffold legal research case results returned in production research mode
  - Trace ID present on API responses and production error paths
- Operational readiness thresholds are met:
  - Ingestion checkpoint recovery runbook completed and validated via at least one dry run/tabletop or documented test execution
  - Cutover/rollback runbook completed and reviewed by engineering
  - Release evidence pack available for sign-off review
- Legal/compliance and engineering sign-off completed for production release decision.

### Product/Feature Metrics (post-release monitoring targets)

- `>= 95%` successful response rate for case research search requests (excluding upstream CanLII outages tracked separately).
- `100%` of case research results include direct source links/provenance fields.
- `100%` of grounded case summaries include case source citation(s) or explicit constrained-response behavior.
- No known production incidents caused by scaffold-only content being served to users.

## 9. Open Questions

- Should broader court coverage (FCA, SCC, IRB-related materials where available on CanLII) be included in the first production release or feature-flagged for phased rollout after Federal Court validation?
- What exact CanLII API limits/terms (rate limits, quotas, endpoint constraints) must be encoded into production throttling and retry behavior?
- For case summaries, what source content retrieval depth is feasible from CanLII endpoints versus linked pages without violating reliability/performance requirements?
- What is the timeline for moving from bearer-token controlled rollout to user authentication with role-based access (e.g., professional vs public)?
- What latency targets (search and summary generation) should be formalized as release gates vs post-release optimization KPIs?

## Implementation Notes for Execution Planning (Non-binding)

- This PRD is a master epic and should be executed in phased slices:
  1. Production safety + release gates (US-003 to US-008)
  2. Retrieval-grounded chat citations (US-001 to US-004)
  3. CanLII legal research API + UI (US-009 to US-013)
  4. Observability, controlled access policy, and final sign-off (US-014 to US-016)
- If scope pressure arises, preserve production safety and groundedness requirements first; defer only explicitly non-goal items or feature-flagged court expansions.
