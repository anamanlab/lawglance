# Architecture Documentation

## Table of Contents

- [Scope](#scope)
- [Documentation Framework](#documentation-framework)
- [Contents](#contents)
- [How to Use](#how-to-use)
- [Validation and Automation](#validation-and-automation)
- [Ownership](#ownership)

This directory contains the authoritative architecture documentation for IMMCAD.

## Scope

- Production runtime baseline: Next.js (`frontend-web`) + FastAPI (`src/immcad_api`) with provider routing, policy gates, and ingestion jobs.
- Legacy development/runtime compatibility: Streamlit thin client (`app.py`) and archived local-RAG modules (`legacy/local_rag`).
- Security, compliance, data, deployment, quality, and operations architecture.
- Architecture Decision Records (ADRs) and documentation governance.

## Documentation Framework

- C4 model for system context, container, and component views.
- Arc42-style narrative for constraints, quality attributes, risks, and evolution.
- Mermaid diagrams as code.
- ADR process for decision traceability and change history.

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
13. `diagrams/`

## How to Use

- Start at `01-system-context.md` for boundaries and external dependencies.
- Use `02-03` when changing runtime topology, module boundaries, or integration flow.
- Use `api-contracts.md` before frontend/backend contract changes.
- Record architecture-impacting decisions in a new ADR under `adr/`.
- Keep docs aligned with implementation in the same PR as architecture changes.

## Validation and Automation

- Local checks:

```bash
make arch-generate
make arch-validate
make docs-audit
```

- CI checks:
  - `.github/workflows/architecture-docs.yml`
  - `.github/workflows/quality-gates.yml`

## Ownership

- Primary owners: backend/platform maintainers.
- Any PR that changes architecture-sensitive code must update this directory and ADRs as needed.
