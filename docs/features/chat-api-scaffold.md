# Feature: Chat API Scaffold

## Table of Contents

- [Goal](#goal)
- [Requirements](#requirements)
- [Acceptance Criteria](#acceptance-criteria)
- [Out of Scope (this scaffold)](#out-of-scope-(this-scaffold))
- [Files Added](#files-added)
- [Next Implementation Steps](#next-implementation-steps)

## Goal

Create an API-first scaffold that decouples UI from backend orchestration and matches architecture contracts.

## Requirements

- Expose `POST /api/chat` and `POST /api/search/cases`.
- Enforce policy block for legal-advice requests.
- Enforce citation requirement for non-refusal responses.
- Support provider routing with explicit order: primary provider OpenAI (attempted first), fallback provider Gemini.
- Emit `x-trace-id` in responses.

## Acceptance Criteria

- Endpoints return schema-aligned payloads from `docs/architecture/api-contracts.md`.
- Provider router attempts primary provider OpenAI, then fallback providers `[Gemini]` (optional Grok only when feature-flagged).
- When policy block is triggered, response includes refusal and `policy_block` reason.
- Case search endpoint returns deterministic scaffold output for integration wiring.

## Out of Scope (this scaffold)

- Real CanLII API integration.
- Production-grade auth and rate limiting.
- Full retrieval/index integration for Canada corpus.

## Files Added

- `src/immcad_api/main.py`
- `src/immcad_api/api/routes/*`
- `src/immcad_api/services/*`
- `src/immcad_api/providers/*`
- `src/immcad_api/policy/*`
- `src/immcad_api/schemas.py`
- `tests/test_api_scaffold.py`

## Next Implementation Steps

1. Integrate real provider SDK calls with timeout/retry policy.
2. Replace deterministic case search with CanLII adapter.
3. Bind retrieval pipeline and citation extraction from indexed corpus.
4. Add auth, rate limits, and structured observability exporters.
