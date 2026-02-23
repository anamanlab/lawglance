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

Then start the app:

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
```

## Environment variables

Use `.env.example` as baseline:

```dotenv
OPENAI_API_KEY=your-openai-api-key
REDIS_URL=redis://localhost:6379/0
```

Production/CI policy:

- Set `ENVIRONMENT=production` (or `prod`/`ci`) only in hardened environments.
- `API_BEARER_TOKEN` is mandatory in `production`/`prod`/`ci`.
- Never commit `.env`; use platform secrets managers and short rotation windows for tokens.

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
  - Verify `OPENAI_API_KEY` in `.env`.
- Redis warnings:
  - App can run without Redis, but session caching may be degraded.
