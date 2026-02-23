# Repository Guidelines

## Project Structure & Module Organization
- Main app entrypoint: `app.py` (Streamlit chat UI).
- Core orchestration and RAG flow: `lawglance_main.py`, `chains.py`, `cache.py`, `prompts.py`.
- Configuration and prompts: `config/prompts.yaml`, `.env`, `.env.example`.
- Data/index artifacts: `chroma_db_legal_bot_part1/` (local Chroma store).
- Docs and onboarding: `README.md`, `docs/` (see `docs/development-environment.md`).
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
