# Architecture Documentation

## Table of Contents

- [Table of Contents](#table-of-contents)
- [Scope](#scope)
- [Documentation Framework](#documentation-framework)
- [Coverage Map](#coverage-map)
- [Contents](#contents)
- [How to Use](#how-to-use)
- [Ownership](#ownership)

This directory contains the authoritative architecture documentation for IMMCAD.

## Scope

- Production architecture baseline (Next.js UI + Python API backend + provider abstraction + Chroma + Redis).
- Legacy development path (`app.py` Streamlit UI) retained for local prototype and troubleshooting workflows only.
- Security, compliance, data, quality, and operations architecture.
- Architecture Decision Records (ADRs).

## Documentation Framework

- C4 model: system context, container, and component views.
- Arc42-style narrative sections for quality attributes, constraints, risks, and evolution.
- Diagram-as-code using Mermaid.
- ADR process for decision traceability.
- CI validation via `scripts/validate_architecture_docs.sh` and `.github/workflows/architecture-docs.yml`.

## Coverage Map

- **Architecture analysis and discovery**: `10-architecture-analysis-and-governance.md`, `08-architecture-debt-and-improvement-plan.md`
- **C4 system context**: `01-system-context.md`
- **Container/service architecture**: `02-container-and-service-architecture.md`, `07-deployment-and-operations.md`, `api-contracts.md`
- **Component/module architecture**: `03-component-and-module-architecture.md`, `diagrams/generated-module-dependencies.mmd`
- **Data architecture**: `04-data-architecture.md`
- **Security/compliance**: `05-security-and-compliance-architecture.md`
- **Quality attributes/cross-cutting concerns**: `06-quality-attributes-and-cross-cutting.md`
- **ADR process and decisions**: `adr/README.md`, `adr/ADR-000-template.md`, `adr/ADR-001...`
- **Automation and maintenance**: `09-documentation-automation.md`, `10-architecture-analysis-and-governance.md`

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
10. `10-architecture-analysis-and-governance.md`
11. `arc42-overview.md`
12. `api-contracts.md`
13. `adr/`

## How to Use

- Start at `01-system-context.md` for boundaries and stakeholders.
- Review `api-contracts.md` before implementing frontend/backend integrations.
- Use `10-architecture-analysis-and-governance.md` for current-state evidence, governance rules, and backlog.
- Record major design changes in a new ADR under `adr/` before implementation.
- Run `./scripts/validate_architecture_docs.sh` before opening a PR.

## Ownership

- Primary owners: maintainers of backend orchestration and platform architecture.
- Every PR changing architecture-sensitive areas must update relevant docs and ADRs.
