# Unmerged Branch and PR Triage Implementation Plan

## Execution Status (2026-02-28)
- Executed.
- PR #37 (`feat/chat-thinking-transparency`) was fully remediated, passed all required checks, merged into `main`, and the remote feature branch was deleted.
- Remaining unmerged remote branches are archive-only:
  - `origin/archive/archive-dirty-root-reconcile-v4-20260224-170035-20260224-195431`
  - `origin/archive/archive-ralph-canada-hardening-next-loop-20260224-20260224-195431`
  - `origin/archive/archive-reconcile-production-readiness-20260224-20260224-195431`
  - `origin/archive/wip-local-dirty-carryforward-20260224-20260224-195431`

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Decide which unmerged branches should be merged to `main`, execute the right merge action for active work, and close/archive stale branches safely.

**Architecture:** Use a three-gate process: inventory gate (branch/PR mapping), risk gate (intent + divergence + CI state), and execution gate (merge or archive action). Treat archival branches as immutable history unless an explicit recovery request exists.

**Tech Stack:** Git (`git`, `rev-list`, `branch`, `show`), GitHub API/PR metadata, local test commands (`make`, `uv`, `npm` as needed).

---

### Task 1: Build authoritative branch/PR inventory

**Files:**
- Modify: `tasks/todo.md`
- Output artifact: `docs/plans/2026-02-28-unmerged-branches-pr-triage.md`

**Step 1: Enumerate unmerged branches**

Run:
```bash
git fetch --prune origin
git branch -r --no-merged origin/main --format='%(refname:short)' \
  | sed '/^origin\/HEAD$/d;/^origin\/main$/d'
```

Expected: list of all remote branches currently not merged into `origin/main`.

**Step 2: Map each branch name to PR state**

Run:
```bash
# For each branch short name, query PRs by head ref and capture latest state/URL.
```

Expected: each branch classified as `NO_PR`, `OPEN_PR`, or `CLOSED_PR`.

**Step 3: Record results in task tracker**

Run:
```bash
# Update tasks/todo.md with inventory totals and mappings.
```

Expected: reproducible inventory section with branch count and PR linkage.

**Step 4: Commit**

```bash
git add tasks/todo.md docs/plans/2026-02-28-unmerged-branches-pr-triage.md
git commit -m "docs(plan): add unmerged branch and PR triage workflow"
```

---

### Task 2: Classify merge intent and risk

**Files:**
- Modify: `tasks/todo.md`

**Step 1: Compute divergence and tip intent**

Run:
```bash
# For each unmerged branch, capture ahead/behind against origin/main and tip subject.
```

Expected: table with `ahead`, `behind`, `tip_sha`, `tip_subject`.

**Step 2: Apply classification rules**

Run:
```bash
# Classify by name and tip intent:
# - archive/*, backup*, wip* => archival, no-merge by default
# - feature/fix branch with active PR => merge candidate
```

Expected: every branch tagged `ARCHIVAL`, `CANDIDATE`, or `INVESTIGATE`.

**Step 3: Gate decision**

Run:
```bash
# Mark merge decision per branch in tasks/todo.md.
```

Expected: explicit yes/no merge decision with reason.

**Step 4: Commit**

```bash
git add tasks/todo.md
git commit -m "docs(plan): classify unmerged branches by merge intent"
```

---

### Task 3: Resolve active candidate source-of-truth

**Files:**
- Modify: `tasks/todo.md`

**Step 1: Compare branch tip vs PR head**

Run:
```bash
git rev-parse origin/feat/chat-thinking-transparency
# compare with PR #34 head SHA from API
```

Expected: explicit statement whether branch tip matches PR tip.

**Step 2: Choose integration target**

Run:
```bash
# If SHAs differ, choose one source of truth:
# A) merge PR head via GitHub
# B) update origin branch to PR head then merge
```

Expected: one canonical merge source selected and documented.

**Step 3: Capture required checks**

Run:
```bash
# Collect PR status checks, review state, and required local verification commands.
```

Expected: readiness checklist with pass/fail for each gate.

**Step 4: Commit**

```bash
git add tasks/todo.md
git commit -m "docs(plan): define source-of-truth and readiness gates for PR 34"
```

---

### Task 4: Execute merge or defer safely

**Files:**
- Modify: `tasks/todo.md`

**Step 1: Merge path (if ready)**

Run:
```bash
# Merge PR #34 through GitHub (preferred), then fast-forward local main.
```

Expected: `main` contains the approved PR commits; post-merge sanity checks pass.

**Step 2: Defer path (if not ready)**

Run:
```bash
# Leave PR open, post blocking findings/checklist, do not merge.
```

Expected: clear blocking criteria documented.

**Step 3: Stale branch policy action**

Run:
```bash
# For archival branches: keep as archives or bulk-delete only after explicit approval.
```

Expected: branch hygiene action aligned with repository retention policy.

**Step 4: Commit final tracker update**

```bash
git add tasks/todo.md
git commit -m "docs(plan): finalize unmerged branch triage decisions"
```
