# Development Environment Setup

## Table of Contents

- [Table of Contents](#table-of-contents)
- [Supported baseline](#supported-baseline)
- [Quick start (recommended)](#quick-start-(recommended))
- [Manual install prerequisites](#manual-install-prerequisites)
  - [Python 3.11+](#python-311+)
  - [uv](#uv)
- [Project bootstrap details](#project-bootstrap-details)
- [Team-shared editor defaults](#team-shared-editor-defaults)
- [Daily workflow](#daily-workflow)
- [Environment variables](#environment-variables)
- [Redis (optional but recommended)](#redis-(optional-but-recommended))
- [Troubleshooting](#troubleshooting)

- [Supported baseline](#supported-baseline)
- [Quick start (recommended)](#quick-start-(recommended))
- [Manual install prerequisites](#manual-install-prerequisites)
  - [Python 3.11+](#python-311+)
  - [uv](#uv)
- [Project bootstrap details](#project-bootstrap-details)
- [Team-shared editor defaults](#team-shared-editor-defaults)
- [Daily workflow](#daily-workflow)
- [Environment variables](#environment-variables)
- [Redis (optional but recommended)](#redis-(optional-but-recommended))
- [Troubleshooting](#troubleshooting)

This guide standardizes local development for IMMCAD.

## Supported baseline

- OS: Linux/macOS (Windows via WSL recommended)
- Python: `3.11+`
- Package/runtime manager: `uv`
- Optional runtime: Redis for chat history cache

## Quick start (recommended)

Run from repository root:

```bash
./scripts/setup_dev_env.sh
./scripts/verify_dev_env.sh
```

Then start the API backend:

```bash
uv run uvicorn immcad_api.main:app --app-dir src --reload --port 8000
```

Then start the Streamlit UI (second terminal):

```bash
uv run streamlit run app.py
```

## Manual install prerequisites

### Python 3.11+

- macOS (Homebrew):

```bash
brew install python@3.11
```

- Ubuntu/Debian:

```bash
sudo apt-get update
sudo apt-get install -y python3.11 python3.11-venv
```

- Any OS (pyenv):

```bash
pyenv install 3.11.11
pyenv local 3.11.11
```

### uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## Project bootstrap details

The setup script performs:

1. Platform and Python checks
2. `uv sync --dev` (and `--frozen` when `uv.lock` is present)
3. `.env` bootstrap from `.env.example`
4. Optional Redis check

## Team-shared editor defaults

- `.editorconfig` for consistent formatting
- `.vscode/extensions.json` for recommended extensions
- `.vscode/settings.json` for Python + Ruff defaults

## Daily workflow

```bash
# One-time (or after dependency changes)
./scripts/setup_dev_env.sh

# Validate local environment
./scripts/verify_dev_env.sh

# Lint and test
make quality

# Run API + UI locally
uv run uvicorn immcad_api.main:app --app-dir src --reload --port 8000
uv run streamlit run app.py
```

## Environment variables

Use `.env.example` as baseline:

```dotenv
OPENAI_API_KEY=your-openai-api-key
GEMINI_API_KEY=your-gemini-api-key
API_BASE_URL=http://127.0.0.1:8000
API_BEARER_TOKEN=your-api-bearer-token
REDIS_URL=redis://localhost:6379/0
```

Production/CI policy:

- Set `ENVIRONMENT=production` (or `prod`/`ci`) only in hardened environments.
- `API_BEARER_TOKEN` is mandatory in `production`/`prod`/`ci`.
- Streamlit UI calls FastAPI `/api/chat` using `API_BASE_URL`.
- Never commit `.env`; use platform secrets managers and short rotation windows for tokens.

Additional backend/runtime variables:

- `CANLII_API_KEY`, `CANLII_BASE_URL`
- `OPENAI_MODEL`, `GEMINI_MODEL`
- `ENABLE_SCAFFOLD_PROVIDER`
- `ALLOW_SCAFFOLD_SYNTHETIC_CITATIONS`
- `PROVIDER_TIMEOUT_SECONDS`, `PROVIDER_MAX_RETRIES`
- `PROVIDER_CIRCUIT_BREAKER_FAILURE_THRESHOLD`, `PROVIDER_CIRCUIT_BREAKER_OPEN_SECONDS`
- `API_RATE_LIMIT_PER_MINUTE`

## Redis (optional but recommended)

Run local Redis with Docker:

```bash
docker run --name immcad-redis -p 6379:6379 -d redis:7-alpine
```

Stop and remove:

```bash
docker stop immcad-redis && docker rm immcad-redis
```

## Troubleshooting

- `Python 3.11+ not found`:
  - Install Python 3.11 and ensure it is on your `PATH`.
- `uv: command not found`:
  - Reopen terminal after install, then run `uv --version`.
- Import check failures:
  - Re-run `./scripts/setup_dev_env.sh`.
- App starts but responses fail:
  - Verify API service is running on `API_BASE_URL`.
  - Verify `API_BEARER_TOKEN` matches backend expectation.
  - Verify provider keys (`OPENAI_API_KEY`, optional `GEMINI_API_KEY`) in `.env`.
- Redis warnings:
  - App can run without Redis, but session caching may be degraded.
