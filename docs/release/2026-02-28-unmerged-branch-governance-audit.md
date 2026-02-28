# Unmerged Branch Governance Audit (2026-02-28)

## Scope
Audit target: all remote branches not merged into `origin/main` at audit time.

- Total unmerged remote branches (initial snapshot): `21`
- Total unmerged local branches: `0`
- Open PR among unmerged branches (current): `0`

## No-Loss Safeguards
Before any cleanup decision:

- Backup bundle created: `backups/branch-safety/unmerged-branches-2026-02-28.bundle`
- Ref/sha manifest created: `backups/branch-safety/unmerged-branches-2026-02-28.manifest.tsv`
- Bundle verification log: `backups/branch-safety/unmerged-branches-2026-02-28.bundle.verify.txt`
- Latest backup snapshot:
  - `backups/branch-safety/unmerged-branches-20260228-152342.bundle`
  - `backups/branch-safety/unmerged-branches-20260228-152342.manifest.tsv`
  - `backups/branch-safety/unmerged-branches-20260228-152342.bundle.verify.txt`
  - `backups/branch-safety/unmerged-branches-20260228-161653.bundle`
  - `backups/branch-safety/unmerged-branches-20260228-161653.manifest.tsv`
  - `backups/branch-safety/unmerged-branches-20260228-161653.bundle.verify.txt`

## Decision Matrix
Legend:

- `delete-after-backup`: safe to remove remote branch once approved; content is archival-only or already integrated.
- `keep-archive`: preserve branch for history; do not merge as-is.
- `cherry-pick`: recover specific commits into fresh branches from `main`.
- `defer-merge`: active candidate blocked pending cleanup and verification.

| Branch | Status | Decision | Evidence Summary |
|---|---|---|---|
| `archive/archive-dirty-root-reconcile-v4-20260224-170035-20260224-195431` | ahead `1`, behind `63` | `keep-archive` | Single archive snapshot commit with unresolved deltas; mixed workflow/test/code scope. |
| `archive/archive-export-policy-gate-20260224-170035-20260224-195431` | ahead `1`, behind `101` | `delete-after-backup` | Archive snapshot for local untracked/docs tasks, no production runtime value. |
| `archive/archive-feature-api-scaffold-20260224-20260224-195431` | ahead `3`, behind `127` | `deleted-after-backup` | Mapped to merged PR #1 lineage; no open PR dependency; deleted in cleanup batch 4. |
| `archive/archive-feature-canada-readiness-foundation-20260224-20260224-195431` | ahead `1`, behind `125` | `delete-after-backup` | `git cherry` marks equivalent patch already in `main`. |
| `archive/archive-feature-jurisdictional-suite-gates-20260224-20260224-195431` | ahead `1`, behind `121` | `delete-after-backup` | `git cherry` marks equivalent patch already in `main`. |
| `archive/archive-feature-ralph-integration-20260224-20260224-195431` | ahead `1`, behind `119` | `delete-after-backup` | `git cherry` marks equivalent patch already in `main`. |
| `archive/archive-feature-release-gates-jurisdiction-checks-20260224-20260224-195431` | ahead `1`, behind `120` | `delete-after-backup` | `git cherry` marks equivalent patch already in `main`. |
| `archive/archive-feature-runtime-hardening-pr4-20260224-20260224-195431` | ahead `1`, behind `123` | `delete-after-backup` | `git cherry` marks equivalent patch already in `main`. |
| `archive/archive-feature-source-registry-loader-20260224-20260224-195431` | ahead `2`, behind `124` | `delete-after-backup` | Feature intent appears superseded by merged mainline source-registry loader work. |
| `archive/archive-legacy-archive-migration-20260224-170035-20260224-195431` | ahead `1`, behind `89` | `delete-after-backup` | Archive snapshot commit patch-equivalent to `main`. |
| `archive/archive-ralph-canada-hardening-next-loop-20260224-20260224-195431` | ahead `15`, behind `118` | `keep-archive` | Large stale branch; selective commit mining only. |
| `archive/archive-ralph-phase2-frontend-authoritative-runtime-20260224-20260224-195431` | ahead `34`, behind `119` | `deleted-after-backup` | Head SHA mapped to merged PR #9 lineage; no open PR dependency; deleted in cleanup batch 4. |
| `archive/archive-ralph-prod-readiness-canlii-legal-research-20260224-20260224-195431` | ahead `20`, behind `119` | `deleted-after-backup` | Head lineage maps to merged PR #9 context; no open PR dependency; deleted in cleanup batch 4. |
| `archive/archive-reconcile-production-readiness-20260224-20260224-195431` | ahead `6`, behind `102` | `keep-archive` | Large cross-cutting stale branch; selective porting only. |
| `archive/backup-stash-case-law-conformance-plan-20260224-195431` | ahead `3`, behind `102` | `delete-after-backup` | Stash metadata commits; no clean tracked delta to merge. |
| `archive/backup-stash-us007-grounding-wip-20260224-195431` | ahead `5`, behind `118` | `deleted-after-backup` | Semantic review confirmed intended behaviors are integrated on `main`; branch deleted in cleanup batch 2. |
| `archive/feat-frontend-shell-redesign-rollout-20260224-20260224-195431` | ahead `1`, behind `49` | `delete-after-backup` | `git cherry` marks equivalent patch already in `main`. |
| `archive/fix-case-law-conformance-live-endpoint-compat-20260224-195431` | ahead `7`, behind `47` | `deleted-after-backup` | Semantic gap review found behavior integrated or intentionally evolved on `main`; stale branch removed in cleanup batch 3. |
| `archive/fix-release-gates-pythonpath-toggle-step-20260224-195431` | ahead `1`, behind `48` | `delete-after-backup` | `git cherry` marks equivalent patch already in `main`. |
| `archive/wip-local-dirty-carryforward-20260224-20260224-195431` | ahead `1`, behind `52` | `keep-archive` | Explicit WIP snapshot; not merge-ready. |
| `feat/chat-thinking-transparency` | merged | `merged-and-deleted` | PR #37 merged to `main` at commit `d9b52db` (`2026-02-28T16:15:40Z`); remote branch deleted afterward. |

## PR 34 Readiness Result
PR link: `https://github.com/anamanlab/lawglance/pull/34`

- PR head SHA: `304dc131b624289d3fccc69eeba203af3f8b7ebb`
- `origin/feat/chat-thinking-transparency` SHA: `89a5db07a138a70023fc2658ddaba5f9bc02847d`
- Delta from origin branch to PR head: `2` commits

Blocking finding:

- PR head includes `304dc13 chore: checkpoint pending workspace changes` (wide mixed-scope checkpoint commit across workflows/backend/frontend/docs/tests).
- Governance decision: do not merge PR #34 as-is.
- Final disposition: PR #34 closed as superseded by repo-owned PR #36 (gate fix) and PR #37 (chat transparency lineage).

## Execution Log (2026-02-28)
- Created sanitized branch from `origin/feat/chat-thinking-transparency`:
  - `prep/pr34-sanitized-gate-fix`
  - Includes only gate fix commit (`40dcaba`) from PR #34 delta.
- Opened draft sanitized PR (later superseded):
  - `https://github.com/anamanlab/lawglance/pull/35`
- Posted governance comment on PR #34 linking sanitized path.
- Opened canonical main-based isolated gate PR:
  - `https://github.com/anamanlab/lawglance/pull/36` (`prep/gate-fix-only-source-of-truth`)
- Closed PR #35 as superseded by #36 and deleted remote branch `prep/pr34-sanitized-gate-fix`.
- Merged PR #36 (squash) and deleted merged branch `prep/gate-fix-only-source-of-truth`.
- Opened canonical repo-owned chat transparency PR:
  - `https://github.com/anamanlab/lawglance/pull/37` (`feat/chat-thinking-transparency`)
- Closed fork PR #34 as superseded by #36 + #37.

### Remote Cleanup Batch Completed
After backup + dry-run + open-PR dependency check, deleted these remote branches:

- `archive/archive-export-policy-gate-20260224-170035-20260224-195431`
- `archive/archive-feature-canada-readiness-foundation-20260224-20260224-195431`
- `archive/archive-feature-jurisdictional-suite-gates-20260224-20260224-195431`
- `archive/archive-feature-ralph-integration-20260224-20260224-195431`
- `archive/archive-feature-release-gates-jurisdiction-checks-20260224-20260224-195431`
- `archive/archive-feature-runtime-hardening-pr4-20260224-20260224-195431`
- `archive/archive-feature-source-registry-loader-20260224-20260224-195431`
- `archive/archive-legacy-archive-migration-20260224-170035-20260224-195431`
- `archive/backup-stash-case-law-conformance-plan-20260224-195431`
- `archive/feat-frontend-shell-redesign-rollout-20260224-20260224-195431`
- `archive/fix-release-gates-pythonpath-toggle-step-20260224-195431`

### Remote Cleanup Batch 2 (Semantic-Integrated Stash Branch)
- After semantic verification that both non-equivalent commits (`ad7a904`, `52c4fa1`) are behaviorally integrated on `main`, deleted:
  - `archive/backup-stash-us007-grounding-wip-20260224-195431`

### Remote Cleanup Batch 3 (Semantically Superseded Fix Branch)
- After commit-level semantic review (`integrated` / `partially integrated with intentional evolution`) and no open PR dependency, deleted:
  - `archive/fix-case-law-conformance-live-endpoint-compat-20260224-195431`

### Remote Cleanup Batch 4 (Merged-Lineage Archive Branches)
- After fresh backup snapshot + dry-run + open-PR checks, deleted:
  - `archive/archive-feature-api-scaffold-20260224-20260224-195431`
  - `archive/archive-ralph-phase2-frontend-authoritative-runtime-20260224-20260224-195431`
  - `archive/archive-ralph-prod-readiness-canlii-legal-research-20260224-20260224-195431`
- Additional active-branch hardening:
  - Pushed remediation commit to `feat/chat-thinking-transparency`: `d2f2adf`.
  - Requested branch update from `main`; PR #37 head is now `00ff607` (currently `mergeable_state=unstable`, pending final review pass).

### Merge Completion and Final Hygiene
- PR #37 (`feat/chat-thinking-transparency`) merged into `main` via merge commit:
  - `d9b52db2ce02baf0a1ebe3afe51c7e17c844a664`
- Post-merge remote cleanup completed:
  - Deleted `origin/feat/chat-thinking-transparency`

### Remaining Unmerged Remote Branches
- `origin/archive/archive-dirty-root-reconcile-v4-20260224-170035-20260224-195431`
- `origin/archive/archive-ralph-canada-hardening-next-loop-20260224-20260224-195431`
- `origin/archive/archive-reconcile-production-readiness-20260224-20260224-195431`
- `origin/archive/wip-local-dirty-carryforward-20260224-20260224-195431`

## Next Steps
1. Execute manual semantic recovery for remaining `keep-archive` branches in small focused PRs.
2. Re-run branch cleanup gate for any archive branches confirmed fully integrated after semantic review.
3. Keep quarterly backup/bundle snapshots for the four remaining archive branches until recovery disposition is final.
