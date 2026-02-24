# Architecture Decision Records (ADR)

## Table of Contents

- [Purpose](#purpose)
- [Naming](#naming)
- [Status Values](#status-values)
- [Workflow](#workflow)
- [Review Cadence](#review-cadence)

## Purpose

ADRs capture architecture decisions with context, alternatives, and trade-offs so future changes can be reasoned from evidence rather than memory.

## Naming

- File format: `ADR-XXX-short-title.md`
- Example: `ADR-003-provider-abstraction-with-gemini-fallback.md`

## Status Values

- `Proposed`
- `Accepted`
- `Superseded`
- `Deprecated`

## Workflow

1. Create ADR from `ADR-000-template.md`.
2. Link relevant issue/task/design references.
3. Include options, trade-offs, and explicit decision statement.
4. Merge ADR in the same PR as architecture-impacting code.
5. If replaced later, mark old ADR as `Superseded` and reference the replacement.

## Review Cadence

- Review accepted ADRs when a core subsystem changes materially.
- During release readiness, verify ADR set still reflects runtime reality.
- Avoid editing history silently; if an ADR is changed or replaced, create a new ADR and mark the old ADR as `Superseded`.
