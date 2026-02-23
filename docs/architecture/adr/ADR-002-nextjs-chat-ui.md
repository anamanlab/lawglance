# ADR-002: Adopt Next.js + Tailwind for Frontend Chat Experience

- Status: Accepted
- Date: 2026-02-23
- Deciders: IMMCAD maintainers
- Tags: frontend, ux, architecture

## Context

Current Streamlit UI is not aligned with desired minimalist, production-grade chat UX and frontend extensibility requirements.

## Options Considered

1. Continue with Streamlit UI.
2. Replace UI with Next.js + Tailwind.
3. Use another SPA framework.

## Decision

Adopt Next.js + Tailwind for frontend; backend remains Python API.

## Rationale

This provides better UI control, performance tuning, and long-term frontend maintainability while preserving backend investment.

## Trade-offs

- Gains: stronger UX, modern frontend ecosystem.
- Costs: additional frontend codebase and deployment pipeline.
- Risks: integration complexity between frontend and backend.

## Consequences

- Positive: cleaner separation of concerns.
- Negative: more moving parts than single-process Streamlit.
- Mitigation: stable API contract and integration tests.

## Revisit Trigger

Revisit if team skill profile or product constraints no longer justify React/Next.js stack.
