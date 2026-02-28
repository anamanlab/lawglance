# Federal RSS Audit Implementation Plan

I'm using the writing-plans skill to create the implementation plan.

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Audit the federal/federal appeals RSS ingestion flow, gating, and documentation so the MVP knows exactly what works, what gaps exist, and what actions are needed.

**Architecture:** Inspect the existing `src/immcad_api/sources`, `policy`, `records`, and prompt configuration modules to trace the RSS ingestion path from source registration through policy enforcement and any UI exposure. Capture discoveries in a dedicated audit doc and ensure future work has runbooks and references. 

**Tech Stack:** Python 3.11 modules under `src/immcad_api`, Streamlit front-end (`app.py`), Markdown docs.

---

### Task 1: Locate federal RSS keywords

**Files:**
- Modify: None (observation only)

**Step 1:** Run `rg -n "federal" src/immcad_api -g"*.py"` and `rg -n "rss" src/immcad_api -g"*.py"` to list files that mention RSS or federal courts, capturing the context for federal/federal-appeals terms.
**Expected:** `rg` outputs file paths and lines, including retroactive keywords like `Federal RSS`, `Federal Court of Appeals`, or similar, so we know where ingestion logic sits.

**Step 2:** Save the list of relevant files and snippets in a temporary note to refer back to while reading ingestion code.

### Task 2: Trace ingestion flow for each relevant file

**Files:**
- Modify: None (research only)

**Step 1:** Sequentially open the identified files (likely within `src/immcad_api/sources`, `policy`, `records`, `config/prompts.yaml`, etc.) and document what watchers/feeds exist, how they are stored, what metadata is included, and how policy gates apply to them.
**Step 2:** Note how the Streamlit UI (`app.py` or related submodules) surfaces these RSS origins or any front-end toggles.
**Output:** A structured understanding of ingestion source registration, scheduled fetch processing, metadata storage (Chroma or records), policy gating, and UI ties.

### Task 3: Document the audit

**Files:**
- Create/Modify: `docs/audits/2026-02-27-legal-rss.md`

**Step 1:** Draft sections covering: what works (source coverage and policy enforcement), gaps (missing feeds, policy misalignment, missing front-end hooks), and actionable recommendations (who to contact, what settings to adjust, what code/ docs to fix).
**Step 2:** Ensure the audit references exact file paths discovered earlier and uses concrete examples.

### Task 4: Verify and record the state

**Files:**
- Modify: None (status capture)

**Step 1:** Run `rg` again if needed for quick verification and `git status -sb` to confirm new files.
**Step 2:** Summarize intended checks in the audit doc for transparency.

### Task 5: Commit the documentation

**Files:**
- Modify: `docs/audits/2026-02-27-legal-rss.md`, optionally `docs/plans/2026-02-27-rss-audit-plan.md`

**Step 1:** Stage the audit doc.
**Step 2:** Commit with `git commit -m "docs(audit): add rc court rss catalog"` once docs reflect the findings.

---

Plan complete and saved to `docs/plans/2026-02-27-rss-audit-plan.md`. Two execution options:

1. Subagent-Driven (this session) - I dispatch fresh subagents per task, review between tasks, fast iteration.
2. Parallel Session (separate) - Open new session with executing-plans, batch execution with checkpoints.

Which approach?
