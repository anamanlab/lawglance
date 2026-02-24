# Case-Law Conformance Runner Design

## Goal

Add a release-quality conformance runner that probes SCC/FC/FCA case-law endpoints, validates parseability and payload quality using existing court validators, and publishes a machine-readable report for CI and operations use.

## Scope

In scope:

- CLI script for live conformance checks.
- Reusable Python module for probing and evaluating conformance.
- CI workflow integration:
  - warning-only in `quality-gates`
  - strict/blocking in `release-gates`
- Tests for script behavior and CI workflow assertions.

Out of scope:

- Changing ingestion validation thresholds (user-owned feature `2`)
- Export policy gate wiring (user-owned feature `3`)
- Refactoring ingestion runtime behavior

## Constraints

- Must reuse existing parser/validator logic in `immcad_api.sources.canada_courts`.
- Must not make PR quality gates fail solely due transient/live endpoint issues (`warning-only` mode).
- Must produce deterministic test coverage without live network dependency.

## Architecture

### Components

1. `src/immcad_api/ops/case_law_conformance.py`
- Core logic for:
  - loading target sources from registry (`SCC_DECISIONS`, `FC_DECISIONS`, `FCA_DECISIONS`)
  - fetching endpoints via `httpx`
  - recording HTTP/content metadata
  - invoking `validate_court_source_payload`
  - classifying results (`pass`, `warn`, `fail`)
  - summarizing overall report

2. `scripts/run_case_law_conformance.py`
- Thin CLI wrapper:
  - parses args
  - calls core evaluator
  - writes JSON artifact
  - enforces `--strict` exit behavior

3. CI workflow steps
- `quality-gates.yml`: non-strict run + artifact upload
- `release-gates.yml`: strict run + artifact upload

### Data Flow

1. CLI starts and loads source registry.
2. Selects court source URLs.
3. HTTP fetch each endpoint.
4. If HTTP 200, run parser/validator on payload.
5. Compute source-level status:
- `pass`: parse/validation succeeds within thresholds
- `warn`: non-critical quality issues in non-strict mode
- `fail`: endpoint unavailable, invalid payload, parser error, or threshold breach
6. Emit JSON report and return exit code.

## Status Model

Per-source statuses:

- `pass`
- `warn`
- `fail`

Overall statuses:

- `pass` (all pass)
- `warn` (>=1 warn, no fail)
- `fail` (>=1 fail)

## CLI Interface (planned)

Required:

- `--output <path>`

Optional:

- `--registry <path>`
- `--timeout-seconds <float>` (default ~20s)
- `--strict` (non-zero on any `fail`)
- `--max-invalid-ratio <float>` (default conservative for live drift tolerance)
- `--min-records <int>` (default >0)

## Testing Strategy

- Unit/script tests with monkeypatched `httpx` fetch behavior.
- Cover:
  - HTTP 200 + valid payload
  - HTTP 404
  - non-parseable payload
  - parser validation invalid records
  - strict vs non-strict exit behavior
  - JSON artifact shape
- Workflow tests assert:
  - step names exist
  - quality gate uses non-strict mode
  - release gate uses `--strict`
  - artifact upload paths include conformance report

## Risks and Mitigations

- Live endpoint instability causes noise
  - Mitigation: non-strict mode in PR quality gates
- Parser strictness drift vs real payloads
  - Mitigation: configurable thresholds in conformance runner
- CI runtime delays from live calls
  - Mitigation: short timeout and only 3 sources

## Acceptance Criteria

- Script and module are added with tests.
- `quality-gates` runs conformance warning-only and uploads artifact.
- `release-gates` runs conformance strict and uploads artifact.
- Targeted tests and lint pass.
