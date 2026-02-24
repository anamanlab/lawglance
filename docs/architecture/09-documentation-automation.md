# 09. Documentation Automation and Maintenance

## Table of Contents

- [Automation Goals](#automation-goals)
- [Maintenance Architecture](#maintenance-architecture)
- [Validation Coverage](#validation-coverage)
- [Operational Commands](#operational-commands)
- [CI Integration](#ci-integration)
- [Team Process](#team-process)

## Automation Goals

- Keep architecture and product docs accurate, verifiable, and CI-enforced.
- Detect stale architecture narratives when code changes.
- Generate and validate diagram artifacts consistently.
- Keep ADR and architecture-index navigation healthy.

## Maintenance Architecture

Documentation maintenance is implemented by `scripts/doc_maintenance/`:

- `main.py`: orchestrates discovery, checks, optional fixes, and reports.
- `audit.py`: freshness/content checks.
- `validator.py`: internal/external link and asset checks.
- `styler.py`: markdown style and heading structure checks.
- `optimizer.py`: table-of-contents refresh.
- `config.yaml`: rule thresholds and report paths.

Architecture-specific helpers:

- `scripts/generate_module_dependency_diagram.py` -> `docs/architecture/diagrams/generated-module-dependencies.mmd`
- `scripts/validate_architecture_docs.sh` for required architecture files/ADRs/diagram presence.

## Validation Coverage

Current coverage includes:

- required architecture file existence,
- minimum ADR count,
- minimum Mermaid diagram count,
- generated dependency diagram presence,
- markdown freshness/style/link checks,
- artifact generation and upload in CI.

## Operational Commands

```bash
make arch-generate
make arch-validate
make docs-audit
make docs-fix
```

Advanced maintenance runs:

```bash
./scripts/venv_exec.sh python scripts/doc_maintenance/main.py --dry-run --check-external
./scripts/venv_exec.sh python scripts/doc_maintenance/main.py --fix --fail-on medium
```

## CI Integration

- `.github/workflows/architecture-docs.yml`
  - regenerates module dependency diagram,
  - validates architecture documentation bundle.
- `.github/workflows/quality-gates.yml`
  - runs docs maintenance audit,
  - uploads maintenance artifacts.

## Team Process

1. Update architecture docs in the same PR as architecture-impacting code.
2. Add or update ADRs for significant architecture decisions.
3. Run `make arch-validate` and `make docs-audit` before opening PRs; use `make docs-fix` only to refresh generated TOCs (it does not fix broken links, stale content, missing alt text, or other audit findings).
4. Review generated artifacts in CI for drift and unresolved issues; manually resolve non-TOC items listed in `artifacts/docs/doc-maintenance-report.md` (broken links, stale content, alt text, and similar audit findings) before merge.
5. Keep `docs/architecture/README.md` and table of contents synchronized after major additions.
