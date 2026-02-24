#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${IMMCAD_API_BASE_URL:-}"
TOKEN="${IMMCAD_API_BEARER_TOKEN:-${API_BEARER_TOKEN:-}}"
QUERY="${CANLII_SMOKE_QUERY:-express entry inadmissibility}"
JURISDICTION="${CANLII_SMOKE_JURISDICTION:-ca}"
DATABASE_ID="${CANLII_SMOKE_DATABASE_ID:-fct}"
LIMIT="${CANLII_SMOKE_LIMIT:-5}"
TIMEOUT_SECONDS="${CANLII_SMOKE_TIMEOUT_SECONDS:-20}"

if [[ -z "${BASE_URL}" ]]; then
  echo "[ERROR] IMMCAD_API_BASE_URL is required."
  echo "Example: IMMCAD_API_BASE_URL=https://<backend-domain> make canlii-live-smoke"
  exit 1
fi

TMP_HEADERS="$(mktemp /tmp/canlii-live-headers.XXXXXX)"
TMP_BODY="$(mktemp /tmp/canlii-live-body.XXXXXX)"
trap 'rm -f "${TMP_HEADERS}" "${TMP_BODY}"' EXIT

auth_args=()
if [[ -n "${TOKEN}" ]]; then
  auth_args=(-H "Authorization: Bearer ${TOKEN}")
fi

status_code="$(
  curl -sS \
    --max-time "${TIMEOUT_SECONDS}" \
    -D "${TMP_HEADERS}" \
    -o "${TMP_BODY}" \
    -w "%{http_code}" \
    -H "Content-Type: application/json" \
    "${auth_args[@]}" \
    -X POST "${BASE_URL%/}/api/search/cases" \
    -d "{\"query\":\"${QUERY}\",\"jurisdiction\":\"${JURISDICTION}\",\"court\":\"${DATABASE_ID}\",\"limit\":${LIMIT}}"
)"

trace_id="$(grep -i '^x-trace-id:' "${TMP_HEADERS}" | head -n1 | sed 's/^[^:]*:[[:space:]]*//' | tr -d '\r' || true)"
fallback_header="$(grep -i '^x-immcad-fallback:' "${TMP_HEADERS}" | head -n1 | sed 's/^[^:]*:[[:space:]]*//' | tr -d '\r' || true)"

if [[ "${status_code}" != "200" ]]; then
  echo "[ERROR] CanLII live smoke failed with HTTP ${status_code}."
  echo "[INFO] Trace ID: ${trace_id:-Unavailable}"
  echo "[DEBUG] Response body:"
  cat "${TMP_BODY}"
  exit 1
fi

if [[ "${fallback_header,,}" == "scaffold" ]]; then
  echo "[ERROR] Unexpected scaffold fallback detected in live smoke."
  echo "[INFO] Trace ID: ${trace_id:-Unavailable}"
  exit 1
fi

python3 - <<'PY' "${TMP_BODY}" "${trace_id:-Unavailable}"
import json
import sys

body_path = sys.argv[1]
trace_id = sys.argv[2]

with open(body_path, "r", encoding="utf-8") as handle:
    payload = json.load(handle)

results = payload.get("results")
if not isinstance(results, list):
    raise SystemExit("[ERROR] Live smoke response is missing results list.")

for item in results:
    title = str(item.get("title", ""))
    if title.startswith("Scaffold Case"):
        raise SystemExit("[ERROR] Live smoke returned scaffold case content.")

print(f"[OK] CanLII live smoke passed. Results: {len(results)}. Trace ID: {trace_id}")
PY
