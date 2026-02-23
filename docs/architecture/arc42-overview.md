# Arc42 Overview (Project-Specific)

## 1. Introduction and Goals

IMMCAD provides citation-grounded, Canada-immigration informational assistance with a minimalist chat interface and compliance-first behavior.

## 2. Constraints

- Python-first backend for MVP velocity.
- Must support Gemini fallback from day one.
- Must enforce legal disclaimer and citation-required response policy.

## 3. Context and Scope

See `01-system-context.md` for external systems and trust boundaries.

## 4. Solution Strategy

- Modular monolith backend.
- Next.js frontend.
- Provider abstraction with fallback routing.
- Source-governed ingestion and retrieval.

## 5. Building Block View

See:
- `02-container-and-service-architecture.md`
- `03-component-and-module-architecture.md`

## 6. Runtime View

Primary runtime: user request -> retrieval -> policy checks -> provider execution -> citation validator -> response.

## 7. Deployment View

See `07-deployment-and-operations.md`.

## 8. Cross-Cutting Concepts

- Security/compliance: `05-security-and-compliance-architecture.md`
- Quality attributes: `06-quality-attributes-and-cross-cutting.md`
- ADR process: `adr/README.md`

## 9. Architectural Decisions

See `adr/`.

## 10. Quality Requirements

Documented SLO targets and observability expectations in `06-quality-attributes-and-cross-cutting.md`.

## 11. Risks and Technical Debt

See `08-architecture-debt-and-improvement-plan.md`.

## 12. Glossary

- RAG: Retrieval-Augmented Generation.
- PIPEDA: Personal Information Protection and Electronic Documents Act.
- ADR: Architecture Decision Record.
