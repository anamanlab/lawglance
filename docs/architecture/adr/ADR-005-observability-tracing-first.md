# ADR-005: Tracing-First Observability for Agent Orchestration

- Status: Accepted
- Date: 2026-02-23
- Deciders: IMMCAD maintainers
- Tags: observability, operations, reliability

## Context

Current state before this ADR: application logs are present but mostly unstructured, no consistent distributed trace propagation exists across API -> provider -> policy paths, and metrics coverage is limited to coarse process health. During scaffold testing, incidents such as ambiguous fallback behavior and policy-gate mismatches required manual log stitching across files.

Operational impact observed in pre-MVP runs: incident triage commonly takes 30-60 minutes, provider failure root-cause analysis frequently requires ad hoc reproduction, and 1-2 observability-related debugging events occur per week during active development.

Constraints influencing the decision: small engineering team, strict privacy expectations for user/legal queries, budget limits for managed telemetry platforms, and a desire to avoid early vendor lock-in before signal quality is validated.

## Options Considered

1. **Basic logs only**: lowest implementation effort and near-zero incremental cost, but weak diagnostic capability for cross-component causality and higher operational overhead during incidents due to manual correlation.
2. **Structured logs + metrics + distributed traces**: moderate implementation effort, manageable operating cost, and strong diagnostic capability for latency and failure attribution with fast time-to-value.
3. **Full APM platform immediately**: highest complexity and cost with strong diagnostics, but significant onboarding/maintenance overhead and slower practical time-to-value for a small team.

Selected option 2 because it materially improves diagnosis speed and reliability now, while avoiding the underpowered visibility of option 1 and the premature cost/complexity of option 3.

## Decision

Adopt structured logs, key metrics, and orchestration traces from MVP onward.

## Rationale

Basic logs alone are insufficient because they do not provide reliable cross-service/request correlation or clear latency causality through orchestration, provider routing, and policy gates. We need structured telemetry to support root-cause analysis, distributed latency profiling, and consistent MTTR reduction during incidents.

A full APM rollout is premature at current scale because of platform cost, operational overhead, and unresolved signal-selection/privacy practices. Structured logs + lightweight metrics + tracing provides immediate observability gains while preserving an upgrade path to full APM when scale and team capacity justify it.

## Trade-offs

- Gains: faster incident debugging and better reliability tuning.
- Costs: additional implementation work and telemetry storage costs.
- Risks: accidental logging of sensitive payloads.

## Consequences

- Positive: measurable SLO tracking and fallback diagnostics.
- Negative: telemetry noise if schema is not curated.
- Mitigation: standard logging schema and sensitive-data redaction policy.

## Revisit Trigger

Revisit this decision when any of the following occurs: sustained traffic above 10K requests/sec, engineering team size above 20, telemetry spend above USD 5,000/month, or MTTR remains above 30 minutes for three consecutive months. Perform a mandatory architecture review every 12 months even if thresholds are not exceeded.
