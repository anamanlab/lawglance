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
- `API_BEARER_TOKEN` (optional; if set, required for `/api/*` routes)
- `API_RATE_LIMIT_PER_MINUTE` (optional, default `120`)
- `REDIS_URL` (optional, default `redis://localhost:6379/0`; used for distributed rate limiting when reachable)
- `OPENAI_MODEL` (optional, default `gpt-4o-mini`)
- `GEMINI_MODEL` (optional, default `gemini-2.5-flash`)
- `PROVIDER_TIMEOUT_SECONDS` (optional, default `15`)
- `PROVIDER_MAX_RETRIES` (optional, default `1`)
- `ENABLE_SCAFFOLD_PROVIDER` (optional, default `true`)

## Notes

- If provider keys are missing, scaffold provider returns deterministic responses.
- If CanLII key or endpoint is unavailable, case search falls back to deterministic scaffold data.
- Rate limiting uses Redis when available; otherwise it falls back to in-memory limiting.
