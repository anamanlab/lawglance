# Arc42 Overview (Project-Specific)

## Table of Contents

- [1. Introduction and Goals](#1-introduction-and-goals)
- [2. Constraints](#2-constraints)
- [3. Context and Scope](#3-context-and-scope)
- [4. Solution Strategy](#4-solution-strategy)
- [5. Building Block View](#5-building-block-view)
- [6. Runtime View](#6-runtime-view)
- [7. Deployment View](#7-deployment-view)
- [8. Cross-Cutting Concepts](#8-cross-cutting-concepts)
- [9. Architectural Decisions](#9-architectural-decisions)
- [10. Quality Requirements](#10-quality-requirements)
- [11. Risks and Technical Debt](#11-risks-and-technical-debt)
- [12. Glossary](#12-glossary)

## 1. Introduction and Goals

IMMCAD delivers citation-aware, policy-constrained informational responses for Canadian immigration queries through a production runtime of Next.js + FastAPI.

## 2. Constraints

- Python 3.11 backend and existing package layout must be preserved.
- Hardened environments require strict runtime controls (`API_BEARER_TOKEN`, trusted citation domains, synthetic citation toggle off).
- Legal/compliance controls are release gating requirements, not optional checks.

## 3. Context and Scope

See `01-system-context.md` for system boundary, personas, and external dependencies.

## 4. Solution Strategy

- Modular monolith backend with explicit packages.
- Provider abstraction with ordered fallback and telemetry.
- Source-governed ingestion and policy-aware execution.
- CI-enforced architecture and documentation checks.

## 5. Building Block View

See:

- `02-container-and-service-architecture.md`
- `03-component-and-module-architecture.md`

## 6. Runtime View

Primary request flow:

`HTTP request -> middleware auth/rate limit/trace -> service orchestration -> provider routing -> policy enforcement -> response with trace metadata`

## 7. Deployment View

See `07-deployment-and-operations.md` for environment topology and operational ownership.

## 8. Cross-Cutting Concepts

- Security/compliance: `05-security-and-compliance-architecture.md`
- Quality and observability: `06-quality-attributes-and-cross-cutting.md`
- Documentation/automation: `09-documentation-automation.md`
- ADR process: `adr/README.md`

## 9. Architectural Decisions

See `adr/` for accepted and superseded decisions.

## 10. Quality Requirements

Latency, reliability, security, and telemetry expectations are defined in `06-quality-attributes-and-cross-cutting.md`.

## 11. Risks and Technical Debt

See `08-architecture-debt-and-improvement-plan.md` and `codebase-audit-plan-2026-02-24.md`.

## 12. Glossary

- ADR: Architecture Decision Record.
- C4: Context/Container/Component/Code modeling framework.
- Arc42: architecture documentation template and structure.
- RAG: Retrieval-Augmented Generation.
