#!/usr/bin/env bash
set -euo pipefail

STATE_DIR="${STATE_DIR:-/tmp/immcad-codespace-named-origin}"
WITH_SEARCH="${WITH_SEARCH:-0}"
WITH_CHAT_CASE_LAW="${WITH_CHAT_CASE_LAW:-0}"
WITH_CANLII="${WITH_CANLII:-0}"

usage() {
  cat <<'EOF'
Validate health for the Codespaces-managed named-tunnel runtime.

Usage:
  scripts/check_cloudflare_named_tunnel_codespace_runtime_health.sh [options]

Options:
  --state-dir PATH      Runtime state directory (default: /tmp/immcad-codespace-named-origin)
  --with-search         Also run frontend case-search smoke
  --with-chat-case-law  Also run chat case-law smoke (requires bearer token in env file)
  --with-canlii         Also run CanLII live smoke (requires bearer token in env file)
  --help                Show help
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --state-dir)
      shift; STATE_DIR="${1:-}" ;;
    --with-search)
      WITH_SEARCH="1" ;;
    --with-chat-case-law)
      WITH_CHAT_CASE_LAW="1" ;;
    --with-canlii)
      WITH_CANLII="1" ;;
    --help|-h)
      usage
      exit 0 ;;
    *)
      echo "ERROR: Unknown argument: $1" >&2
      usage >&2
      exit 1 ;;
  esac
  shift || true
done

require_file() {
  local path="$1"
  if [ ! -f "$path" ]; then
    echo "ERROR: required file not found: $path" >&2
    exit 1
  fi
}

require_cmd() {
  local cmd="$1"
  command -v "$cmd" >/dev/null 2>&1 || {
    echo "ERROR: required command not found: $cmd" >&2
    exit 1
  }
}

require_cmd curl

STATE_ENV="${STATE_DIR}/state.env"
BACKEND_PID_FILE="${STATE_DIR}/backend.pid"
TUNNEL_PID_FILE="${STATE_DIR}/cloudflared.pid"
require_file "$STATE_ENV"
require_file "$BACKEND_PID_FILE"
require_file "$TUNNEL_PID_FILE"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

set -a
# shellcheck disable=SC1090
source "$STATE_ENV"
set +a

BACKEND_PID="${BACKEND_PID:-$(cat "$BACKEND_PID_FILE" 2>/dev/null || true)}"
CLOUDFLARED_PID="${CLOUDFLARED_PID:-$(cat "$TUNNEL_PID_FILE" 2>/dev/null || true)}"
BACKEND_HOST="${BACKEND_HOST:-127.0.0.1}"
BACKEND_PORT="${BACKEND_PORT:-8002}"
API_BASE_URL="${API_BASE_URL:-https://immcad-api.arkiteto.dpdns.org}"
FRONTEND_URL="${FRONTEND_URL:-https://immcad.arkiteto.dpdns.org}"
ENV_FILE="${ENV_FILE:-${ROOT_DIR}/backend-vercel/.env.production.vercel}"

if ! kill -0 "${BACKEND_PID}" 2>/dev/null; then
  echo "ERROR: backend pid is not running: ${BACKEND_PID}" >&2
  exit 1
fi
if ! kill -0 "${CLOUDFLARED_PID}" 2>/dev/null; then
  echo "ERROR: cloudflared pid is not running: ${CLOUDFLARED_PID}" >&2
  exit 1
fi

curl -fsS --max-time 5 "http://${BACKEND_HOST}:${BACKEND_PORT}/healthz" >/dev/null
curl -fsS --max-time 8 "${API_BASE_URL%/}/healthz" >/dev/null

if [ "$WITH_SEARCH" = "1" ]; then
  curl -fsS --max-time 10 -X POST "${FRONTEND_URL%/}/api/search/cases" \
    -H 'content-type: application/json' \
    --data '{"query":"IRPA procedural fairness inadmissibility","top_k":1}' >/dev/null
fi

if [ "$WITH_CHAT_CASE_LAW" = "1" ] || [ "$WITH_CANLII" = "1" ]; then
  require_file "${ENV_FILE}"
  set -a
  # shellcheck disable=SC1090
  source "${ENV_FILE}"
  set +a
  token="${IMMCAD_API_BEARER_TOKEN:-${API_BEARER_TOKEN:-}}"
  if [ -z "${token:-}" ]; then
    echo "ERROR: bearer token missing in env file: ${ENV_FILE}" >&2
    exit 1
  fi
fi

if [ "$WITH_CHAT_CASE_LAW" = "1" ]; then
  IMMCAD_API_BASE_URL="${API_BASE_URL}" \
  IMMCAD_API_BEARER_TOKEN="${token}" \
  bash "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/run_chat_case_law_tool_smoke.sh" >/dev/null
fi

if [ "$WITH_CANLII" = "1" ]; then
  IMMCAD_API_BASE_URL="${API_BASE_URL}" \
  IMMCAD_API_BEARER_TOKEN="${token}" \
  bash "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/run_canlii_live_smoke.sh" >/dev/null
fi

echo "OK: Codespaces named-tunnel runtime healthy"
echo "  state_dir: ${STATE_DIR}"
echo "  backend_pid: ${BACKEND_PID}"
echo "  cloudflared_pid: ${CLOUDFLARED_PID}"
echo "  api_base_url: ${API_BASE_URL}"
echo "  frontend_url: ${FRONTEND_URL}"
