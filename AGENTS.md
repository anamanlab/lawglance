# Repository Guidelines

## Project Structure & Module Organization
- Main app entrypoint: `app.py` (Streamlit chat UI).
- Core orchestration and RAG flow: `src/immcad_api/` (legacy local-RAG modules archived under `legacy/local_rag/`).
- Configuration and prompts: runtime prompts in `src/immcad_api/policy/prompts.py` (legacy compatibility prompt file: `config/prompts.yaml`), plus `.env`, `.env.example`.
- Data/index artifacts: `chroma_db_legal_bot_part1/` (local Chroma store).
- Docs and onboarding: `README.md`, `docs/` (see `docs/development-environment.md`).
- Task planning/lessons artifacts: `tasks/` (repo-root `tasks/todo.md` for plans/TODOs and `tasks/lessons.md` for user-correction patterns and working rules).
- Utility scripts: `scripts/setup_dev_env.sh`, `scripts/verify_dev_env.sh`.
- Experimental notebooks: `src/*.ipynb`, `examples/*.ipynb`.

## Build, Test, and Development Commands
- `make setup` — validate prerequisites and install dependencies with `uv`.
- `make verify` — check Python/tooling, imports, and local environment health.
- `make dev` — run the local app (`uv run streamlit run app.py`).
- `make lint` — run Ruff checks.
- `make format` — apply Ruff formatting.
- `make test` — run pytest (`uv run pytest -q`).

If `make` is unavailable, run the underlying commands directly from the repo root.

## Coding Style & Naming Conventions
- Python 3.11+ required (`pyproject.toml`).
- Follow `.editorconfig`: UTF-8, LF, final newline, 4-space indentation (2 spaces for YAML/JSON/TOML).
- Use Ruff for linting/formatting.
- Naming: `snake_case` for functions/files/variables, `PascalCase` for classes, `UPPER_SNAKE_CASE` for constants.
- Keep modules focused; prefer small, composable functions for retrieval, prompt, and cache logic.

## Testing Guidelines
- Framework: `pytest`.
- Place tests in `tests/` with names `test_*.py`.
- Add/extend tests for every behavior change, especially retrieval quality, prompt safety, and cache behavior.
- No enforced coverage gate currently; aim for strong coverage of touched code and failure paths.

## Commit & Pull Request Guidelines
- Existing history uses short imperative summaries and issue-linked merges (e.g., `Merge pull request #22...`, `Update ...`, `bug fixed ...`).
- Prefer: `type(scope): concise summary` (e.g., `fix(cache): handle empty Redis payload`).
- PRs should include:
  - Clear problem/solution summary
  - Linked issue or context (`#<id>`) when available
  - Test evidence (`make test`, `make lint`)
  - Screenshots/GIFs for UI changes

## Security & Configuration Tips
- Never commit secrets; use `.env` locally and keep `.env.example` as template.
- MVP provider baseline is Gemini-first (`ENABLE_OPENAI_PROVIDER=false`, `PRIMARY_PROVIDER=gemini`).
- Minimum production runtime secrets: `GEMINI_API_KEY`, `IMMCAD_API_BEARER_TOKEN` (and compatibility alias `API_BEARER_TOKEN` with same value).
- Redis is optional but recommended (`REDIS_URL=redis://localhost:6379/0`).

## Workflow Orchestration
1. Plan Mode Default
  - Enter plan mode for any non-trivial task (3+ steps or architectural decisions).
  - If something goes sideways, stop and re-plan immediately.
  - Use plan mode for verification steps, not just implementation.
  - Write detailed specs up front to reduce ambiguity.
2. Subagent Strategy
  - Use subagents liberally to keep the main context window clean.
  - Offload research, exploration, and parallel analysis to subagents.
  - For complex problems, use more parallel compute via subagents.
  - Keep one focused task per subagent.
3. Self-Improvement Loop
  - After any user correction, update `tasks/lessons.md` with the pattern.
  - Write explicit rules that prevent the same mistake.
  - Iterate on lessons until mistake rate drops.
  - Review relevant lessons at session start.
4. Verification Before Done
  - Never mark a task complete without proving it works.
  - Diff behavior between `main` and your changes when relevant.
  - Ask: "Would a staff engineer approve this?"
  - Run tests, check logs, and demonstrate correctness.
5. Demand Elegance (Balanced)
  - For non-trivial changes, ask whether there is a more elegant design.
  - If a fix feels hacky, re-implement the elegant solution with full context.
  - Skip this for simple, obvious fixes to avoid over-engineering.
  - Challenge your own work before presenting.
6. Autonomous Bug Fixing
  - For bug reports, diagnose and fix without hand-holding.
  - Use logs, errors, and failing tests as the source of truth.
  - Resolve failing CI tests proactively.

## Task Management
- Plan First: Write a plan to `tasks/todo.md` with checkable items.
- Verify Plan: Check in before starting implementation.
- Track Progress: Mark items complete as work advances.
- Explain Changes: Provide high-level summaries at each step.
- Document Results: Add a review section to `tasks/todo.md`.
- Capture Lessons: Update `tasks/lessons.md` after corrections.

## Core Principles
- Simplicity First: Keep changes as simple as possible and minimize code impact.
- No Laziness: Find root causes; no temporary fixes; maintain senior-engineer quality.
- Minimal Impact: Touch only what is necessary and avoid introducing regressions.

## Current Execution Priorities (2026-02-24)
- Objective (MVP): ship a production-safe Canada case-law pipeline and API surface with enforceable policy gates, trusted-source grounding, and deterministic CI checks.
- Phase 0 (Release Safety First): close secret/config hygiene and workflow race conditions.
  - Add/verify backup ignore rules and untracked-secret policy.
  - Ensure workflow dedup/concurrency (`quality-gates`, `release-gates`) and SHA pinning where required.
  - Exit gate: workflow-focused tests pass and no tracked secret backups remain.
- Phase 1 (Core Ingestion Correctness): finish SCC/FC/FCA parser and policy enforcement path.
  - Complete `canada_courts` parsing resilience and registry/source consistency.
  - Keep ingestion policy decisions deterministic across environments.
  - Exit gate: parser + ingestion + registry tests pass.
- Phase 2 (Runtime/API Safety): close auth, prompt, citation, and export-policy gaps.
  - Harden `/ops` auth behavior, citation trusted-domain handling, prompt input wiring, and markdown/citation sanitization.
  - Finalize export/download policy gate behavior and tests.
  - Exit gate: API scaffold/chat-service/export-policy tests pass with no prompt leakage regressions.
- Phase 3 (Tooling + Docs Alignment): stabilize Makefile/doc-maint scripts and sync plans/docs.
  - Fix hermetic quality target behavior and env guardrails.
  - Complete documentation consistency updates across `docs/plans`, `docs/release`, and `docs/research`.
  - Exit gate: doc/workflow tests and maintenance scripts pass; plan docs match runtime behavior.
- Delivery discipline:
  - One PR per phase; avoid mixing workflow/security and runtime parser changes.
  - Every phase requires explicit verification before status is moved to done in `tasks/todo.md`.

## Cloudflare Deployment Baseline (2026-02-27)
- Canonical production path is Cloudflare-only:
  - Backend: `backend-cloudflare` native Python Worker.
  - Frontend: `frontend-web` Cloudflare Worker.
- Canonical deploy command (GitHub-independent):
  - `bash scripts/deploy_cloudflare_gemini_mvp_no_github.sh`
- Deploy script behavior expectations:
  - Uses local Wrangler when available, falls back to `npx wrangler`.
  - Syncs backend + frontend bearer token secrets.
  - Fails fast if `GEMINI_API_KEY` is unavailable/placeholder.
  - Prevents accidental bearer-token rotation unless `ALLOW_GENERATE_BEARER_TOKEN=true`.
- Runtime data/policy resilience:
  - Source registry and source policy must be available in hardened mode.
  - Embedded fallbacks are present in `src/immcad_api/sources/source_registry_embedded.py` and `src/immcad_api/policy/source_policy_embedded.py`.
- Legacy Vercel tooling policy:
  - `scripts/vercel_env_sync.py` and related `vercel-*` commands are recovery-only and not part of the active deploy path.
