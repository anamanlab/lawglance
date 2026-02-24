# Repository Guidelines

## Project Structure & Module Organization
- Main app entrypoint: `app.py` (Streamlit chat UI).
- Core orchestration and RAG flow: `src/immcad_api/` (legacy local-RAG modules archived under `legacy/local_rag/`).
- Configuration and prompts: `config/prompts.yaml`, `.env`, `.env.example`.
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
- Minimum required env var: `OPENAI_API_KEY`.
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
