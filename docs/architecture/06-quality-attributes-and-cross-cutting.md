# 06. Quality Attributes and Cross-Cutting Concerns

## Performance

Targets (MVP):

- P50 chat latency: <= 3.0s
- P95 chat latency: <= 8.0s
- Fallback activation overhead: <= 2.0s additional in P95

Approach:

- Query rewrite + bounded retrieval k.
- Cache repeated query/session combinations.
- Provider timeout budgets and short retry policy.

## Reliability and Availability

Targets:

- API success rate: >= 99.0% (MVP target)
- Graceful degradation on provider failure.

Approach:

- Primary provider with Gemini fallback.
- Optional Grok fallback behind feature flag.
- Circuit breaker for provider error storms.

## Security

Targets:

- Authentication and authorization enforced on all `/api/*` routes in production.
- Correlation/session identifiers propagated for incident traceability.
- No plaintext credentials in source control or local logs.
- PII handling follows minimization and redaction policies.

Approach:

- AuthN/AuthZ middleware with bearer/JWT controls and session/correlation ID handling.
- API keys and credentials stored in secrets managers with scheduled rotation policy.
- Input validation/sanitization with strict bounds, schema validation, and PII-safe logging.
- Rate limiting and abuse prevention controls (throttling, anomaly detection, deny rules).
- TLS-secured communication to all providers and external APIs.
- Logging/privacy constraints: redact secrets, avoid raw personal data, enforce retention limits.

## Observability

- Structured logs with correlation ID and session ID.
- Metrics: latency, retrieval hit quality, policy block rate, fallback rate.
- Tracing for orchestration and tool calls.

## Maintainability

- Clear module boundaries and adapter interfaces.
- ADR-based decision process.
- Documentation validation in CI.

## Evolution Strategy

- Start with modular monolith.
- Extract ingestion worker first if needed.
- Extract independent provider gateway only when justified by scale.

## Business Continuity

- Backup vector artifacts and metadata snapshots.
- Define cold-start rebuild process for indexes.
- Runbook for provider outage mode.
