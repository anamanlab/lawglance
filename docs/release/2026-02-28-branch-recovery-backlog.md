# Branch Recovery Backlog (Selective Cherry-Pick)

This backlog tracks unmerged branch commits that are not patch-equivalent to `main` and may warrant selective recovery.

Guidelines:
- Never merge archive/WIP branches directly.
- Recover only focused commits onto fresh branches from `main`.
- Run targeted tests per recovered commit scope before opening a PR.

## Recovery Trial Notes
- Trialed first recovery path on `recovery/us007-domain-leak-scanner` from `origin/main`.
- Attempted cherry-pick of `ad7a90412eef5b88942127e24ba0d82a1785d3eb`.
- Result: conflict on add/add and content overlap in:
  - `scripts/scan_domain_leaks.py`
  - `tests/test_domain_leak_scanner.py`
  - `scripts/ralph/progress.txt`
- Interpretation: this work is likely already partially integrated on `main` with drift; use semantic diff review instead of direct cherry-pick replay.

## Replay Viability Summary (2026-02-28)
- Method: `git cherry-pick --no-commit` on temp branches from `origin/main`.
- `backup-stash-us007`: non-equivalent commits conflict on scanner/progress overlap; no clean replay.
- `fix-case-law-conformance-live-endpoint-compat`: most commits conflict; `21bd52e` is now effectively integrated (empty replay on current main), `7052b78` is docs-only and replayable.
- `archive-reconcile-production-readiness`: all tested non-equivalent commits conflict.
- `archive-feature-api-scaffold`: all tested non-equivalent commits conflict (branch later deleted after merged-lineage verification).
- Large `archive-ralph-*` candidates: all tested candidates conflict, usually on workflow files and `scripts/ralph/*` metadata (phase2/prod-readiness refs later deleted after merged-lineage verification).

### Immediate Recovery Priority
1. Do manual semantic recovery (no raw cherry-pick replay) for selected `archive-reconcile-production-readiness` workflow/docs-tooling deltas.
2. Keep `archive/archive-dirty-root-reconcile-v4-*` and `archive/wip-local-dirty-carryforward-*` as history-only snapshots unless concrete recovery requirements emerge.
3. Treat `archive/archive-ralph-canada-hardening-next-loop-*` as reference-only source; recover narrowly scoped deltas in dedicated PRs only when justified.

## Closed Recovery Items
- `feat/chat-thinking-transparency`
  - Merged via PR #37 at commit `d9b52db2ce02baf0a1ebe3afe51c7e17c844a664`.
  - Remote feature branch deleted after successful merge/checks.
- `prep/gate-fix-only-source-of-truth`
  - Merged via PR #36 and deleted from remote.
- `archive/backup-stash-us007-grounding-wip-20260224-195431`
  - `ad7a904` and `52c4fa1` were semantically verified as integrated on `main`.
  - Branch deleted from remote after backup + open-PR check.
- `archive/archive-feature-api-scaffold-20260224-20260224-195431`
  - Mapped to merged PR #1 lineage.
  - Branch deleted from remote after backup + open-PR check.
- `archive/archive-ralph-phase2-frontend-authoritative-runtime-20260224-20260224-195431`
  - Head lineage mapped to merged PR #9.
  - Branch deleted from remote after backup + open-PR check.
- `archive/archive-ralph-prod-readiness-canlii-legal-research-20260224-20260224-195431`
  - Head lineage mapped to merged PR #9 context.
  - Branch deleted from remote after backup + open-PR check.

## Candidate Commits by Branch

### archive/archive-feature-api-scaffold-20260224-20260224-195431

- Divergence: ahead `3`, behind `126`
- Non-equivalent commits (from `git cherry -v`):
  - `f66a2907b50ff9efcfb8226d9b45074a6aa70775` (72 files): feat(api): scaffold immcad service and architecture docs
  - `ee7dd8b35db79d5de5af39dc1599a9d6a4f42ecf` (3 files): fix(api): tighten openai retry handling and stabilize canlii tests
  - `e40b99762ec62298ac90076f9d317e41d3f20284` (43 files): chore: enforce quality gates and execute canada-readiness hardening

### archive/archive-ralph-canada-hardening-next-loop-20260224-20260224-195431

- Divergence: ahead `15`, behind `118`
- Non-equivalent commits (from `git cherry -v`):
  - `4060a6bd4c64b9593229acdae7793814c2e67505` (5 files): feat: [US-001] - [Add domain-leak scanner for Canada scope]
  - `a42ee75ed359de7d288760c148f78bf70f957989` (4 files): feat: [US-002] - [Wire domain-leak scanner into quality gates]
  - `8821081b30fefa696e8d6592a97cb4a8f285dc8f` (5 files): feat: [US-003] - [Add audit log events for policy blocks and provider failures]
  - `5797052f24642881a754cc96820b8d93f1647581` (3 files): feat: [US-004] - [Add ingestion checkpoint recovery runbook]
  - `c1e26697e8ea7beeeeb802693bca884e961b4fdf` (5 files): feat: [US-005] - [Add release artifact verification checklist step]
  - `e7d975b72074c17f08bc2e35055d2cce8b7095e8` (2 files): chore(ralph): update prd backlog and progress log
  - `a9e8ccdcb2929342d5bea731d83cbb0c3b549e50` (2 files): feat: US-001 - Add domain-leak scanner for Canada scope
  - `aac14bcbb8aab25bb3c61b91483afb2bf4677578` (5 files): feat: [US-002] - Add release config safety validator for production flags
  - `0a5376699465d39419a9dbddff54f568320d6bca` (4 files): feat: [US-003] - Add retrieved document schema and citation mapping helper
  - `c8f69348015803f00505406639d1fdb5551f1734` (9 files): feat: [US-004] - Introduce chat retriever interface and grounding settings
  - `210c16bf702ea5b5bed7293efd777b764f8e21eb` (8 files): feat: US-005 - Extend provider/router interfaces for grounding context
  - `be645df7b9456c6723f762a1eba62db859129e2c` (4 files): feat: [US-006] - [Implement Chroma-based Canada retriever adapter]
  - `82172e2acac5fd278fb12a3607381eb5ef6b0ea6` (4 files): feat: [US-007] - [Wire chat service to retrieval grounding and citation mapping]
  - `2e99a0395bfa5e3c4f3fb84e90061c9d5feb7f2d` (6 files): feat: [US-008] - [Add insufficient-context behavior for chat grounding failures]
  - `cb43f2a6fe3d8aff2d0b26f8bd048472721e2813` (14 files): feat: enhance Canada jurisdiction hardening, update chat and doc maintenance scripts

### archive/archive-ralph-phase2-frontend-authoritative-runtime-20260224-20260224-195431

- Divergence: ahead `34`, behind `118`
- Non-equivalent commits (from `git cherry -v`):
  - `ad7a90412eef5b88942127e24ba0d82a1785d3eb` (4 files): feat: [US-001] - Add domain-leak scanner for Canada scope
  - `52c4fa1aa90af11b49ad7bb834f50601ee060038` (6 files): feat: [US-002] - Wire domain-leak scanner into quality gates
  - `3ef790c8094896242dd791c5966ba57f681119a2` (5 files): feat: [US-003] - [Add audit log events for policy blocks and provider failures]
  - `b9b5cb1ce52215cfe776507cc92e973e32f5e2ca` (3 files): feat: [US-004] - [Add ingestion checkpoint recovery runbook]
  - `3175907e02602e201694b204590a58ab923d3543` (5 files): chore(ralph): harden codex setup and preflight
  - `207c328b7056f8d91d0c0a85b4036322d2795bd2` (5 files): feat: [US-005] - [Add release artifact verification checklist step]
  - `0f3dc93e56bfddbf70312ce7354ea16af0ce3c57` (2 files): chore: reset ralph backlog for production-readiness v1
  - `b4c6f7298068980fc7bb4e3e2ae6c528c74fe0c2` (3 files): feat: [US-001] - [Complete required Canada legal source registry]
  - `6b21010dba14b24a204b4f6518ce70e44383ecf2` (8 files): feat: [US-002] - [Enforce strict source-registry validation]
  - `3e5b7443e929ca45b6801f114e3962da3d98a6d8` (8 files): feat: [US-003] - [Disable synthetic CanLII case output in production]
  - `9d9ec1efa8a3837a801ce1e971bf44f919cb208f` (7 files): feat: US-004 - Harden policy refusal coverage
  - `d0236d841720f291ebd7e33e0222f294d0ee8d92` (9 files): feat: [US-005] - [Enforce no synthetic citations in production]
  - `91771115d338a2ca03fe024904f4990edc2c2c8a` (5 files): feat: [US-006] - [Lock provider routing contract]
  - `5cb0e0fbcbb68adb2c55193ac002587588e58804` (4 files): feat: [US-007] - [Strengthen API security baseline enforcement]
  - `028236b4a0607db17446e46dd2b3843f2c7df505` (3 files): feat: [US-008] - [Add PII-minimizing audit logging guarantees]
  - `22b0280f11f661e77f59a18f263eb4fcf61cee1f` (6 files): feat: [US-009] - [Enforce legal release checklist sign-off]
  - `edd4ca94c5865d0d5597b105a9668322bded169b` (12 files): feat: [US-010] - [Create production observability baseline]
  - `c5f842bb44bd9955a8ba68c82298b09aedbb516e` (4 files): feat: US-011 - Define backup and recovery operational targets
  - `96dd6d2dde370673e53d3567d6714edd8de7ec45` (4 files): feat: [US-012] - [Scaffold Next.js minimal chat UI plan and integration contract]
  - `b12fefb74efc6ae3b64d8c2afdce88e3be1b6451` (2 files): chore: reset ralph backlog for phase2 frontend + authoritative runtime
  - `1205524fe467b98505ab2c1534f2f72ba8201f70` (4 files): feat: [US-001] - [Correct authoritative legal source links]
  - `6c14a540ca96dc0f783c7e54b389e9e7d6087500` (8 files): feat: [US-002] - Disable synthetic CanLII fallback in production
  - `28a20fd285006d3ea61d65f76eef286acc97ff71` (4 files): feat: [US-003] - [Enforce no synthetic citations in production]
  - `eaaf09f949de9fd8976a2cccd9c0d1601e7f98ab` (8 files): feat: [US-004] - Implement grounded citation adapter contract
  - `952e88dc027eaf96130bec4d06f679262328379e` (5 files): feat: [US-005] - [Expand policy refusal coverage]
  - `9c2bd0a979dde2a332e33a7c69a065e50cd613e6` (21 files): feat: [US-006] - [Scaffold Next.js and Tailwind frontend]
  - `6913126081d483cd42ae162c4b3f2de8252c55fb` (8 files): feat: [US-007] - [Implement frontend API integration with trace IDs]
  - `616ac87d6792d6dc1fa76a2066d7959b2900379b` (3 files): feat: [US-008] - [Render citation chips and refusal/error UX states]
  - `629551d79f5eceb0f99d74bdc960cd9ba25ac4ad` (9 files): feat: [US-009] - [Add frontend quality and contract tests]
  - `8a20f628de2024f7ad572dbc5692aa52221665bf` (8 files): feat: [US-010] - [Add frontend CI and release evidence integration]
  - `546bc695bf83804b6a951d7ce7ea7ad1e0e2eefe` (10 files): feat: US-011 - Mark Streamlit as legacy and update docs
  - `c693c83aeb8704ae99e76e6b42c61673e7b2d4d0` (1 files): feat: US-011 - Mark Streamlit as legacy and update docs
  - `3d55d7c2d3e3a36198d775a60861f92b875b51ea` (9 files): feat: [US-012] - Add staging end-to-end smoke workflow
  - `31df86e2d6072b5e6852e4134fc264f1c6a347ea` (1 files): fix(ci): set PYTHONPATH for hardened runtime safety check

### archive/archive-reconcile-production-readiness-20260224-20260224-195431

- Divergence: ahead `6`, behind `102`
- Non-equivalent commits (from `git cherry -v`):
  - `ff377e469b68b8359e31437da9fe7300d4718bff` (31 files): feat(runtime): enforce source policy and export gate contracts
  - `44f031afba318cad1c1bc6fd993a38e4bac1acf6` (15 files): feat(ci): harden quality gates and ops alert workflows
  - `ffd273a7d7c160ea51b787e0d07833720ef73fd7` (9 files): fix(docs-tooling): harden markdown maintenance and validation
  - `bbb14267821571f9288689418494cc4dfd719bce` (17 files): feat(legacy): migrate local-rag runtime into archived package
  - `7a24b6caeaa081d412a1e9946debb0411bec3f19` (22 files): docs(architecture): align arc42, ADRs, and readiness plans
  - `4e1a506744265110e5a10c8d023a79355b66c04f` (12 files): chore(repo): sync env templates and reconciliation task records

### archive/backup-stash-us007-grounding-wip-20260224-195431

- Divergence: ahead `5`, behind `118`
- Non-equivalent commits (from `git cherry -v`):
  - `ad7a90412eef5b88942127e24ba0d82a1785d3eb` (4 files): feat: [US-001] - Add domain-leak scanner for Canada scope
  - `52c4fa1aa90af11b49ad7bb834f50601ee060038` (6 files): feat: [US-002] - Wire domain-leak scanner into quality gates
  - `4ed5b4521615338018216bd5a19b93613cfe2978` (2 files): untracked files on ralph/prod-readiness-canlii-legal-research: 52c4fa1 feat: [US-002] - Wire domain-leak scanner into quality gates
  - `4e4eecdbd8f4e43bea7c79ad80a5a5581fc3086d` (0 files): index on ralph/prod-readiness-canlii-legal-research: 52c4fa1 feat: [US-002] - Wire domain-leak scanner into quality gates

### archive/fix-case-law-conformance-live-endpoint-compat-20260224-195431

- Divergence: ahead `7`, behind `47`
- Non-equivalent commits (from `git cherry -v`):
  - `5e0d9c90c1eb5010a9e6f1ac1f08fe3267c584d8` (9 files): fix(settings): enforce hardened env requirements for production deploys
  - `f37c66141cd15cfbdd90d57ecd959dea2cf4aa6c` (9 files): feat(settings): allow gemini-only mvp with case search toggle
  - `8dcd5961dbef6be6cd80b56e5e2e3ac84446145e` (3 files): fix(ingestion): honor CLI timeout override over fetch policy
  - `8388b91cbcc2dfb44fe81ccf8c3618822c791120` (15 files): feat(case-law): harden FCA/SCC ingestion and fetch policy controls
  - `7052b78c20b09857d3e8a0a273af017e9653f8ad` (1 files): docs(agents): add current execution priorities
  - `fa080512c0274168eaf68e8e57e09281b02799e9` (2 files): fix(provider): use millisecond timeout for gemini sdk
  - `21bd52ed0e7126bc09e1e575fad876655fb3f755` (1 files): fix(backend-vercel): sync gemini timeout millis conversion

## Recommended Recovery Order
1. `archive/archive-reconcile-production-readiness-20260224-20260224-195431`
2. `archive/archive-ralph-canada-hardening-next-loop-20260224-20260224-195431`
3. `archive/archive-dirty-root-reconcile-v4-20260224-170035-20260224-195431`
4. `archive/wip-local-dirty-carryforward-20260224-20260224-195431`

Rationale: merged-lineage archive branches were already deleted after backup; remaining entries are selective-recovery candidates or history-only snapshots.
