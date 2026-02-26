# IMMCAD AI Assistant Architecture Improvement Proposals

Date: 2026-02-26
Owner: platform-engineering
Scope: `src/immcad_api`, `frontend-web`, ingestion/retrieval workflows

## Executive Summary

The current architecture already has strong production safety controls (hardened env gates, source-policy enforcement, signed export approvals, trusted citation domains, and endpoint-level trace IDs). The main remaining gap is **answer quality and research depth** relative to a legal-work assistant standard.

High-impact opportunities are:

1. Replace keyword/static grounding with retrieval-backed grounding plus passage-level evidence.
2. Move from regex-triggered tool usage to structured multi-tool orchestration with explicit stop/retry policies.
3. Add deterministic legal research outputs (issue map, authority table, conflict notes) before final narrative generation.
4. Improve observability from request metrics to **workflow/trace metrics per tool step**.
5. Expand source strategy to reduce dependence on CanLII API quotas and improve freshness guarantees.

## Current-State Findings (Code-Based)

1. Chat grounding is mostly static/keyword:
   - `src/immcad_api/main.py` selects `StaticGroundingAdapter` or `KeywordGroundingAdapter` only.
   - `src/immcad_api/services/grounding.py` provides curated citations, not corpus retrieval.

2. Tool invocation is heuristic:
   - `src/immcad_api/services/chat_service.py` uses regex (`_CASE_SEARCH_TOOL_PATTERN`) to decide whether to call case search.
   - No model-planned tool arguments, no multi-step tool chaining policy, no tool confidence thresholding.

3. Research planner/ranker is deterministic but shallow:
   - `src/immcad_api/services/lawyer_research_planner.py` and `src/immcad_api/services/lawyer_case_research_service.py` use token/keyword scoring with handcrafted boosts.
   - No passage-level relevance model, contradiction checks, or statutory/case cross-linking.

4. Source pipeline remains feed-metadata focused:
   - `src/immcad_api/sources/official_case_law_client.py` ranks by metadata fields and patterns.
   - `src/immcad_api/sources/canlii_client.py` can still synthesize scaffold cases in non-hardened envs.

5. Frontend can block parallel legal work:
   - `frontend-web/components/chat/use-chat-logic.ts` uses aggregate `isSubmitting`, which can unnecessarily gate chat while case-search/export is active.

6. Observability is request-level, not agent-step-level:
   - `src/immcad_api/telemetry/request_metrics.py` tracks rates/latency/outcomes but not per-tool call latency, retrieval hit-rate, or citation coverage by workflow phase.

## External Research Signals (As of 2026-02-26)

1. OpenAI tooling guidance emphasizes multi-call tool flows and strict schema enforcement:
   - Function-calling guidance notes model responses may include zero/one/multiple tool calls and recommends explicit orchestration loops.
   - Structured Outputs strict mode and tool schema controls reduce malformed tool payloads.

2. OpenAI eval guidance stresses continuous evaluation and trace grading:
   - Evals should be integrated continuously across prompt/model/tool changes.
   - Trace-level scoring is recommended for multi-step agent workflows.

3. OpenAI hosted retrieval/search tools show a current best-practice direction:
   - File Search uses combined lexical + semantic retrieval and reranking by default.
   - Web Search supports real-time retrieval for up-to-date information tasks.

4. NIST AI RMF + GenAI Profile prioritize measurable reliability/governance controls:
   - The profile extends AI RMF controls specifically for generative AI lifecycle risks.

5. Canadian legal operations are tightening expectations on AI use in legal submissions:
   - Federal Court guidance requires parties to verify AI-generated citations and authority claims.
   - This supports implementing explicit internal citation verification and research traceability.

6. CanLII ecosystem is changing:
   - CanLII launched Search+ (publicly announced on 2026-02-25) with daily usage limits and enhanced analysis features for logged-in users.
   - CanLII terms continue to restrict automated scraping/bulk extraction, so source strategy should remain policy-aware.

## Proposed Architecture Upgrades

## Proposal 1: Retrieval-Backed Grounding With Evidence Spans (P0)

Problem:
- Current grounding cannot provide high-confidence, case-specific legal answers at scale.

Changes:
- Introduce a `RetrievalGroundingAdapter` that returns passage-level evidence objects:
  - `source_id`, `doc_id`, `url`, `pinpoint`, `quote_span`, `retrieval_score`.
- Index official statutes/regulations/guidance/case text chunks with structured metadata:
  - `jurisdiction`, `source_type`, `court`, `decision_year`, `program`, `effective_date`.
- Keep keyword adapter only as fallback path when retrieval infrastructure is unavailable.

Why now:
- Highest answer-quality lift per unit effort; unlocks better legal research and citation fidelity.

Acceptance metrics:
- `grounded_answer_rate >= 90%` on internal benchmark set.
- `citation_match_rate >= 98%` (citation points to retrieved evidence span).

## Proposal 2: Structured Tool Orchestration Layer (P0)

Problem:
- Regex tool trigger is brittle and cannot compose multi-step research reliably.

Changes:
- Add a typed tool registry + dispatcher:
  - tools: `search_cases`, `fetch_case_document`, `retrieve_statute`, `retrieve_policy`.
- Use strict JSON schema for tool arguments/results.
- Add bounded orchestration policy:
  - max tool steps per request
  - per-tool timeout/retry budgets
  - explicit terminal states (`answered`, `need_more_context`, `source_unavailable`).

Why now:
- Converts chat from heuristic to auditable agent behavior; improves determinism and debugging.

Acceptance metrics:
- `tool_schema_error_rate < 0.5%`.
- `tool_timeout_user_visible_rate < 2%` with graceful fallback envelopes.

## Proposal 3: Deterministic Legal Research Product Layer (P0)

Problem:
- Research output is mostly ranked case cards + narrative; missing a lawyer-grade work product format.

Changes:
- Add an internal structured output before final prose:
  - issue list
  - authority table (statute + cases)
  - supports/contradicts matrix
  - unresolved questions
- Require final answer to reference this structure.
- Persist a short-lived trace artifact for each research run (for reproducibility and QA).

Why now:
- Enables “actually do work” expectation: reusable legal research artifacts, not only chat text.

Acceptance metrics:
- `research_trace_completeness = 100%` for successful requests.
- Reviewer rubric score improvement on legal research usefulness.

## Proposal 4: Source Reliability and Freshness Controls (P1)

Problem:
- Feeds and APIs can fail/lag; metadata-only ranking can miss high-value authorities.

Changes:
- Add freshness ledger per source:
  - last successful fetch, staleness class, expected cadence breach alerts.
- Expand official-source-first strategy with explicit fallback matrix and user-visible source-status details.
- Add ingestion-level canonicalization:
  - citation normalization, duplicate clustering, court-provided neutral citation preference.

Why now:
- Improves trust and operational predictability under source instability.

Acceptance metrics:
- `freshness_sla_breach_rate` tracked and alerting active.
- reduction in `SOURCE_UNAVAILABLE` for case-research endpoint.

## Proposal 5: Agent-Step Observability and Evals (P1)

Problem:
- Current metrics are request-level and cannot isolate which agent step failed.

Changes:
- Extend telemetry with step spans:
  - planning, each tool call, retrieval, citation-validation, final synthesis.
- Add quality eval suite:
  - citation correctness
  - refusal correctness
  - legal-scope compliance
  - source-trust compliance
- Add CI gate with fixed benchmark set and regression thresholds.

Why now:
- Needed to ship changes safely without quality regressions.

Acceptance metrics:
- CI fails on benchmark regression beyond threshold.
- per-step latency and error SLO dashboards available.

## Proposal 6: Frontend Research UX for Parallel Work (P2)

Problem:
- Single aggregate submit lock can reduce expert-user throughput.

Changes:
- Keep per-workflow pending state only (`chat`, `case_search`, `export`).
- Show source provenance and evidence confidence per case/result.
- Add “stale results” warning when query changes after last search (partially present; extend to chat context).

Why now:
- Better user control and transparency for legal research workflows.

Acceptance metrics:
- reduced “stuck UI” complaints
- improved completion rate for case-search + export flows

## 90-Day Delivery Sequence

Phase A (Weeks 1-3):
- Proposal 1 + minimal Proposal 2 scaffolding
- benchmark/eval dataset definition

Phase B (Weeks 4-6):
- Full Proposal 2 orchestration + Proposal 5 telemetry spans
- CI eval gate v1

Phase C (Weeks 7-9):
- Proposal 3 legal research product layer
- Proposal 4 freshness ledger + fallback transparency

Phase D (Weeks 10-12):
- Proposal 6 UX refinements
- performance tuning and release hardening

## Immediate Next Actions (Recommended)

1. Implement `RetrievalGroundingAdapter` behind feature flag and run A/B against current keyword grounding.
2. Introduce tool registry + strict schema for `search_cases` first (single-tool pilot).
3. Add trace-step telemetry fields before adding more tools (so quality impact is measurable).
4. Build a 100-query Canada immigration legal benchmark and lock it into CI regression checks.

## References

- OpenAI Function Calling Guide: https://platform.openai.com/docs/guides/function-calling
- OpenAI Evals Guide: https://platform.openai.com/docs/guides/evals
- OpenAI Trace Grading Guide: https://platform.openai.com/docs/guides/graders/trace-grading
- OpenAI File Search Guide: https://platform.openai.com/docs/guides/tools-file-search
- OpenAI Web Search Guide: https://platform.openai.com/docs/guides/tools-web-search
- NIST AI RMF 1.0: https://www.nist.gov/itl/ai-risk-management-framework
- NIST Generative AI Profile: https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-generative-artificial-intelligence
- Federal Court of Canada notice on AI use (as linked by CITT): https://www.fct-cf.gc.ca/en/pages/online-access/e-filing/notice-to-the-parties-and-the-profession-use-of-artificial-intelligence
- CITT practice notice (AI use in submissions): https://www.citt-tcce.gc.ca/fr/regles-pratiques-directives/practice-notice-no-7-use-of-artificial-intelligence-in-citt-proceedings
- Canadian Bar Association AI resources: https://www.cba.org/our-work/partnerships-and-engagement/technology/ai/
- CanLII Terms and Conditions: https://www.canlii.org/en/info/terms.html
- CanLII announcement: Search+ launch (2026-02-25): https://blog.canlii.org/2026/02/25/introducing-canlii-search/
