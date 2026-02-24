# IMMCAD API Scaffold

Run locally (after dependencies are installed):

```bash
uv run uvicorn immcad_api.main:app --app-dir src --reload --port 8000
```

Endpoints:

- `POST /api/chat`
- `POST /api/search/cases`
- `GET /healthz`
- `GET /ops/metrics` (requires bearer auth when `API_BEARER_TOKEN` is configured)

## Environment Variables

- `OPENAI_API_KEY` (optional in scaffold; used by primary provider)
- `GEMINI_API_KEY` (optional in scaffold; used by fallback provider)
- `ENABLE_OPENAI_PROVIDER` (optional, default `true`; set `false` for Gemini-only runtime)
- `PRIMARY_PROVIDER` (optional, default `openai`; set `gemini` for Gemini-only runtime)
- `CANLII_API_KEY` (optional; enables CanLII client attempts)
- `CANLII_BASE_URL` (optional, default `https://api.canlii.org/v1`)
- `ENABLE_CASE_SEARCH` (optional, default `true`; set `false` for Gemini-only MVP to disable `/api/search/cases` and `/api/export/cases`)
- `ENVIRONMENT` (optional; defaults to `development`, or `production` when `VERCEL_ENV=production`; use `production`/`prod`/`ci` for hardened mode)
- `API_BEARER_TOKEN` (required when `ENVIRONMENT` is `production`, `prod`, or `ci`)
- `API_RATE_LIMIT_PER_MINUTE` (optional, default `120`)
- `CORS_ALLOWED_ORIGINS` (optional CSV, default `http://127.0.0.1:3000,http://localhost:3000`)
- `REDIS_URL` (optional, default `redis://localhost:6379/0`; used for distributed rate limiting when reachable)
- `OPENAI_MODEL` (optional, default `gpt-4o-mini`)
- `GEMINI_MODEL` (optional, default `gemini-3-flash-preview`)
- `GEMINI_MODEL_FALLBACKS` (optional CSV, default `gemini-2.5-flash`)
- `PROVIDER_TIMEOUT_SECONDS` (optional, default `15`)
- `PROVIDER_MAX_RETRIES` (optional, default `1`)
- `PROVIDER_CIRCUIT_BREAKER_FAILURE_THRESHOLD` (optional, default `3`)
- `PROVIDER_CIRCUIT_BREAKER_OPEN_SECONDS` (optional, default `30`)
- `ENABLE_SCAFFOLD_PROVIDER` (optional, default `true`; must be `false` in `production`/`prod`/`ci`)
- `ALLOW_SCAFFOLD_SYNTHETIC_CITATIONS` (optional, default `true`; must be `false` in `production`/`prod`/`ci`)
- `EXPORT_POLICY_GATE_ENABLED` (optional, default `false`; when `true`, export endpoints enforce source-policy gate checks)
- `CITATION_TRUSTED_DOMAINS` (CSV; default in development: `laws-lois.justice.gc.ca,justice.gc.ca,canada.ca,ircc.canada.ca,canlii.org`; must be explicitly set in `production`/`prod`/`ci`)
- `SOURCE_POLICY_PATH` (optional; path override for ingestion source policy, defaults to `config/source_policy.yaml`)

## Notes

- If provider keys are missing, scaffold provider returns deterministic responses.
- If `ALLOW_SCAFFOLD_SYNTHETIC_CITATIONS=false` and no grounded citations are available, chat returns a safe constrained response with low confidence and no citations.
- Runtime citation enforcement accepts citations only when they are well-formed and match grounding-adapter candidates; ungrounded citations are dropped and the response is constrained safely.
- Runtime citation enforcement also validates citation URL domains against `CITATION_TRUSTED_DOMAINS`.
- Hardened mode (`production`/`prod`/`ci`) requires `GEMINI_API_KEY`; `CANLII_API_KEY` is required only when `ENABLE_CASE_SEARCH=true`. If `ENABLE_OPENAI_PROVIDER=true`, `OPENAI_API_KEY` is also required.
- Case-law fallback behavior is environment-sensitive:
  - `development` (and non-prod environments): CanLII failures can return deterministic scaffold case data for integration continuity.
  - `production`/`prod`/`ci`: CanLII failures return a structured `SOURCE_UNAVAILABLE` envelope with `trace_id`; synthetic scaffold cases are disabled.
- CanLII integration uses metadata endpoints only and enforces plan limits (`5000/day`, `2 req/s`, `1 in-flight request`).
- Rate limiting uses Redis when available; otherwise it falls back to in-memory limiting.
- `/ops/metrics` is treated as an operational endpoint and is protected by bearer auth whenever `API_BEARER_TOKEN` is set.
- Store all production tokens/keys in a secrets manager and rotate on a regular schedule.
- Provider routing has circuit-breaker safeguards for repeated provider failures.

## Operational Scripts

- Run registry-driven ingestion jobs and emit JSON report:
  - `uv run python scripts/run_ingestion_jobs.py --cadence daily`
  - `ENVIRONMENT=production uv run python scripts/run_ingestion_jobs.py --cadence scheduled_incremental --fail-on-error`
  - Uses checkpoint state (`artifacts/ingestion/checkpoints.json`) for conditional fetches.
  - Enforces source policy gates from `config/source_policy.yaml` (or `--source-policy`).
- Run deterministic ingestion smoke gate (no external network required):
  - `make ingestion-smoke`
- Evaluate operational alert thresholds against live `/ops/metrics`:
  - `IMMCAD_API_BASE_URL=https://<backend-domain> IMMCAD_API_BEARER_TOKEN=<token> make ops-alert-eval`
- Verify CanLII API key access:
  - `make canlii-key-verify`
- Run live CanLII case-search smoke against deployed API:
  - `IMMCAD_API_BASE_URL=https://<backend> IMMCAD_API_BEARER_TOKEN=<token> make canlii-live-smoke`
- Generate jurisdictional scoring report (JSON + Markdown):
  - `uv run python scripts/generate_jurisdiction_eval_report.py`
- Run jurisdictional behavior suite (policy refusal + citation checks):
  - `uv run python scripts/run_jurisdictional_test_suite.py`
