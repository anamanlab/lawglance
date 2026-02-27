# FCA Fallback Instrumentation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add visibility around the Federal Court of Appeal HTML fallback and document how the ingestion checkpoint path is shared so operators can monitor the MSS feeds.

**Architecture:** Instrument the `parse_fca_decisions_html_feed` helper so every HTML fallback invocation emits a structured warning/metric, and update the operator-facing documentation to explain how the checkpoint file is wired for ingestion, transparency, and monitoring.

**Tech Stack:** Python 3.11 runtime (`src/immcad_api/sources`), FastAPI documentation surface, Markdown docs under `docs/`.

---

### Task 1: Instrument the FCA HTML fallback

**Files:**
- Modify: `src/immcad_api/sources/canada_courts.py`

**Step 1:** Add a logger call in `parse_fca_decisions_html_feed` that warns when the HTML parser is triggered. Include enough metadata (case count, source_id) so alerting can differentiate repeated fallbacks.
**Step 2:** Ensure the log will be emitted during both ingestion jobs and live `OfficialCaseLawClient` fetches by keeping the helper pure and accessible from both entry points.
**Step 3:** Run targeted linting to confirm there are no unused imports and the log addition is formatted correctly.
**Step 4:** Run `git status` to verify only intended files changed.
**Step 5:** Commit with `chore(rss): log fca html fallback` when ready.

### Task 2: Document checkpoint wiring and fallback behavior

**Files:**
- Modify: `docs/IMMCAD_System_Overview.md`
- Modify: `docs/plans/2026-02-27-legal-rss-audit.md` (summary section)

**Step 1:** Add a subsection in `docs/IMMCAD_System_Overview.md` describing the ingestion checkpoint path (`.cache/immcad/ingestion-checkpoints.json`) and why it must be the same path wired into the Source Transparency router/Azure/Cloudflare deployments.
**Step 2:** In the audit plan `docs/plans/2026-02-27-legal-rss-audit.md`, append a short note referencing the new warning log and the checkpoint documentation so future readers know where to look for fallback events.
**Step 3:** Proofread the added text for clarity and ensure markdown formatting matches existing style.
**Step 4:** Run `git status` again to confirm docs-only changes and commit after Task 1 with `docs(rss): explain fca fallback monitoring`.
