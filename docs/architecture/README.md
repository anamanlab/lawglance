# Architecture Documentation

## Table of Contents

- [Scope](#scope)
- [Documentation Framework](#documentation-framework)
- [Contents](#contents)
- [How to Use](#how-to-use)
- [Ownership](#ownership)

This directory contains the authoritative architecture documentation for IMMCAD.

## Scope

- Current architecture baseline (Streamlit + LangChain + Chroma + Redis).
- Target architecture for Canada-focused legal assistant (Next.js UI + Python API backend + provider abstraction).
- Security, compliance, data, quality, and operations architecture.
- Architecture Decision Records (ADRs).

## Documentation Framework

- C4 model: system context, container, and component views.
- Arc42-style narrative sections for quality attributes, constraints, risks, and evolution.
- Diagram-as-code using Mermaid.
- ADR process for decision traceability.

## Contents

1. `01-system-context.md`
2. `02-container-and-service-architecture.md`
3. `03-component-and-module-architecture.md`
4. `04-data-architecture.md`
5. `05-security-and-compliance-architecture.md`
6. `06-quality-attributes-and-cross-cutting.md`
7. `07-deployment-and-operations.md`
8. `08-architecture-debt-and-improvement-plan.md`
9. `09-documentation-automation.md`
10. `arc42-overview.md`
11. `api-contracts.md`
12. `adr/`

## How to Use

- Start at `01-system-context.md` for boundaries and stakeholders.
- Review `api-contracts.md` before implementing frontend/backend integrations.
- Record major design changes in a new ADR under `adr/` before implementation.
- Run `./scripts/validate_architecture_docs.sh` before opening a PR.

## Ownership

- Primary owners: maintainers of backend orchestration and platform architecture.
- Every PR changing architecture-sensitive areas must update relevant docs and ADRs.
