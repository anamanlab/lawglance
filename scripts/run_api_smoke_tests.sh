#!/usr/bin/env bash
set -euo pipefail

PORT="${API_SMOKE_PORT:-8010}"
TOKEN="${API_BEARER_TOKEN:-smoke-token}"
HOST="127.0.0.1"
BASE_URL="http://${HOST}:${PORT}"

export ENVIRONMENT="${ENVIRONMENT:-ci}"
export API_BEARER_TOKEN="${TOKEN}"
export ENABLE_SCAFFOLD_PROVIDER="${ENABLE_SCAFFOLD_PROVIDER:-true}"

uv run uvicorn immcad_api.main:app --app-dir src --host "${HOST}" --port "${PORT}" >/tmp/immcad_smoke.log 2>&1 &
SERVER_PID=$!
trap 'kill ${SERVER_PID} >/dev/null 2>&1 || true' EXIT

for _ in $(seq 1 40); do
  if curl -fsS "${BASE_URL}/healthz" >/tmp/immcad_healthz.json 2>/dev/null; then
    break
  fi
  sleep 0.5
done

curl -fsS "${BASE_URL}/healthz" >/tmp/immcad_healthz.json

chat_status=$(curl -sS -o /tmp/immcad_chat.json -w "%{http_code}" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -X POST "${BASE_URL}/api/chat" \
  -d '{"session_id":"smoke-session-12345","message":"Summarize IRPA section 11 in plain language.","locale":"en-CA","mode":"standard"}')

if [[ "${chat_status}" != "200" ]]; then
  echo "Chat smoke test failed with status ${chat_status}"
  cat /tmp/immcad_smoke.log
  cat /tmp/immcad_chat.json || true
  exit 1
fi

case_status=$(curl -sS -o /tmp/immcad_cases.json -w "%{http_code}" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -X POST "${BASE_URL}/api/search/cases" \
  -d '{"query":"express entry inadmissibility","jurisdiction":"ca","court":"fct","limit":2}')

if [[ "${case_status}" != "200" ]]; then
  echo "Case search smoke test failed with status ${case_status}"
  cat /tmp/immcad_smoke.log
  cat /tmp/immcad_cases.json || true
  exit 1
fi

python3 - <<'PY'
import json

with open("/tmp/immcad_chat.json", "r", encoding="utf-8") as handle:
    chat = json.load(handle)
assert "answer" in chat and isinstance(chat["answer"], str)
assert "citations" in chat and isinstance(chat["citations"], list)

with open("/tmp/immcad_cases.json", "r", encoding="utf-8") as handle:
    cases = json.load(handle)
assert "results" in cases and isinstance(cases["results"], list)
assert len(cases["results"]) >= 1
PY

echo "[OK] API smoke tests passed."
