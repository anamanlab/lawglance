# 09. Documentation Automation and Maintenance

## Table of Contents

- [Automation Goals](#automation-goals)
- [Tooling](#tooling)
- [Team Process](#team-process)
- [Review Checklist](#review-checklist)
- [Versioning and Change Management](#versioning-and-change-management)

## Automation Goals

- Keep architecture docs complete and synchronized with code evolution.
- Validate required architecture sections and ADR presence in CI.
- Generate a module dependency diagram from Python imports.

## Tooling

- Diagram-as-code: Mermaid in markdown.
- Validation script: `scripts/validate_architecture_docs.sh`.
- Diagram generation script: `scripts/generate_module_dependency_diagram.py`.
- CI workflow: `.github/workflows/architecture-docs.yml`.

## Team Process

1. For architecture-impacting changes, update impacted docs under `docs/architecture/`.
2. For major decisions, add a new ADR in `docs/architecture/adr/`.
3. Run validation locally before PR:

```bash
./scripts/generate_module_dependency_diagram.py
./scripts/validate_architecture_docs.sh
```

4. CI enforces this on pull requests.

## Review Checklist

- Context/container/component/data/security docs updated.
- API contracts updated when interfaces change.
- New decision captured in ADR with alternatives and trade-offs.
- Generated module dependency diagram refreshed.

## Versioning and Change Management

- Architecture docs live with code and follow git history.
- ADR status must be maintained (`Proposed`, `Accepted`, `Superseded`).
- Superseded decisions should link forward to replacement ADR.
