# Chat API Scaffold: Potential Issues and Mitigations

## Table of Contents

- [Table of Contents](#table-of-contents)
- [1. Error Contract Drift](#1-error-contract-drift)
- [2. Unprotected API Surface](#2-unprotected-api-surface)
- [3. Fallback Observability Ambiguity](#3-fallback-observability-ambiguity)
- [4. CanLII Integration Risk](#4-canlii-integration-risk)
- [5. Remaining Gaps (not yet solved)](#5-remaining-gaps-(not-yet-solved))

- [1. Error Contract Drift](#1-error-contract-drift)
- [2. Unprotected API Surface](#2-unprotected-api-surface)
- [3. Fallback Observability Ambiguity](#3-fallback-observability-ambiguity)
- [4. CanLII Integration Risk](#4-canlii-integration-risk)
- [5. Remaining Gaps (not yet solved)](#5-remaining-gaps-(not-yet-solved))

## 1. Error Contract Drift

Issue:
- Framework default validation responses can drift from API contract.

Mitigation implemented:
- Added global validation handler returning standardized error envelope with `trace_id`.

## 2. Unprotected API Surface

Issue:
- Endpoints were publicly callable without any auth control.

Mitigation implemented:
- Added bearer-token gate for all `/api/*` routes via `IMMCAD_API_BEARER_TOKEN` (`API_BEARER_TOKEN` accepted as compatibility alias).
- Policy: `IMMCAD_API_BEARER_TOKEN` is required and enforced in production + CI environments (with `API_BEARER_TOKEN` alias compatibility); it may be optional for local development/ephemeral test runs only when guarded by developer-only configuration.
- Store tokens in a secrets manager (not in source control), and rotate them on a fixed schedule or after suspected exposure.

## 3. Fallback Observability Ambiguity

Issue:
- Fallback reason was hardcoded to `provider_error`, losing routing context.

Mitigation implemented:
- Propagate router-level fallback reason into response contract.

## 4. CanLII Integration Risk

Issue:
- Endpoint originally returned deterministic data only.

Mitigation implemented:
- Added `CanLIIClient` integration boundary with graceful fallback when key/network/endpoint fails.

## 5. Remaining Gaps (not yet solved)

- No production-grade authN/authZ (JWT, RBAC, key rotation).
- Current rate limiting is Redis-backed when available but still fixed-window and coarse; no per-user quota model yet.
- No persistent request audit store.
- CanLII endpoint mapping may require adjustment once API key is provisioned and tested against real datasets.
- Provider adapters are scaffold-level and need real SDK call paths with timeout/retry/circuit-breaker behavior.
