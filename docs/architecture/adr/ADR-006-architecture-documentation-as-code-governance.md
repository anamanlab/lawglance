# ADR-006: Architecture Documentation as Code Governance

## Table of Contents

- [Table of Contents](#table-of-contents)
- [Context](#context)
- [Options Considered](#options-considered)
- [Decision](#decision)
- [Rationale](#rationale)
- [Trade-offs](#trade-offs)
- [Consequences](#consequences)
- [Revisit Trigger](#revisit-trigger)

- Status: Accepted
- Date: 2026-02-24
- Deciders: IMMCAD maintainers
- Tags: architecture, documentation, governance, process

## Context

The repository already contains a substantial architecture documentation set under `docs/architecture/`
with C4 views, arc42-style narratives, ADRs, and a validation workflow. However, governance guidance is
distributed across multiple files, and architecture documentation quality can regress when changes are
made without explicit review discipline (for example, duplicated TOC sections in index/template files).

The team needs a lightweight but explicit rule set for treating architecture documentation as a
first-class artifact alongside code changes.

## Options Considered

1. **Ad hoc documentation updates**
2. **Documentation-as-code with CI validation and ADR-backed governance**
3. **External architecture platform as primary source of truth**

## Decision

Adopt and maintain a documentation-as-code governance model for architecture documentation in this
repository, using Markdown + Mermaid + ADRs + CI validation as the canonical workflow.

## Rationale

Option 2 fits the current team size and repository maturity: it preserves low operational overhead while
keeping architecture decisions and diagrams reviewable in pull requests. It also avoids the adoption cost
and process friction of an external platform before stronger evidence of scale-driven need exists.

## Trade-offs

- Benefits gained: strong reviewability, low tooling cost, versioned history, CI-enforced minimum quality.
- Costs accepted: manual discipline for keeping docs synchronized with code changes.
- Risks introduced: markdown drift and duplicated/fragmented guidance if validation rules stay too coarse.

## Consequences

- Positive outcomes:
  - Architecture docs remain colocated with source code and CI workflows.
  - ADRs become the expected mechanism for major architecture changes.
  - Automated validation catches missing files/diagrams and basic regressions.
- Negative outcomes:
  - Some quality issues (semantic drift, stale examples, duplicate TOCs) are not caught by current checks.
- Mitigations:
  - Expand validation/lint checks incrementally.
  - Perform quarterly architecture documentation review.
  - Require architecture-impact PRs to reference updated docs/ADRs.

## Revisit Trigger

Revisit this ADR when any of the following occurs:

- architecture docs exceed maintainable review volume for Markdown-based workflows,
- diagram complexity requires stronger model consistency guarantees,
- onboarding/review feedback repeatedly identifies documentation discoverability issues,
- or the team adopts a broader platform engineering standard requiring centralized architecture tooling.

