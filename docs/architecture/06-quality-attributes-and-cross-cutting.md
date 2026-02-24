# 06. Quality Attributes and Cross-Cutting Concerns

## Table of Contents

- [Performance](#performance)
- [Reliability and Availability](#reliability-and-availability)
- [Security and Compliance](#security-and-compliance)
- [Observability](#observability)
- [Maintainability](#maintainability)
- [Evolution Strategy](#evolution-strategy)
- [Business Continuity](#business-continuity)

## Performance

Targets (MVP):

- P50 chat latency <= 3.0s
- P95 chat latency <= 8.0s
- Controlled fallback overhead under provider degradation

Current controls:

- bounded provider timeout and retry budgets,
- API request rate limiting,
- usage limiting for CanLII access,
- request latency tracking in `RequestMetrics`.

## Reliability and Availability

Targets:

- API success rate >= 99.0% (MVP)
- graceful degradation on provider or source instability

Current controls:

- ordered provider routing with circuit-breaker behavior,
- OpenAI primary + Gemini fallback + optional scaffold fallback,
- ingestion smoke checks in CI,
- release-gate workflow checks for staging readiness.

Known risk:

- live court feeds may drift from strict citation assumptions; conformance gates and threshold tuning are required for production resilience.

## Security and Compliance

Core requirements:

- bearer-token protection for `/api/*` and `/ops/*` in hardened environments,
- explicit trusted citation domain configuration in hardened environments,
- refusal policy for disallowed legal-advice/representation prompts,
- source-policy gating for ingestion and export controls.

Controls:

- schema validation + typed models,
- rate limiting and abuse controls,
- secrets in environment variables (not source),
- policy and registry validation in CI.

## Observability

Available telemetry:

- `x-trace-id` response header and error envelope trace IDs,
- request metrics (`requests`, `errors`, `fallback`, `refusal`, latency percentiles),
- provider metrics (success/failure/circuit/fallback counters),
- `GET /ops/metrics` operational snapshot,
- ops alert evaluation pipeline using configured thresholds.

## Maintainability

- modular package structure (`api`, `services`, `providers`, `policy`, `sources`, `ingestion`),
- ADR-driven architecture change tracking,
- architecture documentation validation in CI,
- deterministic smoke scripts for API and ingestion paths.

## Evolution Strategy

- keep modular monolith boundaries until scale requires extraction,
- likely first extraction: ingestion execution path,
- keep provider adapters isolated for future model/routing changes,
- evolve source conformance into release-blocking quality gates.

## Business Continuity

- keep ingestion state/checkpoint artifacts,
- maintain rebuild path for source registry + vector data,
- provide rollback guidance in release workflows,
- preserve legal/compliance evidence artifacts in CI uploads.
