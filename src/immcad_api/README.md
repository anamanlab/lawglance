# IMMCAD API Scaffold

Run locally (after dependencies are installed):

```bash
uv run uvicorn immcad_api.main:app --app-dir src --reload --port 8000
```

Endpoints:

- `POST /api/chat`
- `POST /api/search/cases`
- `POST /api/export/cases`
- `GET /healthz`
- `GET /ops/metrics` (requires bearer auth when `IMMCAD_API_BEARER_TOKEN` is configured; `API_BEARER_TOKEN` is accepted as a compatibility alias)

## Environment Variables

- `OPENAI_API_KEY` (optional in scaffold; used by primary provider)
- `GEMINI_API_KEY` (optional in scaffold; used by fallback provider)
- `ENABLE_OPENAI_PROVIDER` (optional, default `true`; set `false` for Gemini-only runtime)
- `PRIMARY_PROVIDER` (optional, default `openai`; set `gemini` for Gemini-only runtime)
- `CANLII_API_KEY` (optional; enables CanLII client attempts)
- `CANLII_BASE_URL` (optional, default `https://api.canlii.org/v1`)
- `ENABLE_CASE_SEARCH` (optional, default `true`; set `false` for Gemini-only MVP to disable `/api/search/cases` and `/api/export/cases`)
- `ENABLE_OFFICIAL_CASE_SOURCES` (optional; defaults to `false` in development and `true` in `production`/`prod`/`ci`; enables SCC/FC/FCA public-feed search without CanLII)
- `CASE_SEARCH_OFFICIAL_ONLY_RESULTS` (optional, default `true` in `production`/`prod`/`ci` and `false` in development; when `true`, `/api/search/cases` filters out results that are not export-eligible under source policy and host checks)
- `OFFICIAL_CASE_CACHE_TTL_SECONDS` (optional, default `300`; fresh-cache window for official SCC/FC/FCA feed results)
- `OFFICIAL_CASE_STALE_CACHE_TTL_SECONDS` (optional, default `900`; stale-cache serve window; must be `>= OFFICIAL_CASE_CACHE_TTL_SECONDS`)
- `ENVIRONMENT` (optional; defaults to `development`, or `production` when `VERCEL_ENV=production`; use `production`/`prod`/`ci` for hardened mode, including aliases like `production-us-east`, `prod_blue`, `ci-smoke`)
- `IMMCAD_ENVIRONMENT` (optional compatibility alias for `ENVIRONMENT`; if both are set they must match)
- `IMMCAD_API_BEARER_TOKEN` (required when `ENVIRONMENT` is `production`, `prod`, or `ci`; `API_BEARER_TOKEN` is accepted as a compatibility alias)
- `API_RATE_LIMIT_PER_MINUTE` (optional, default `120`)
- `CORS_ALLOWED_ORIGINS` (optional CSV, default `http://127.0.0.1:3000,http://localhost:3000`)
- `REDIS_URL` (optional; if unset the API uses in-memory rate limiting)
- `OPENAI_MODEL` (optional, default `gpt-4o-mini`)
- `GEMINI_MODEL` (default `gemini-2.5-flash-lite` in development; must be explicitly set in `production`/`prod`/`ci`)
- `GEMINI_MODEL_FALLBACKS` (optional CSV, default `gemini-2.5-flash`; preview/experimental models are rejected in `production`/`prod`/`ci`)
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
- If `ALLOW_SCAFFOLD_SYNTHETIC_CITATIONS=false`, runtime uses curated official grounding citations (IRPA/IRCC references) instead of synthetic scaffold citations.
- Runtime citation enforcement accepts citations only when they are well-formed and match grounding-adapter candidates; ungrounded citations are dropped and the response is constrained safely.
- Runtime citation enforcement also validates citation URL domains against `CITATION_TRUSTED_DOMAINS`.
- Hardened mode (`production`/`prod`/`ci`) requires `GEMINI_API_KEY`; case search requires at least one backend (`ENABLE_OFFICIAL_CASE_SOURCES=true` or `CANLII_API_KEY`); if `ENABLE_OPENAI_PROVIDER=true`, `OPENAI_API_KEY` is also required.
- Case-law fallback behavior is environment-sensitive:
  - `development` (and non-prod environments): official-feed search is disabled by default and CanLII failures can return deterministic scaffold case data for integration continuity.
  - `production`/`prod`/`ci`: official SCC/FC/FCA feeds are enabled by default; when all configured case sources are unavailable, the API returns a structured `SOURCE_UNAVAILABLE` envelope with `trace_id`.
- Official feeds are always the primary case-search source; CanLII is queried as a non-blocking fallback when official feeds are unavailable or return no matches.
- `POST /api/search/cases` returns export metadata (`source_id`, `document_url`, `export_allowed`, `export_policy_reason`) alongside each result.
- `CASE_SEARCH_OFFICIAL_ONLY_RESULTS=true` keeps `/api/search/cases` results limited to export-eligible official sources, which avoids dead-end export attempts in production UX.
- `source_id` values are registry-driven (`data/sources/canada-immigration/registry.json`) and export eligibility is enforced by source policy.
- `POST /api/export/cases` requires explicit per-request consent and a signed approval token issued by `POST /api/export/cases/approval` before any download is attempted.
- `POST /api/export/cases` rejects missing or `false` approval with `403 POLICY_BLOCKED` and `policy_reason=source_export_user_approval_required`.
- `POST /api/export/cases` enforces trusted source-host matching for `document_url` (exact host or dot-bounded subdomain such as `www.<source-host>`).
- `POST /api/export/cases` rejects non-PDF upstream responses with `422 VALIDATION_ERROR` and `policy_reason=source_export_non_pdf_payload` when `format=pdf`.
- successful `POST /api/export/cases` responses stream binary content and include `x-trace-id`, `x-export-policy-reason`, and `content-disposition` headers.
- `/ops/metrics` includes `request_metrics.export.audit_recent` with per-export consent/audit events (trace ID, client ID, source/case, host, approval flag, outcome, policy reason).
- Official SCC/FC/FCA search uses in-process cache with stale-while-refresh behavior to reduce tail latency and temporary upstream feed outages.
- CanLII integration uses metadata endpoints only and enforces plan limits (`5000/day`, `2 req/s`, `1 in-flight request`).
- Rate limiting uses Redis when available; otherwise it falls back to in-memory limiting.
- `/ops/metrics` is treated as an operational endpoint and is protected by bearer auth whenever `IMMCAD_API_BEARER_TOKEN` (or `API_BEARER_TOKEN`) is set.
- Store all production tokens/keys in a secrets manager and rotate on a regular schedule.
- Provider routing has circuit-breaker safeguards for repeated provider failures.

## Operational Scripts

- Run registry-driven ingestion jobs and emit JSON report:
  - `uv run python scripts/run_ingestion_jobs.py --cadence daily`
  - `ENVIRONMENT=production uv run python scripts/run_ingestion_jobs.py --cadence scheduled_incremental --fail-on-error`
  - Uses checkpoint state (`.cache/immcad/ingestion-checkpoints.json`) for conditional fetches.
  - Enforces source policy gates from `config/source_policy.yaml` (or `--source-policy`).
- Run Cloudflare hourly ingestion scheduler wrapper (FC hourly, SCC every 6h, laws daily + Tue/Fri full-sync window):
  - `uv run python scripts/run_cloudflare_ingestion_hourly.py --fail-on-error`
  - Writes scheduler report JSON + federal-laws section chunks JSONL (`--federal-laws-output`).
  - Dry-run schedule only: `uv run python scripts/run_cloudflare_ingestion_hourly.py --dry-run --utc-timestamp 2026-02-27T04:00:00Z`
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
