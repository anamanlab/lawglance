# Staging Smoke Rollback Trigger Criteria (Canada Scope)

Use this runbook when `scripts/run_api_smoke_tests.sh` fails in staging or release gates.

## Smoke checks covered

- Chat submit contract (`POST /api/chat`) with citation payload required for frontend source chips.
- Policy refusal contract (`fallback_used.reason = policy_block`) for representation requests.
- Related case-search contract (`POST /api/search/cases`) for frontend case list rendering.
- `x-trace-id` capture for each request path in `artifacts/evals/staging-smoke-report.json`.

## Mandatory rollback triggers

Rollback the deployment candidate when any condition below is true:

- Smoke workflow exits non-zero for chat submit, refusal path, or case-search path.
- `staging-smoke-report.json` is missing or does not include all three trace IDs.
- Citation contract fails (missing `title`, `url`, or `pin` fields in chat citations).
- Policy refusal contract fails (no refusal reason, non-empty citations, or non-low confidence).
- Case-search contract fails (missing citation text or URL for returned results).

## Decision window

- If the failure is reproducible in two consecutive reruns within 30 minutes, trigger rollback.
- If failure is non-reproducible but trace IDs map to provider/transient incidents, pause promotion and open an incident before retrying.
- Do not promote to production until one full smoke run passes with report artifact attached.

## Immediate actions on failure

1. Capture the workflow run URL and attach `staging-smoke-report.json`.
2. Copy trace IDs from the report and correlate using `docs/release/incident-observability-runbook.md`.
3. Revert deployment candidate to the last passing staging build.
4. Re-run staging smoke on the reverted build to confirm recovery before resuming promotion.
