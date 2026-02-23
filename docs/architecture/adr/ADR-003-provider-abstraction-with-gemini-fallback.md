# ADR-003: Provider Abstraction with Gemini Fallback

- Status: Accepted
- Date: 2026-02-23
- Deciders: IMMCAD maintainers
- Tags: llm, reliability, architecture

## Context

Single-provider dependency creates availability and resilience risks. User requirement includes Gemini fallback and optional Grok support. OpenAI is currently the best-supported provider in the existing codebase and provides the strongest compatibility with current prompt and response handling.

## Options Considered

1. Single provider only.
2. Provider abstraction with Gemini fallback (and optional Grok).
3. Equal-weight multi-provider routing always-on.

## Decision

Use provider abstraction with ordered fallback: Primary provider: OpenAI (attempted first), Gemini as ordered fallback (second), Grok optional via feature flag.

## Rationale

Improves reliability while limiting complexity compared to dynamic multi-provider routing. OpenAI remains primary because it is the most mature integration in this repository, has known behavior under current prompts, and minimizes migration risk while fallback paths are hardened.

## Trade-offs

- Gains: graceful degradation and reduced downtime risk.
- Costs: adapter maintenance and more integration tests.
- Risks: behavior differences across models/providers.

## Consequences

- Positive: improved resilience under provider outage.
- Negative: output consistency challenges.
- Mitigation: normalized response schema, policy validation, regression tests.

## Revisit Trigger

Revisit when traffic patterns justify intelligent routing based on cost/latency/quality scores.
