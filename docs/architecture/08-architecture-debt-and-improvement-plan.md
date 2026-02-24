# 08. Architecture Debt and Improvement Plan

## Table of Contents

- [Table of Contents](#table-of-contents)
- [Current Debt](#current-debt)
- [Risk Assessment](#risk-assessment)
- [Improvement Backlog (Prioritized)](#improvement-backlog-(prioritized))
- [Success Criteria](#success-criteria)

- [Current Debt](#current-debt)
- [Risk Assessment](#risk-assessment)
- [Improvement Backlog (Prioritized)](#improvement-backlog-(prioritized))
- [Success Criteria](#success-criteria)

## Current Debt

1. Legacy Streamlit `app.py` is still present for local/dev workflows and requires continued deprecation controls to avoid production usage.
2. Production vector database is still using legacy Indian legal data (requires full purge/rebuild).
3. Prompt ownership convergence must remain enforced so archive modules cannot diverge from backend policy prompts.
4. No automated runtime "Grounding" layer verifies citations before user delivery.
5. Notebook-era ingestion artifacts still exist and should be fully replaced by script-driven jobs.

## Risk Assessment

- **High**: Jurisdictional Hallucination (mixing Indian vs Canadian laws).
- **High**: Citation mismatch (LLM cites non-existent IRPR sections).
- **Medium**: Single-language limitation (lacks French support for official compliance).

## Improvement Backlog (Prioritized)

1. **[HIGH] Data Migration**: Purge legacy vectors; ingest IRPA/IRPR and IRCC sources into a new "Canada" collection.
2. **[HIGH] Prompt Convergence**: Keep `src/immcad_api/policy/prompts.py` as canonical prompt source and prevent legacy archive imports into active codepaths.
3. **[MEDIUM] Legacy Decommissioning**: Keep Streamlit `app.py` marked dev-only in docs/tooling and route production traffic exclusively through `frontend-web` + `immcad_api`.
4. **[MEDIUM] Observability Rollout**: Finalize the telemetry implementation in `src/immcad_api/telemetry` to capture all provider latency/error metrics.
5. **[LOW] Quality Evaluation**: Implement the benchmark-based evaluation harness to score groundedness on 50 sample Canadian immigration queries.

## Success Criteria

- Every legal factual response includes citations or explicit refusal.
- Provider outage does not fully break service.
- Architecture docs and ADRs are updated with each major design change.
