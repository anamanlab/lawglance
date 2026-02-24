# Canada Legal AI Production Implementation Plan

**Date:** 2026-02-24  
**Project:** IMMCAD legal research AI agent  
**Status:** Draft for execution

## 1. Objective

Operationalize the Canada legal source strategy into production, with explicit rights controls, connector hardening, conformance testing, pilot evaluation, and parallel provider procurement.

This plan directly implements the five required tracks:

1. Finalize rights matrix and policy gates.
2. Implement Phase 1 connectors (SCC, FC, FCA) with safeguards.
3. Add conformance tests before rollout.
4. Run pilot ingestion and retrieval evaluation.
5. Run commercial provider diligence/procurement in parallel.

## 1.1 Top Priorities (Ranked)

`P0` (must ship before production pilot):

1. Rights matrix and runtime source policy gates (internal vs production + export controls).
2. SCC/FC/FCA connector hardening with year/citation/source-validation safeguards.
3. Conformance suite in CI with release-blocking behavior for rights/compliance failures.

`P1` (must ship before production cutover):

1. Pilot scorecard automation with hard go/no-go thresholds.
2. Expanded operational metrics for ingestion/citation SLOs and alerting escalation path.

`P2` (parallel, non-blocking for initial official-source launch):

1. Commercial provider diligence and procurement track.
2. Internal-only accelerator lane governance (A2AJ/Refugee Law Lab) with legal review cadence.

## 2. Scope and Non-Goals

### In Scope

- Canadian case-law ingestion for SCC, FC, FCA.
- Rights-aware retrieval and export controls.
- User PDF and curated-website ingestion hardening.
- Pilot release decision for production promotion.

### Out of Scope (for this execution window)

- Full national historical corpus backfill for every court.
- Unbounded web crawling.
- Production promotion of unofficial datasets before legal approval.

## 3. Policy Decisions (Explicit)

Effective immediately unless superseded by legal approval:

1. `CanLII API`
- Allowed for metadata discovery only.
- Not allowed for full-text ingestion via API.

2. `A2AJ`
- `internal-only`: allowed for prototyping and evaluation.
- `production`: blocked until legal/compliance approves source and downstream rights.

3. `Refugee Law Lab (RLL)`
- `internal-only`: allowed for prototyping and evaluation.
- `production`: blocked until legal/compliance approves CC BY-NC and upstream compatibility.

4. `Official court sources (SCC/FC/FCA)`
- Allowed for production ingestion subject to source terms, attribution, and policy-gate enforcement.

## 3.1 Cross-Vendor Agent Reliability Controls

The implementation must satisfy cross-vendor agent reliability controls:

1. Strict tool/function schemas and explicit orchestration loop ownership in application code.
2. Human approval interrupts for sensitive actions (for example, full-text export/download).
3. Durable run state and resumability for interrupted workflows.
4. Input/output guardrails and explicit failure handling paths.
5. Tracing and auditability for tool calls, policy decisions, and retries.

These controls reflect common cross-vendor guidance (OpenAI Agents SDK, Anthropic tool-use guidance, and Google agent/Gemini production safety guidance).

## 4. Workstream A: Rights Matrix and Policy Gates (Week 1)

### Deliverables

1. Source rights matrix in `artifacts/compliance/source-rights-matrix.md`.
2. Machine-readable policy config in `config/source_policy.yaml`.
3. Runtime gate checks integrated in ingestion and retrieval paths.

### Minimum matrix fields

- `source_id`
- `source_class` (`official`, `unofficial`, `commercial`)
- `internal_ingest_allowed`
- `production_ingest_allowed`
- `answer_citation_allowed`
- `export_fulltext_allowed`
- `license_notes`
- `review_owner`
- `review_date`

### Gate behavior

1. Ingestion gate: block ingestion when source policy marks `production_ingest_allowed: false` for production environment.
2. Retrieval gate: suppress citations when `answer_citation_allowed: false`.
3. Export gate: deny full download when `export_fulltext_allowed: false`.
4. Audit log: record blocked action, source, and governing policy key (`production_ingest_allowed`, `answer_citation_allowed`, or `export_fulltext_allowed`) with request ID.

### Exit criteria

- Rights matrix approved by legal/compliance.
- Gate unit tests pass.
- No bypass paths in API/UI flows.

## 5. Workstream B: Phase 1 Connectors (SCC, FC, FCA) (Weeks 1-3)

### Implementation tasks

1. Build/finish source adapters for SCC, FC, FCA.
2. Add incremental sync with checkpointing and resumable cursors.
3. Enforce per-source throttling and retry budgets in adapter layer.
4. Implement metadata validation and source filtering.
5. Implement deterministic document identity and dedupe.

### Required safeguards

1. Year validation
- Verify requested year/date window matches returned document metadata.
- Reject/flag mismatches for manual review.

2. Citation validation
- Validate court-specific citation patterns and metadata completeness.
- Reject records with invalid citation format into quarantine queue.

3. Source filtering
- Keep only whitelisted collections for each connector.
- Drop cross-court/noise records from feed anomalies.

4. Per-source throttling
- Token bucket or equivalent limiter per source.
- Centralized config for `rps`, burst, timeout, retries.

### Exit criteria

- Connector smoke runs complete with zero fatal ingestion errors.
- Safeguard checks are exercised in tests and logs.
- Freshness lag from source publication to index is below `24h` (see Workstream D initial thresholds in Section 7).

## 6. Workstream C: Conformance Test Suite (Weeks 2-3)

### Test categories

1. Endpoint health
- Feed/search endpoints reachable.
- Error handling for timeouts and transient HTTP failures.

2. PDF retrieval
- `document.do` download works for sampled decisions.
- MIME and file-integrity checks pass.

3. Metadata completeness
- Required fields present: title, date, court, citation, source URL, document ID.

4. Rights enforcement behavior
- Blocked source in production is rejected.
- Citation-only mode works when export is forbidden.
- Audit records created for blocked operations.

### Required CI gates

- Conformance suite must pass in staging before pilot.
- Any rights-enforcement failure is release-blocking.

## 7. Workstream D: Pilot Ingestion + Retrieval Evaluation (Week 4)

### Pilot design

- Pilot sources: SCC + FC + FCA only.
- Fixed question set covering immigration/federal jurisprudence use cases.
- Include low-confidence and missing-evidence prompts by design.

### Metrics

- `freshness_lag_hours`
- `citation_presence_rate`
- `parse_success_rate`
- `refusal_on_low_confidence_rate`
- `unsupported_claim_rate`

### Initial thresholds

- Freshness lag: `< 24h`
- Citation presence: `>= 99%` on factual legal responses
- Parse success: `>= 98%`
- Refusal on low confidence: `>= 95%`
- Unsupported claim rate: `<= 1%`

### Go/No-Go rule

- Promote only if all thresholds pass for two consecutive pilot runs.
- If any threshold fails: block promotion, open corrective action, rerun pilot.

## 8. Workstream E: Commercial Provider Diligence (Parallel, Weeks 1-4)

### Provider track

- Candidates: vLex (vLex Canada), Lexum / CanLII API (commercial tier, if available), and other licensed providers.
- Collect API and contract evidence in `artifacts/compliance/provider-diligence/`.

### Evaluation criteria

1. Coverage depth for Canada immigration/federal case law.
2. Full-text rights and redistribution permissions.
3. SLA, quota model, and incident escalation process.
4. Cost and overage behavior.
5. Attribution/citation requirements.

### Decision outcome

- If provider passes legal + technical review: add as Phase 2 fallback/coverage expansion.
- If not: continue with official-source-first architecture and revisit quarterly.

### Exit criteria

- Provider diligence memo delivered by end of Week 4.
- Legal review verdict (`proceed`/`defer`/`reject`) stored under `artifacts/compliance/provider-diligence/`.
- Coverage/SLA threshold is met, or an explicit official-source-first fallback decision is documented.
- Final go/no-go decision recorded before Week 4 production-promotion checkpoint.

## 9. Execution Timeline (Target)

1. Week 1
- Rights matrix finalization and policy gate implementation.
- SCC/FC/FCA connector hardening: Day 3-4 adapters/validation/throttling implementation.
- Start provider diligence.

2. Week 2
- SCC/FC/FCA connector hardening: Day 5-6 conformance tests and safeguard integration.
- Conformance tests added in CI.

3. Week 3
- Complete conformance stabilization.
- Dry-run ingestion and defect burn-down.

4. Week 4
- Pilot evaluation runs and go/no-go decision.
- Production promotion if gates pass.

## 9.1 Critical Path and Parallelization Plan

Critical path (`P0`):

1. `A1` Create `config/source_policy.yaml` and `artifacts/compliance/source-rights-matrix.md`.
2. `A2` Enforce policy gates in ingestion/retrieval/export paths.
3. `B1` Implement SCC/FC/FCA adapters and validation safeguards.
4. `C1` Add conformance tests and wire as release blockers.
5. `D1` Run pilot twice and enforce go/no-go criteria.

Parallel lanes (run at the same time):

1. Lane A (Policy/Compliance): rights matrix, source policy loader, audit events.
2. Lane B (Connectors/Ingestion): SCC/FC/FCA adapters, throttling, checkpointing, metadata guards.
3. Lane C (Quality/CI): conformance tests, workflow gates, staging smoke.
4. Lane D (Eval/Ops): pilot scorecards, SLO metrics, alert escalation.
5. Lane E (Commercial): provider diligence and contract/legal reviews.

Recommended agent assignment model:

1. Agent 1: Policy gates + rights matrix artifacts.
2. Agent 2: Connector implementation + ingestion safeguards.
3. Agent 3: Conformance tests + CI release gating.
4. Agent 4: Pilot evaluation + metrics/alerts integration.
5. Agent 5: Provider diligence tracker and decision memo.

## 10. Ownership Model

- `Engineering`: adapters, gates, tests, observability, pilot execution.
- `Legal/Compliance`: rights matrix approvals and provider contract constraints.
- `Product`: source priorities, acceptance criteria, rollout sequencing.
- `Operations`: runbooks, incident response, rollback readiness.

## 11. Production Readiness Checklist

- [ ] Rights matrix approved and versioned.
- [ ] A2AJ/RLL production policy remains blocked unless signed approval exists.
- [ ] SCC/FC/FCA connectors pass conformance and pilot thresholds.
- [ ] Citation and refusal behavior meet quality gates.
- [ ] Rollback and incident runbooks validated.

## 12. Immediate Next Actions (This Week)

1. Finalize `config/source_policy.yaml` with legal and engineering sign-off.
2. Implement remaining SCC/FC/FCA safeguards (year/citation/source filtering/throttling).
3. Add conformance test module and wire into CI release gates.
4. Run first pilot ingestion + retrieval eval and publish scorecard.
5. Open provider diligence tracker and legal review cadence.

## 13. First 10 Business Days (Step-by-Step)

Day 1-2:

1. Create `config/source_policy.yaml` and `artifacts/compliance/source-rights-matrix.md`.
2. Add policy loader and schema validation tests.
3. Wire environment-aware source allow/deny checks into ingestion source selection.

Day 3-4:

1. Implement SCC/FC/FCA adapters and registry entries.
2. Add year-window and citation-format validation; quarantine invalid records.
3. Add per-source throttling config (`rps`, burst, retry, timeout).

Day 5-6:

1. Add conformance tests: endpoint health, PDF retrieval, metadata completeness, rights enforcement.
2. Make rights/conformance failures release-blocking in CI.
3. Run ingestion smoke and fix defects.

Day 7-8:

1. Instrument missing pilot metrics (`freshness_lag_hours`, citation presence, parse success, refusal behavior).
2. Extend `/ops/metrics` and alert evaluator to include these metrics.
3. Add alert escalation step (not just artifact generation).

Day 9-10:

1. Run two pilot cycles on SCC/FC/FCA.
2. Publish pilot scorecards and go/no-go memo.
3. If all thresholds pass, cut production rollout; otherwise open corrective actions and rerun.
