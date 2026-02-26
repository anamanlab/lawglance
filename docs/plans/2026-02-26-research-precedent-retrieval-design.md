# Research, Precedent Retrieval, and Workflow Clarity Design

## Context
IMMCAD currently provides a split workflow: users ask chat questions first, then manually trigger related case-law research. Retrieval quality is limited by strict broad-query rejection, shallow query expansion, and token-overlap ranking that underweights legal precedent signals.

This design addresses the approved direction:
- intent-gated auto retrieval for precedent/case-law requests,
- preserved manual case-search controls,
- clearer backend provenance and frontend workflow distinction.

## Goals
- Improve relevance of retrieved precedents for legal research questions.
- Reduce user confusion between conversational answers and case-law outputs.
- Keep costs/latency controlled via intent-gated (not always-on) retrieval.
- Preserve existing policy/safety gates and source-trust guarantees.

## Non-Goals
- Replacing source connectors (official court feeds/CanLII) in this phase.
- Building semantic/vector retrieval infrastructure in this phase.
- Introducing jurisdictional scope beyond current Canada case-law pathways.

## Proposed Architecture

### 1) Intent-Gated Auto Retrieval (Backend)
- Add a shared intent detector for precedent/case-law requests.
- In chat orchestration, run lawyer research automatically only when intent is positive.
- Preserve manual `/api/research/lawyer-cases` as the explicit user-controlled path.
- Return retrieval provenance metadata to distinguish auto vs manual retrieval mode.

### 2) Query Planning and Refinement
- Upgrade planner to generate more diverse legal research queries using:
  - detected court/citation/docket anchors,
  - issue tags and procedural posture,
  - normalized legal keywords and synonymic variants.
- Introduce refinement hints for low-specificity queries so callers can guide users.

### 3) Precedent Relevance Ranking
- Expand ranking signals beyond simple token overlap:
  - court-target match,
  - citation/docket explicit matches,
  - issue-tag alignment,
  - recency as a tie-breaker.
- Keep deterministic ordering and dedupe rules.

### 4) Validation and Degradation Behavior
- Replace binary broad-query behavior with graded handling:
  - allow sufficiently specific legal queries,
  - only block clearly non-specific noise,
  - include refinement reasons/hints for near-threshold queries.
- If official sources fail, continue CanLII fallback where allowed, with explicit source status.

### 5) Frontend Contract for Clarity
- Support UI distinction with backend metadata fields:
  - retrieval mode (`auto` or `manual`),
  - executed query summary,
  - result rationale/provenance.
- Keep existing manual panel controls and stale-query messaging behavior.

## Data Flow
1. User sends chat message.
2. Chat service classifies intent.
3. If precedent intent is true:
   - build expanded research queries,
   - run lawyer research,
   - attach provenance + top supports to response payload.
4. Chat answer is returned with grounded citations and optional research preview.
5. User may still run manual related-case search; manual mode is labeled distinctly.

## Error Handling
- Chat response remains resilient if research subflow fails; research metadata degrades to unavailable state without crashing chat.
- Source/policy failures propagate structured error codes and trace IDs.
- Broad/noise query responses provide actionable refinement guidance when possible.

## Testing Strategy
- Backend unit tests:
  - intent-gated auto retrieval activation,
  - query planner expansion quality and dedupe,
  - ranking order with legal relevance signals,
  - graded validation and refinement hints.
- API tests:
  - chat response contract with optional research preview metadata,
  - lawyer research response provenance and source status consistency,
  - fallback behavior under official-source failures.
- Frontend tests (follow-up phase):
  - conversation vs case-law labeling,
  - retrieval mode badges,
  - stale-query refresh cues.

## Rollout
- Phase 1: backend retrieval quality + contracts behind non-breaking optional fields.
- Phase 2: frontend rendering of provenance and workflow clarity labels.
- Phase 3: tuning thresholds from observed test and telemetry evidence.

## Acceptance Criteria
- Retrieval for precedent-focused prompts returns higher-quality, court-relevant cases in deterministic tests.
- Broad/noise prompts no longer fail silently; users receive refinement guidance.
- Chat and case-law outputs are distinguishable via explicit metadata and UI labels.
- Existing policy, citation trust, and export gates remain green.
