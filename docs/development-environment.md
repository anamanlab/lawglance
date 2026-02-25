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
- [Cloudflare Frontend Deploy](#cloudflare-frontend-deploy)
- [Cloudflare Backend Proxy (Transitional)](#cloudflare-backend-proxy-(transitional))
- [Legacy Vercel Environment Sync (Transitional)](#legacy-vercel-environment-sync-(transitional))
- [Troubleshooting](#troubleshooting)

This guide standardizes local development for IMMCAD.

## Supported baseline

- OS: Linux/macOS (Windows via WSL recommended)
- Python: `3.11+`
- Package/runtime manager: `uv`
- Node.js: `20+` (required for `frontend-web`)
- Optional runtime: Redis for chat history cache

## Quick start (recommended)

Run from repository root:

```bash
./scripts/setup_dev_env.sh
./scripts/verify_dev_env.sh
```

Then start the production runtime:

```bash
# Terminal 1
make api-dev

# Terminal 2
make frontend-install
make frontend-dev
```

Legacy note: `app.py` (Streamlit) is dev-only and no longer the production path. It now acts as a thin client to backend `/api/chat`.

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

# Documentation quality checks
make docs-audit
```

Run services in separate terminals when actively developing:

```bash
# Terminal 1
make api-dev

# Terminal 2
make frontend-dev
```

Lawyer case-research local smoke (optional quick check):

```bash
curl -sS -X POST http://127.0.0.1:8000/api/research/lawyer-cases \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "session-123456",
    "matter_summary": "Federal Court appeal on procedural fairness and inadmissibility",
    "jurisdiction": "ca",
    "court": "fc",
    "limit": 5
  }'
```

## Environment variables

Use `.env.example` as baseline:

```dotenv
OPENAI_API_KEY=your-openai-api-key
REDIS_URL=redis://localhost:6379/0
IMMCAD_API_BASE_URL=http://127.0.0.1:8000
IMMCAD_API_BEARER_TOKEN=your-api-bearer-token
CITATION_TRUSTED_DOMAINS=laws-lois.justice.gc.ca,justice.gc.ca,canada.ca,ircc.canada.ca,canlii.org
```

Production/CI policy:

- Set `ENVIRONMENT=production` (or `prod`/`ci`, including aliases like `production-us-east`, `prod_blue`, `ci-smoke`) only in hardened environments.
- `IMMCAD_ENVIRONMENT` is accepted as a compatibility alias for `ENVIRONMENT`; when both are set they must match.
- `IMMCAD_API_BEARER_TOKEN` is the canonical token variable and is mandatory in `production`/`prod`/`ci` (`API_BEARER_TOKEN` is supported only as a compatibility alias).
- `CITATION_TRUSTED_DOMAINS` must be explicitly set in `production`/`prod`/`ci`.
- `EXPORT_POLICY_GATE_ENABLED` must remain enabled in `production`/`prod`/`ci` (startup rejects disabled values).
- `EXPORT_MAX_DOWNLOAD_BYTES` controls export payload caps (default `10485760`, i.e. 10 MB).
- `CASE_SEARCH_OFFICIAL_ONLY_RESULTS=true` is recommended in hardened deployments to hide non-exportable case results from UI.
- `GET /ops/metrics` requires a valid bearer token in every environment.
- Never commit `.env`; use platform secrets managers and short rotation windows for tokens.
- If the team adopts `git-secret` for encrypted repo-stored env bundles, use it only for approved non-production/bootstrap workflows and follow `docs/release/git-secret-runbook.md` (do not replace GitHub/Cloudflare runtime secrets).

Recommended hardened baseline:

```dotenv
ENVIRONMENT=production-us-east
IMMCAD_API_BEARER_TOKEN=<secret>
ENABLE_SCAFFOLD_PROVIDER=false
ALLOW_SCAFFOLD_SYNTHETIC_CITATIONS=false
EXPORT_POLICY_GATE_ENABLED=true
ENABLE_CASE_SEARCH=true
ENABLE_OFFICIAL_CASE_SOURCES=true
CASE_SEARCH_OFFICIAL_ONLY_RESULTS=true
CITATION_TRUSTED_DOMAINS=laws-lois.justice.gc.ca,justice.gc.ca,canada.ca,ircc.canada.ca,canlii.org
```

## Redis (optional but recommended)

Run local Redis with Docker:

```bash
docker run --name immcad-redis -p 6379:6379 -d redis:7-alpine
```

Stop and remove:

```bash
docker stop immcad-redis && docker rm immcad-redis
```

## Cloudflare Frontend Deploy

`frontend-web` is Cloudflare-ready via OpenNext + Wrangler.

Local parity verification:

```bash
make frontend-cf-build
make frontend-cf-preview
```

Required secrets/vars for CI deploy:

- `CLOUDFLARE_API_TOKEN`
- `CLOUDFLARE_ACCOUNT_ID`

GitHub Actions workflow:

- `.github/workflows/cloudflare-frontend-deploy.yml`

The workflow performs typecheck + contract tests + OpenNext bundle build before deploy.

## Cloudflare Backend Proxy (Transitional)

`backend-cloudflare` provides a Cloudflare Worker edge proxy in front of the current backend origin.

Local/backend migration checks:

```bash
# Build backend runtime container spike artifact
make backend-cf-spike-build

# Deploy backend proxy worker
make backend-cf-proxy-deploy
```

Key files:

- `backend-cloudflare/src/worker.ts`
- `backend-cloudflare/wrangler.backend-proxy.jsonc`
- `.github/workflows/cloudflare-backend-proxy-deploy.yml`
- GitHub Actions secret required for deploy: `IMMCAD_BACKEND_ORIGIN`

This is a transitional step for edge cutover while backend runtime migration (Containers vs Python Worker) is finalized.

## Cloudflare Backend Native (Python Worker, In Progress)

Native backend runtime scaffold artifacts are available under `backend-cloudflare/`:

- `backend-cloudflare/src/entry.py`
- `backend-cloudflare/wrangler.toml`
- `backend-cloudflare/pyproject.toml`
- `.github/workflows/cloudflare-backend-native-deploy.yml`

Local/native commands:

```bash
make backend-cf-native-sync
make backend-cf-native-dev
make backend-cf-native-deploy
```

Note: native Python Worker deploy can fail on Cloudflare plan script-size limits (`code: 10027`) for large dependency bundles; validate plan/runtime constraints before cutover.

Runtime performance smoke helper (authenticated):

```bash
export IMMCAD_API_BASE_URL=https://immcad-api.arkiteto.dpdns.org
export IMMCAD_API_BEARER_TOKEN=<prod-token>
REQUESTS=20 CONCURRENCY=5 MAX_P95_SECONDS=2.5 make backend-cf-perf-smoke
```

## Legacy Vercel Environment Sync (Transitional)

Use `scripts/vercel_env_sync.py` to analyze, pull, diff, validate, push, and backup Vercel variables for linked projects.

This workflow is retained only for transitional operations while backend origin remains on legacy infrastructure. It is not the primary Cloudflare deployment path.

Typical project directories in this repo:

- `frontend-web` (linked Vercel frontend project)
- `backend-vercel` (linked Vercel backend project)

Project-scoped templates:

- `frontend-web/.env.example`
- `backend-vercel/.env.example`

Run directly:

```bash
python scripts/vercel_env_sync.py analyze --project-dir frontend-web
python scripts/vercel_env_sync.py pull --project-dir frontend-web --environment production
python scripts/vercel_env_sync.py diff --project-dir backend-vercel --environment production
python scripts/vercel_env_sync.py validate --project-dir backend-vercel --environment production
python scripts/vercel_env_sync.py push --project-dir backend-vercel --file .env.production --environment production
python scripts/vercel_env_sync.py backup --project-dir backend-vercel
```

Or use Make targets:

```bash
make vercel-env-analyze PROJECT_DIR=frontend-web
make vercel-env-pull PROJECT_DIR=frontend-web ENV=production
make vercel-env-diff PROJECT_DIR=backend-vercel ENV=production
make vercel-env-validate PROJECT_DIR=backend-vercel ENV=production
make vercel-env-push-dry-run PROJECT_DIR=backend-vercel ENV=production
make vercel-env-backup PROJECT_DIR=backend-vercel
make vercel-env-restore PROJECT_DIR=backend-vercel TS=YYYYMMDD_HHMMSS
```

Notes:

- `push` writes to Vercel; use `--dry-run` first. Without `--file`, `push` uses the script's default per-project file map (it can push multiple environments).
- `pull` creates a local backup unless `--no-backup` is provided.
- `validate` loads required keys from `<project-dir>/.env.example` and falls back to repo-root `.env.example`, plus explicit `--required` keys.
- backup files are namespaced by project directory in `.env-backups/` to avoid collisions.
- `git-secret` (if used) complements this workflow by encrypting repo-stored env bundles; it does not replace Cloudflare runtime secret bindings or `scripts/vercel_env_sync.py` in transitional scenarios.

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
- `NotImplementedError: /dev/urandom (or equivalent) not found` in restricted sandboxes:
  - Use `./scripts/venv_exec.sh <command>` (for example `./scripts/venv_exec.sh pytest -q`).
  - This wrapper enables deterministic local fallbacks for entropy and asyncio cross-thread wakeups only when the runtime cannot support them natively.
  - Do not rely on these fallbacks for production runtime security guarantees.
