#!/usr/bin/env bash
set -euo pipefail

PORT="${API_SMOKE_PORT:-8010}"
TOKEN="${API_BEARER_TOKEN:-smoke-token}"
HOST="127.0.0.1"
BASE_URL="http://${HOST}:${PORT}"
REPORT_PATH="${STAGING_SMOKE_REPORT_PATH:-artifacts/evals/staging-smoke-report.json}"
SERVER_LOG_PATH="/tmp/immcad_smoke.log"
ARTIFACT_DIR="$(dirname "${REPORT_PATH}")"

mkdir -p "${ARTIFACT_DIR}"

export ENVIRONMENT="${ENVIRONMENT:-staging}"
export API_BEARER_TOKEN="${TOKEN}"
export ENABLE_SCAFFOLD_PROVIDER="${ENABLE_SCAFFOLD_PROVIDER:-true}"
export ALLOW_SCAFFOLD_SYNTHETIC_CITATIONS="${ALLOW_SCAFFOLD_SYNTHETIC_CITATIONS:-true}"
TMP_CHECKPOINT_PATH="$(mktemp /tmp/immcad-ingestion-checkpoints.XXXXXX.json)"
python3 - <<'PY' "${TMP_CHECKPOINT_PATH}"
import json
import sys
from datetime import datetime, timezone

checkpoint_path = sys.argv[1]
now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
payload = {
    "version": 1,
    "updated_at": now,
    "checkpoints": {
        "SCC_DECISIONS": {
            "etag": "smoke-scc-etag",
            "last_modified": "Sat, 28 Feb 2026 00:00:00 GMT",
            "checksum_sha256": "smoke-scc-checksum",
            "last_http_status": 200,
            "last_success_at": now,
        },
        "FC_DECISIONS": {
            "etag": "smoke-fc-etag",
            "last_modified": "Sat, 28 Feb 2026 00:00:00 GMT",
            "checksum_sha256": "smoke-fc-checksum",
            "last_http_status": 200,
            "last_success_at": now,
        },
    },
}
with open(checkpoint_path, "w", encoding="utf-8") as handle:
    json.dump(payload, handle)
PY
export INGESTION_CHECKPOINT_STATE_PATH="${TMP_CHECKPOINT_PATH}"

uv run uvicorn immcad_api.main:app --app-dir src --host "${HOST}" --port "${PORT}" >"${SERVER_LOG_PATH}" 2>&1 &
SERVER_PID=$!
trap 'kill ${SERVER_PID} >/dev/null 2>&1 || true; rm -f "${TMP_CHECKPOINT_PATH}"' EXIT

print_debug_artifacts() {
  if [[ -f "${SERVER_LOG_PATH}" ]]; then
    cat "${SERVER_LOG_PATH}"
  fi
  cat /tmp/immcad_chat_headers.txt /tmp/immcad_chat.json 2>/dev/null || true
  cat /tmp/immcad_refusal_headers.txt /tmp/immcad_refusal.json 2>/dev/null || true
  cat /tmp/immcad_cases_headers.txt /tmp/immcad_cases.json 2>/dev/null || true
  cat /tmp/immcad_sources_headers.txt /tmp/immcad_sources.json 2>/dev/null || true
}

for _ in $(seq 1 40); do
  if curl -fsS "${BASE_URL}/healthz" >/tmp/immcad_healthz.json 2>/dev/null; then
    break
  fi
  sleep 0.5
done

curl -fsS "${BASE_URL}/healthz" >/tmp/immcad_healthz.json

chat_status=$(curl -sS -o /tmp/immcad_chat.json -w "%{http_code}" \
  -D /tmp/immcad_chat_headers.txt \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -X POST "${BASE_URL}/api/chat" \
  -d '{"session_id":"smoke-session-12345","message":"Summarize IRPA section 11 in plain language.","locale":"en-CA","mode":"standard"}')

if [[ "${chat_status}" != "200" ]]; then
  echo "Chat smoke test failed with status ${chat_status}"
  print_debug_artifacts
  exit 1
fi

refusal_status=$(curl -sS -o /tmp/immcad_refusal.json -w "%{http_code}" \
  -D /tmp/immcad_refusal_headers.txt \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -X POST "${BASE_URL}/api/chat" \
  -d '{"session_id":"smoke-session-12345","message":"Please represent me and file my application","locale":"en-CA","mode":"standard"}')

if [[ "${refusal_status}" != "200" ]]; then
  echo "Policy refusal smoke test failed with status ${refusal_status}"
  print_debug_artifacts
  exit 1
fi

case_status=$(curl -sS -o /tmp/immcad_cases.json -w "%{http_code}" \
  -D /tmp/immcad_cases_headers.txt \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -X POST "${BASE_URL}/api/search/cases" \
  -d '{"query":"express entry inadmissibility","jurisdiction":"ca","court":"fct","limit":2}')

if [[ "${case_status}" != "200" ]]; then
  echo "Case search smoke test failed with status ${case_status}"
  print_debug_artifacts
  exit 1
fi

sources_status=$(curl -sS -o /tmp/immcad_sources.json -w "%{http_code}" \
  -D /tmp/immcad_sources_headers.txt \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -X GET "${BASE_URL}/api/sources/transparency")

if [[ "${sources_status}" != "200" ]]; then
  echo "Source transparency smoke test failed with status ${sources_status}"
  print_debug_artifacts
  exit 1
fi

STAGING_SMOKE_REPORT_PATH="${REPORT_PATH}" python3 - <<'PY'
import json
import os
from datetime import datetime, timezone


def extract_trace_id(headers_path: str) -> str:
    with open(headers_path, "r", encoding="utf-8") as handle:
        for line in handle:
            if line.lower().startswith("x-trace-id:"):
                value = line.split(":", 1)[1].strip()
                if value:
                    return value
    raise AssertionError(f"Missing x-trace-id in {headers_path}")


with open("/tmp/immcad_chat.json", "r", encoding="utf-8") as handle:
    chat = json.load(handle)
assert "answer" in chat and isinstance(chat["answer"], str)
assert "citations" in chat and isinstance(chat["citations"], list)
assert len(chat["citations"]) >= 1
for citation in chat["citations"]:
    assert isinstance(citation.get("title"), str) and citation["title"].strip()
    assert isinstance(citation.get("url"), str) and citation["url"].startswith("http")
    assert isinstance(citation.get("pin"), str) and citation["pin"].strip()

with open("/tmp/immcad_refusal.json", "r", encoding="utf-8") as handle:
    refusal = json.load(handle)
assert refusal["fallback_used"]["reason"] == "policy_block"
assert refusal["citations"] == []
assert refusal["confidence"] == "low"

with open("/tmp/immcad_cases.json", "r", encoding="utf-8") as handle:
    cases = json.load(handle)
assert "results" in cases and isinstance(cases["results"], list)
assert len(cases["results"]) >= 1
for result in cases["results"]:
    assert isinstance(result.get("citation"), str) and result["citation"].strip()
    assert isinstance(result.get("url"), str) and result["url"].startswith("http")

with open("/tmp/immcad_sources.json", "r", encoding="utf-8") as handle:
    sources = json.load(handle)
assert isinstance(sources.get("supported_courts"), list)
assert "SCC" in sources["supported_courts"]
assert "FC" in sources["supported_courts"]
source_items = {
    item.get("source_id"): item for item in sources.get("case_law_sources", [])
}
assert "SCC_DECISIONS" in source_items
assert "FC_DECISIONS" in source_items
assert source_items["SCC_DECISIONS"].get("freshness_status") in {
    "fresh",
    "stale",
    "missing",
}
assert source_items["FC_DECISIONS"].get("freshness_status") in {
    "fresh",
    "stale",
    "missing",
}

allow_priority_failure = os.getenv("ALLOW_PRIORITY_SOURCE_FRESHNESS", "").strip().lower() == "true"
if not allow_priority_failure:
    for source_id in ("SCC_DECISIONS", "FC_DECISIONS"):
        freshness_status = (
            source_items.get(source_id, {}).get("freshness_status") or "missing"
        )
        if freshness_status != "fresh":
            raise AssertionError(
                f"Priority source {source_id} freshness_status={freshness_status} (must be fresh)"
            )

chat_trace_id = extract_trace_id("/tmp/immcad_chat_headers.txt")
refusal_trace_id = extract_trace_id("/tmp/immcad_refusal_headers.txt")
cases_trace_id = extract_trace_id("/tmp/immcad_cases_headers.txt")
sources_trace_id = extract_trace_id("/tmp/immcad_sources_headers.txt")

report = {
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "environment": os.getenv("ENVIRONMENT", "unknown"),
    "contracts": {
        "chat_submit": "passed",
        "policy_refusal": "passed",
        "citation_display": "passed",
        "case_search": "passed",
        "source_transparency": "passed",
    },
    "trace_ids": {
        "chat_submit": chat_trace_id,
        "policy_refusal": refusal_trace_id,
        "case_search": cases_trace_id,
        "source_transparency": sources_trace_id,
    },
    "counts": {
        "chat_citations": len(chat["citations"]),
        "case_results": len(cases["results"]),
        "source_rows": len(sources.get("case_law_sources", [])),
    },
}

report_path = os.environ["STAGING_SMOKE_REPORT_PATH"]
with open(report_path, "w", encoding="utf-8") as handle:
    json.dump(report, handle, indent=2)
    handle.write("\n")

print(
    "[OK] Trace IDs captured for staging smoke:"
    f" chat={chat_trace_id}, refusal={refusal_trace_id},"
    f" cases={cases_trace_id}, sources={sources_trace_id}"
)
print(f"[OK] Smoke report written to {report_path}")
PY

echo "[OK] API smoke tests passed."
