# ADR-001: Use Modular Monolith Backend in Python for MVP

- Status: Accepted
- Date: 2026-02-23
- Deciders: IMMCAD maintainers
- Tags: backend, architecture, mvp

## Context

Current codebase is Python-based and tightly integrated with Streamlit. MVP priority is rapid delivery with controlled complexity.

## Options Considered

1. Keep Streamlit-coupled architecture.
2. Build modular monolith backend in Python.
3. Split into microservices immediately.

## Decision

Adopt a modular monolith backend with clear internal boundaries and API-first interfaces.

## Rationale

It preserves team velocity, reuses current Python logic, and avoids premature distributed-system complexity.

## Trade-offs

- Gains: faster implementation and lower operational overhead.
- Costs: less independent scaling than microservices.
- Risks: module boundary erosion if governance is weak.

## Consequences

- Positive: simpler deployment and debugging.
- Negative: potential growth bottlenecks if boundaries are ignored.
- Mitigation: strict module ownership and interface contracts.

## Revisit Trigger

Revisit when sustained load or team structure requires independent service scaling.
