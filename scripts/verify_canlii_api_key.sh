#!/usr/bin/env bash
set -euo pipefail

CANLII_BASE_URL="${CANLII_BASE_URL:-https://api.canlii.org/v1}"
CANLII_API_KEY="${CANLII_API_KEY:-}"
TIMEOUT_SECONDS="${CANLII_KEY_VERIFY_TIMEOUT_SECONDS:-12}"

if [[ -z "${CANLII_API_KEY}" ]]; then
  echo "[ERROR] CANLII_API_KEY is not set."
  echo "Set CANLII_API_KEY and rerun: CANLII_API_KEY=*** make canlii-key-verify"
  exit 1
fi

TMP_HEADERS="$(mktemp /tmp/canlii-key-headers.XXXXXX)"
TMP_BODY="$(mktemp /tmp/canlii-key-body.XXXXXX)"
trap 'rm -f "${TMP_HEADERS}" "${TMP_BODY}"' EXIT

status_code="$(
  curl -sS \
    --max-time "${TIMEOUT_SECONDS}" \
    --get \
    --data-urlencode "api_key=${CANLII_API_KEY}" \
    -D "${TMP_HEADERS}" \
    -o "${TMP_BODY}" \
    -w "%{http_code}" \
    "${CANLII_BASE_URL%/}/caseBrowse/en/"
)"

if [[ "${status_code}" != "200" ]]; then
  echo "[ERROR] CanLII key verification failed with HTTP ${status_code}."
  echo "[DEBUG] Response body:"
  cat "${TMP_BODY}"
  exit 1
fi

python3 - <<'PY' "${TMP_BODY}"
import json
import sys

path = sys.argv[1]
with open(path, "r", encoding="utf-8") as handle:
    payload = json.load(handle)

databases = payload.get("caseDatabases")
if not isinstance(databases, list) or not databases:
    raise SystemExit("[ERROR] CanLII key verification response missing caseDatabases list.")

print(f"[OK] CanLII API key verified. caseDatabases returned: {len(databases)}")
PY
