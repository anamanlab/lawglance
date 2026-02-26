#!/usr/bin/env bash
set -euo pipefail

API_BASE_URL="${IMMCAD_API_BASE_URL:-}"
FRONTEND_URL="${IMMCAD_FRONTEND_URL:-https://immcad.arkiteto.dpdns.org}"
TOKEN="${IMMCAD_API_BEARER_TOKEN:-${API_BEARER_TOKEN:-}}"

if [[ -z "${API_BASE_URL}" ]]; then
  echo "[ERROR] IMMCAD_API_BASE_URL is required."
  echo "Example: IMMCAD_API_BASE_URL=https://immcad-api.arkiteto.dpdns.org make free-tier-runtime-validate"
  exit 1
fi
if [[ -z "${TOKEN}" ]]; then
  echo "[ERROR] IMMCAD_API_BEARER_TOKEN (or API_BEARER_TOKEN) is required."
  exit 1
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "[1/5] Backend health check"
health_payload="$(curl -fsS "${API_BASE_URL%/}/healthz")"
python3 - <<'PY' "${health_payload}"
import json
import sys

payload = json.loads(sys.argv[1])
if payload.get("status") != "ok":
    raise SystemExit("[ERROR] Backend health payload is not ok.")
print("[OK] Backend health payload is ok.")
PY

echo "[2/5] Frontend case-search smoke"
search_payload="$(curl -fsS -X POST "${FRONTEND_URL%/}/api/search/cases" \
  -H 'content-type: application/json' \
  -d '{"query":"IRPA procedural fairness inadmissibility","top_k":3}')"
python3 - <<'PY' "${search_payload}"
import json
import sys

payload = json.loads(sys.argv[1])
results = payload.get("results")
if not isinstance(results, list) or not results:
    raise SystemExit("[ERROR] Case-search smoke returned no results.")
first = results[0]
if str(first.get("title", "")).startswith("Scaffold Case"):
    raise SystemExit("[ERROR] Case-search smoke returned scaffold result.")
print(f"[OK] Case-search smoke passed. results={len(results)} first_source={first.get('source_id')}")
PY

echo "[3/5] Chat case-law smoke"
IMMCAD_API_BASE_URL="${API_BASE_URL}" \
IMMCAD_API_BEARER_TOKEN="${TOKEN}" \
bash "${ROOT_DIR}/scripts/run_chat_case_law_tool_smoke.sh"

echo "[4/5] Lawyer research smoke"
lawyer_payload="$(curl -fsS -X POST "${API_BASE_URL%/}/api/research/lawyer-cases" \
  -H 'content-type: application/json' \
  -H "authorization: Bearer ${TOKEN}" \
  -d '{"session_id":"free-tier-runtime-validate","matter_summary":"Federal Court procedural fairness inadmissibility appeal decision","jurisdiction":"ca","court":"fc","limit":1}')"
python3 - <<'PY' "${lawyer_payload}"
import json
import sys

payload = json.loads(sys.argv[1])
cases = payload.get("cases")
if not isinstance(cases, list) or not cases:
    raise SystemExit("[ERROR] Lawyer-research smoke returned no cases.")
first = cases[0]
if first.get("source_id") not in {"FC_DECISIONS", "FCA_DECISIONS", "SCC_DECISIONS", "CANLII_CASE_BROWSE", "CANLII_CASE_CITATOR"}:
    raise SystemExit("[ERROR] Lawyer-research smoke returned unexpected source.")
print(
    "[OK] Lawyer-research smoke passed. "
    f"source={first.get('source_id')} "
    f"pdf_status={first.get('pdf_status')} "
    f"export_allowed={first.get('export_allowed')}"
)
PY

echo "[5/5] CanLII live smoke"
IMMCAD_API_BASE_URL="${API_BASE_URL}" \
IMMCAD_API_BEARER_TOKEN="${TOKEN}" \
bash "${ROOT_DIR}/scripts/run_canlii_live_smoke.sh"

echo "[OK] Free-tier runtime validation passed."
