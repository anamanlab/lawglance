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
- `CANLII_API_KEY` (optional; enables CanLII client attempts)
- `CANLII_BASE_URL` (optional, default `https://api.canlii.org/v1`)
- `ENVIRONMENT` (optional, default `development`; use `production`/`prod`/`ci` for hardened mode)
- `API_BEARER_TOKEN` (required when `ENVIRONMENT` is `production`, `prod`, or `ci`)
- `API_RATE_LIMIT_PER_MINUTE` (optional, default `120`)
- `REDIS_URL` (optional, default `redis://localhost:6379/0`; used for distributed rate limiting when reachable)
- `OPENAI_MODEL` (optional, default `gpt-4o-mini`)
- `GEMINI_MODEL` (optional, default `gemini-2.5-flash`)
- `PROVIDER_TIMEOUT_SECONDS` (optional, default `15`)
- `PROVIDER_MAX_RETRIES` (optional, default `1`)
- `PROVIDER_CIRCUIT_BREAKER_FAILURE_THRESHOLD` (optional, default `3`)
- `PROVIDER_CIRCUIT_BREAKER_OPEN_SECONDS` (optional, default `30`)
- `ENABLE_SCAFFOLD_PROVIDER` (optional, default `true`)

## Notes

- If provider keys are missing, scaffold provider returns deterministic responses.
- If CanLII key or endpoint is unavailable, case search falls back to deterministic scaffold data.
- Rate limiting uses Redis when available; otherwise it falls back to in-memory limiting.
- Store all production tokens/keys in a secrets manager and rotate on a regular schedule.
- Provider routing has circuit-breaker safeguards for repeated provider failures.

## Operational Scripts

- Run registry-driven ingestion jobs and emit JSON report:
  - `uv run python scripts/run_ingestion_jobs.py --cadence daily`
  - Uses checkpoint state (`artifacts/ingestion/checkpoints.json`) for conditional fetches.
- Generate jurisdictional scoring report (JSON + Markdown):
  - `uv run python scripts/generate_jurisdiction_eval_report.py`
- Run jurisdictional behavior suite (policy refusal + citation checks):
  - `uv run python scripts/run_jurisdictional_test_suite.py`
