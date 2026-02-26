#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${IMMCAD_API_BASE_URL:-}"
TOKEN="${IMMCAD_API_BEARER_TOKEN:-${API_BEARER_TOKEN:-}}"
QUERY="${CHAT_CASE_LAW_SMOKE_QUERY:-Find one Federal Court immigration case on procedural fairness with citation and court.}"
TIMEOUT_SECONDS="${CHAT_CASE_LAW_SMOKE_TIMEOUT_SECONDS:-25}"
SESSION_ID="${CHAT_CASE_LAW_SMOKE_SESSION_ID:-chat-case-law-smoke-20260226}"

if [[ -z "${BASE_URL}" ]]; then
  echo "[ERROR] IMMCAD_API_BASE_URL is required."
  echo "Example: IMMCAD_API_BASE_URL=https://immcad-api.example.com make chat-case-law-smoke"
  exit 1
fi
if [[ -z "${TOKEN}" ]]; then
  echo "[ERROR] IMMCAD_API_BEARER_TOKEN (or API_BEARER_TOKEN) is required."
  exit 1
fi

TMP_HEADERS="$(mktemp /tmp/chat-case-law-headers.XXXXXX)"
TMP_BODY="$(mktemp /tmp/chat-case-law-body.XXXXXX)"
trap 'rm -f "${TMP_HEADERS}" "${TMP_BODY}"' EXIT

status_code="$(
  curl -sS \
    --max-time "${TIMEOUT_SECONDS}" \
    -D "${TMP_HEADERS}" \
    -o "${TMP_BODY}" \
    -w "%{http_code}" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer ${TOKEN}" \
    -X POST "${BASE_URL%/}/api/chat" \
    -d "{\"session_id\":\"${SESSION_ID}\",\"message\":\"${QUERY}\",\"locale\":\"en-CA\",\"mode\":\"standard\"}"
)"

trace_id="$(grep -i '^x-trace-id:' "${TMP_HEADERS}" | head -n1 | sed 's/^[^:]*:[[:space:]]*//' | tr -d '\r' || true)"

if [[ "${status_code}" != "200" ]]; then
  echo "[ERROR] Chat case-law smoke failed with HTTP ${status_code}."
  echo "[INFO] Trace ID: ${trace_id:-Unavailable}"
  echo "[DEBUG] Response body:"
  cat "${TMP_BODY}"
  exit 1
fi

python3 - <<'PY' "${TMP_BODY}" "${trace_id:-Unavailable}"
import json
import sys

body_path = sys.argv[1]
trace_id = sys.argv[2]

with open(body_path, "r", encoding="utf-8") as handle:
    payload = json.load(handle)

answer = payload.get("answer")
if not isinstance(answer, str) or not answer.strip():
    raise SystemExit("[ERROR] Chat case-law smoke missing non-empty answer.")

citations = payload.get("citations")
if not isinstance(citations, list) or not citations:
    raise SystemExit("[ERROR] Chat case-law smoke missing citations list.")

allowed_case_sources = {
    "FC_DECISIONS",
    "FCA_DECISIONS",
    "SCC_DECISIONS",
    "CANLII_CASE_BROWSE",
    "CANLII_CASE_CITATOR",
}

source_ids = {
    str(citation.get("source_id", "")).strip().upper()
    for citation in citations
    if isinstance(citation, dict)
}

if not (source_ids & allowed_case_sources):
    raise SystemExit(
        "[ERROR] Chat case-law smoke did not return a case-law citation source. "
        f"Observed source_ids={sorted(source_ids)}"
    )

print(
    "[OK] Chat case-law smoke passed. "
    f"citations={len(citations)} "
    f"case_law_sources={sorted(source_ids & allowed_case_sources)} "
    f"trace_id={trace_id}"
)
PY
