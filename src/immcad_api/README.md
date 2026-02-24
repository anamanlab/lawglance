# IMMCAD API Scaffold

Run locally (after dependencies are installed):

```bash
uv run uvicorn immcad_api.main:app --app-dir src --reload --port 8000
```

Endpoints:

- `POST /api/chat`
- `POST /api/search/cases`
- `GET /healthz`

## Environment Variables

- `OPENAI_API_KEY` (optional in scaffold; used by primary provider)
- `GEMINI_API_KEY` (optional in scaffold; used by fallback provider)
- `ENABLE_OPENAI_PROVIDER` (optional, default `true`; set `false` for Gemini-only runtime)
- `PRIMARY_PROVIDER` (optional, default `openai`; set `gemini` for Gemini-only runtime)
- `CANLII_API_KEY` (optional; enables CanLII client attempts)
- `CANLII_BASE_URL` (optional, default `https://api.canlii.org/v1`)
- `ENVIRONMENT` (optional, default `development`; use `production`/`prod`/`ci` for hardened mode)
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
- `ENABLE_SCAFFOLD_PROVIDER` (optional, default `true`)
- `ALLOW_SCAFFOLD_SYNTHETIC_CITATIONS` (optional, default `true`; must be `false` in `production`/`prod`/`ci`)

## Notes

- If provider keys are missing, scaffold provider returns deterministic responses.
- If `ALLOW_SCAFFOLD_SYNTHETIC_CITATIONS=false` and no grounded citations are available, chat returns a safe constrained response with low confidence and no citations.
- Case-law fallback behavior is environment-sensitive:
  - `development` (and non-prod environments): CanLII failures can return deterministic scaffold case data for integration continuity.
  - `production`/`prod`/`ci`: CanLII failures return a structured `SOURCE_UNAVAILABLE` envelope with `trace_id`; synthetic scaffold cases are disabled.
- CanLII integration uses metadata endpoints only and enforces plan limits (`5000/day`, `2 req/s`, `1 in-flight request`).
- Rate limiting uses Redis when available; otherwise it falls back to in-memory limiting.
- Store all production tokens/keys in a secrets manager and rotate on a regular schedule.
- Provider routing has circuit-breaker safeguards for repeated provider failures.

## Operational Scripts

- Run registry-driven ingestion jobs and emit JSON report:
  - `uv run python scripts/run_ingestion_jobs.py --cadence daily`
  - Uses checkpoint state (`artifacts/ingestion/checkpoints.json`) for conditional fetches.
- Verify CanLII API key access:
  - `make canlii-key-verify`
- Run live CanLII case-search smoke against deployed API:
  - `IMMCAD_API_BASE_URL=https://<backend> IMMCAD_API_BEARER_TOKEN=<token> make canlii-live-smoke`
- Generate jurisdictional scoring report (JSON + Markdown):
  - `uv run python scripts/generate_jurisdiction_eval_report.py`
- Run jurisdictional behavior suite (policy refusal + citation checks):
  - `uv run python scripts/run_jurisdictional_test_suite.py`
