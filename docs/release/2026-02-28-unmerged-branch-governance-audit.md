# Unmerged Branch Governance Audit (2026-02-28)

## Snapshot

- Audit date: 2026-02-28
- Base: `origin/main` at merge commit `d9b52db2ce02baf0a1ebe3afe51c7e17c844a664`
- Remaining unmerged remote branches: 4 (`origin/archive/*` only)
- PR linkage check: no PRs for any remaining archive branch

## Branch Findings

| Branch | Unique Commits vs `origin/main` | PR | Disposition | Notes |
|---|---:|---|---|---|
| `origin/archive/archive-dirty-root-reconcile-v4-20260224-170035-20260224-195431` | 1 | none | archive-only | Snapshot commit includes regressive deletions/conflicts around conformance workflows/docs. |
| `origin/archive/archive-ralph-canada-hardening-next-loop-20260224-20260224-195431` | 15 | none | archive-only (partial recovery applied) | Most intents already superseded on main; recovered only explicit insufficient-context fallback reason contract. |
| `origin/archive/archive-reconcile-production-readiness-20260224-20260224-195431` | 6 | none | archive-only | Branch is stale/high-conflict vs main; replay risk is high for workflow/runtime regressions. |
| `origin/archive/wip-local-dirty-carryforward-20260224-20260224-195431` | 1 | none | archive-only | Mixed-scope WIP snapshot; no mandatory unsuperseded fix identified. |

## Recovery Applied

Surgical delta integrated into current architecture:

- Added `"insufficient_context"` to chat fallback reason contract.
- Applied when constrained safe answer is returned because no validated grounded citations exist.
- Updated API/service tests to assert the explicit reason in constrained no-grounding scenarios.

Files:
- `src/immcad_api/schemas.py`
- `src/immcad_api/services/chat_service.py`
- `tests/test_chat_service.py`
- `tests/test_api_scaffold.py`

## No-Loss Preservation

Immutable patch-series backups generated for every archive branch delta:

- `backups/branch-safety/20260228-branch-archive-audit/`
- `backups/branch-safety/20260228-branch-archive-audit/manifest.tsv`

This preserves full per-commit recoverability without merging stale archive branches.

## Verification Constraints

This session environment does not provide `uv` or `pytest` binaries, so local test execution was not possible here. Validation should run via CI or a provisioned dev environment before final promotion.
