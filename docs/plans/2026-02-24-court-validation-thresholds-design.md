# Court Validation Thresholds Design (2026-02-24)

## Goal
Make court payload validation production-safe by allowing a small amount of bad records without failing the whole ingestion job, while preserving strict validation when configured.

## Requirements
- Validate SCC/FC/FCA payload records for citation/metadata shape.
- Allow ingestion success when invalid records are below a configurable ratio threshold.
- Require a configurable minimum count of valid records.
- Support optional expected-year validation with a configurable +/- year window.
- Keep defaults backward-compatible (strict).

## Options Considered
1. Enforce thresholds only in `ingestion/jobs.py`
- Pros: minimal surface area.
- Cons: duplicates ratio logic and makes unit-testing court validation behavior harder.

2. Add threshold config into `canada_courts.py` and apply in ingestion
- Pros: centralizes validation semantics and improves testability.
- Cons: slightly larger API change.

## Decision
Use option 2 with a small `CourtPayloadValidationConfig` dataclass and summary helpers, then enforce acceptance in `ingestion/jobs.py`.

## Acceptance Criteria
- Ingestion job succeeds when court payload has a small invalid ratio within configured limit and enough valid records.
- Ingestion job fails when invalid ratio exceeds limit.
- Year-window validation accepts records within configured range and rejects outside it.
- Existing strict behavior remains the default when no config is passed.

