# ADR-003: Provider Abstraction with Gemini Fallback

## Table of Contents

- [Context](#context)
- [Options Considered](#options-considered)
- [Decision](#decision)
- [Rationale](#rationale)
- [Trade-offs](#trade-offs)
- [Consequences](#consequences)
- [Revisit Trigger](#revisit-trigger)

- Status: Accepted
- Date: 2026-02-23
- Updated: 2026-02-24
- Deciders: IMMCAD maintainers
- Tags: llm, reliability, architecture

## Context

Single-provider dependency creates availability and resilience risks. The runtime requires ordered fallback while preserving a stable response contract and policy enforcement path.

## Options Considered

Options 1-3 are mutually exclusive base strategies:

1. Single provider only.
2. Provider abstraction with OpenAI primary and Gemini fallback.
3. Equal-weight multi-provider routing always-on.
4. Optional augmentation to Option 2: dev-only scaffold fallback in addition to primary/fallback providers.

## Decision

Use provider abstraction with ordered fallback:

- Primary provider: OpenAI (when enabled and selected as primary). If the configured primary is unavailable/disabled, `ProviderRouter` deterministically promotes the next configured provider as the effective primary.
- First fallback: Gemini (or next configured provider in deterministic order).
- Optional non-production safety fallback: Scaffold provider.

Provider order and failover are managed by `ProviderRouter` with circuit-breaker telemetry.

## Rationale

This improves runtime resilience while keeping behavior predictable and implementation complexity moderate. It avoids overfitting to dynamic multi-provider routing before sufficient production signal exists.

## Trade-offs

- Gains: graceful degradation and lower outage risk.
- Costs: adapter maintenance and broader test matrix.
- Risks: provider output variance requiring stronger policy and regression checks.

## Consequences

- Positive: reduced dependency on a single upstream provider.
- Negative: fallback behavior must be continuously observed and tuned.
- Mitigation: standardized response schema, policy gate enforcement, circuit-breaker telemetry (ProviderRouter), and release-gate checks.

## Revisit Trigger

Revisit when traffic, cost, or latency profiles justify policy-aware dynamic routing instead of fixed ordered fallback.
