# Architecture Decision Records (ADR)

## Table of Contents

- [Table of Contents](#table-of-contents)
- [Purpose](#purpose)
- [Naming](#naming)
- [Status Values](#status-values)
- [Current ADR Index](#current-adr-index)
- [Workflow](#workflow)
- [Review Cadence](#review-cadence)

## Purpose

ADRs document significant architecture decisions with context, alternatives, and trade-offs.

## Naming

- File format: `ADR-XXX-short-title.md`
- Example: `ADR-003-provider-abstraction-with-gemini-fallback.md`

## Status Values

- `Proposed`
- `Accepted`
- `Superseded`
- `Deprecated`

## Current ADR Index

- `ADR-001-modular-monolith-python-backend.md`
- `ADR-002-nextjs-chat-ui.md`
- `ADR-003-provider-abstraction-with-gemini-fallback.md`
- `ADR-004-citation-required-policy-gate.md`
- `ADR-005-observability-tracing-first.md`
- `ADR-006-architecture-documentation-as-code-governance.md`

## Workflow

1. Create ADR using `ADR-000-template.md`.
2. Link related issues/design discussions.
3. Review in PR with architecture-impacting changes.
4. If replaced, mark old ADR as `Superseded` and reference replacement.

## Review Cadence

- Per PR: architecture-impacting changes must include an ADR or an explicit note explaining why an ADR is not required.
- Quarterly: review accepted ADRs for supersession, drift, or outdated assumptions.
- Release readiness: verify ADRs and `docs/architecture/*` remain consistent with deployment/runtime posture.
