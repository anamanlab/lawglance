# Legal RSS Audit Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Audit the existing federal, federal appeal, and superior court RSS/ingestion flows, document front-end exposure, data storage, and outstanding gaps so we can finalize the MVP.

**Architecture:** Review the Python/RAG service layers handling court RSS ingestion (including the new FCA HTML fallback warning), trace how the Streamlit UI surfaces the data, and capture how the agent consumes those sources within the runtime prompt stack.

**Tech Stack:** Python 3.11, Streamlit (`app.py`), `src/immcad_api` APIs, Chroma DB locally stored in `chroma_db_legal_bot_part1`, and existing config/prompts modules.

---

### Task 1: Catalog federal/federal appeal RSS integration

**Files:**
- Inspect: `src/immcad_api/sources/source_registry_embedded.py`, `src/immcad_api/sources/canada_courts`, `src/immcad_api/policy/source_policy_embedded.py`
- Inspect: `src/immcad_api/records/` and `config/prompts.yaml`

**Step 1:** Search for RSS-related constants/identifiers (e.g., "RSS", "federal court", "FCA") using `rg` and capture file paths for the pipeline.
**Step 2:** Read each located file to describe how RSS feeds are ingested, how records get stored or indexed, and how policy gates apply.
**Step 3:** Note anything missing or flagged (e.g., no front-end endpoint, misconfigured policy) and log in the audit summary.
**Step 4:** Save findings as bullet items in `docs/audits/2026-02-27-legal-rss.md` (create file if needed).
**Step 5:** Commit these documentation changes with message `docs(audit): add rc court rss catalog`.

### Task 2: Map superior court integration and UI exposure

**Files:**
- Inspect: `app.py`, `src/immcad_api/agents`, `frontend-web` components.
- Inspect: `docs/` and `README.md` for user-facing descriptions.

**Step 1:** Trace how superior court data flows from backend (source/policy) to UI (Streamlit/Front-end), noting components that expose source selection or summaries.
**Step 2:** Identify whether this data is persisted (check Chroma directory and any storage wrappers) and how the agent uses it in prompts.
**Step 3:** List features available to the user (via UI or logs), and clarify in audit notes whether this satisfies MVP requirements.
**Step 4:** Document gaps or potential improvements in the same audit file.
**Step 5:** Commit updates referencing this scope with `docs(audit): update superior court coverage`.

### Task 3: Synthesize recommendations and next steps

**Files:**
- Create/Modify: `docs/audits/2026-02-27-legal-rss.md`

**Step 1:** Review gathered notes and distill what is working, what is missing, and what needs prioritization for SCC/SCC/FC.
**Step 2:** Translate findings into actionable recommendations for ingestion, policy gating, UI visibility, and storage.
**Step 3:** Highlight verification steps (e.g., tests or manual checks) for each recommendation.
**Step 4:** Update `tasks/todo.md` with a short plan referencing the audit.
**Step 5:** Commit final recommendations with message `docs(audit): add next steps for legal rss mvp`.
