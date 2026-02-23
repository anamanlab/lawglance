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

1. UI and orchestration are still loosely coupled in legacy `app.py`; migration to `immcad_api` service is ongoing.
2. Production vector database is still using legacy Indian legal data (requires full purge/rebuild).
3. System prompts in `prompts.py` are jurisdictionally ambiguous.
4. No automated "Grounding" layer to verify citations before user delivery.
5. Ingestion pipeline in `src/Constituion_Pdf_Injestion...` is a notebook and needs migration to a production script.

## Risk Assessment

- **High**: Jurisdictional Hallucination (mixing Indian vs Canadian laws).
- **High**: Citation mismatch (LLM cites non-existent IRPR sections).
- **Medium**: Single-language limitation (lacks French support for official compliance).

## Improvement Backlog (Prioritized)

1. **[HIGH] Data Migration**: Purge legacy vectors; ingest IRPA/IRPR and IRCC sources into a new "Canada" collection.
2. **[HIGH] Prompt Engineering**: Rewrite `prompts.py` for strict Canadian legal disclaimer and citation-only behavior.
3. **[MEDIUM] API Integration**: Point Streamlit `app.py` to the new `immcad_api` FastAPI service for production-grade orchestration.
4. **[MEDIUM] Observability Rollout**: Finalize the telemetry implementation in `src/immcad_api/telemetry` to capture all provider latency/error metrics.
5. **[LOW] Quality Evaluation**: Implement the benchmark-based evaluation harness to score groundedness on 50 sample Canadian immigration queries.

## Success Criteria

- Every legal factual response includes citations or explicit refusal.
- Provider outage does not fully break service.
- Architecture docs and ADRs are updated with each major design change.
