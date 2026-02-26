#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Validate the active Cloudflare Quick Tunnel bridge runtime.

Usage:
  scripts/check_cloudflare_quick_bridge_health.sh [options]

Options:
  --state-dir PATH      Bridge state dir (default: /tmp/immcad-cloudflare-bridge-managed)
  --with-search         Also run a lightweight frontend case-search smoke
  --help                Show help
EOF
}

STATE_DIR="/tmp/immcad-cloudflare-bridge-managed"
WITH_SEARCH="0"

while [ "$#" -gt 0 ]; do
  case "$1" in
    --state-dir)
      shift
      if [ "$#" -eq 0 ] || [[ "$1" == --* ]]; then
        echo "ERROR: --state-dir requires a value" >&2
        usage >&2
        exit 1
      fi
      STATE_DIR="$1"
      shift
      ;;
    --with-search)
      WITH_SEARCH="1"
      shift
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      echo "ERROR: Unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

STATE_ENV="${STATE_DIR}/state.env"
if [ ! -f "$STATE_ENV" ]; then
  echo "ERROR: Bridge state file not found: $STATE_ENV" >&2
  exit 1
fi

set -a
# shellcheck disable=SC1090
source "$STATE_ENV"
set +a

require_var() {
  local name="$1"
  local value="${!name-}"
  if [ -z "$value" ]; then
    echo "ERROR: Missing required state variable: $name" >&2
    exit 1
  fi
}

for v in BACKEND_HOST BACKEND_PORT UVI_PID CF_PID BACKEND_PROXY_WORKER_URL FRONTEND_URL QUICK_TUNNEL_URL; do
  require_var "$v"
done

check_pid() {
  local pid="$1"
  local label="$2"
  if ! kill -0 "$pid" 2>/dev/null; then
    echo "ERROR: ${label} process is not running (pid=${pid})" >&2
    exit 1
  fi
}

check_pid "$UVI_PID" "uvicorn"
check_pid "$CF_PID" "cloudflared"

curl -fsS --max-time 3 "http://${BACKEND_HOST}:${BACKEND_PORT}/healthz" >/dev/null
curl -fsS --max-time 5 "${BACKEND_PROXY_WORKER_URL}/healthz" >/dev/null

if [ "$WITH_SEARCH" = "1" ]; then
  curl -fsS --max-time 8 -X POST "${FRONTEND_URL}/api/search/cases" \
    -H 'content-type: application/json' \
    --data '{"query":"IRPA procedural fairness", "top_k": 1}' >/dev/null
fi

echo "OK: Cloudflare quick bridge healthy"
echo "  state_file: ${STATE_ENV}"
echo "  quick_tunnel: ${QUICK_TUNNEL_URL}"
echo "  uvicorn_pid: ${UVI_PID}"
echo "  cloudflared_pid: ${CF_PID}"
echo "  backend_proxy_url: ${BACKEND_PROXY_WORKER_URL}"
