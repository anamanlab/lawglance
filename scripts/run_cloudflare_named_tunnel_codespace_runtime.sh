#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Start a repeatable Codespaces-hosted IMMCAD backend runtime behind an existing
Cloudflare named tunnel token.

This script launches:
  - local backend: uvicorn on 127.0.0.1:8002
  - named tunnel connector: cloudflared tunnel run --token-file ...

It writes PID/log/state files under /tmp by default and can run smoke checks.

Usage:
  scripts/run_cloudflare_named_tunnel_codespace_runtime.sh [options]

Options:
  --state-dir PATH       Runtime state directory (default: /tmp/immcad-codespace-named-origin)
  --env-file PATH        Backend env file (default: backend-vercel/.env.production.vercel)
  --token-file PATH      cloudflared token file (default: /tmp/immcad_named_tunnel.token)
  --backend-host HOST    Backend host bind (default: 127.0.0.1)
  --backend-port PORT    Backend port bind (default: 8002)
  --api-base-url URL     Public API base URL (default: https://immcad-api.arkiteto.dpdns.org)
  --frontend-url URL     Public frontend URL (default: https://immcad.arkiteto.dpdns.org)
  --skip-smoke           Skip post-start smoke checks
  --force-restart        Stop existing tracked runtime before start
  --help                 Show help
EOF
}

require_cmd() {
  local cmd="$1"
  command -v "$cmd" >/dev/null 2>&1 || {
    echo "ERROR: Required command not found: $cmd" >&2
    exit 1
  }
}

is_running_pid() {
  local pid="${1:-}"
  [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null
}

stop_pid_file() {
  local pid_file="$1"
  local label="$2"
  if [ ! -f "$pid_file" ]; then
    return 0
  fi
  local pid
  pid="$(cat "$pid_file" 2>/dev/null || true)"
  if ! is_running_pid "$pid"; then
    rm -f "$pid_file"
    return 0
  fi
  echo "[stop] ${label} pid=${pid}"
  kill "$pid" 2>/dev/null || true
  for _ in $(seq 1 10); do
    if ! is_running_pid "$pid"; then
      rm -f "$pid_file"
      return 0
    fi
    sleep 1
  done
  echo "[kill] ${label} pid=${pid}"
  kill -9 "$pid" 2>/dev/null || true
  rm -f "$pid_file"
}

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATE_DIR="/tmp/immcad-codespace-named-origin"
ENV_FILE="${ROOT_DIR}/backend-vercel/.env.production.vercel"
TOKEN_FILE="/tmp/immcad_named_tunnel.token"
BACKEND_HOST="127.0.0.1"
BACKEND_PORT="8002"
API_BASE_URL="https://immcad-api.arkiteto.dpdns.org"
FRONTEND_URL="https://immcad.arkiteto.dpdns.org"
SKIP_SMOKE="0"
FORCE_RESTART="0"

while [ "$#" -gt 0 ]; do
  case "$1" in
    --state-dir)
      shift; STATE_DIR="${1:-}" ;;
    --env-file)
      shift; ENV_FILE="${1:-}" ;;
    --token-file)
      shift; TOKEN_FILE="${1:-}" ;;
    --backend-host)
      shift; BACKEND_HOST="${1:-}" ;;
    --backend-port)
      shift; BACKEND_PORT="${1:-}" ;;
    --api-base-url)
      shift; API_BASE_URL="${1:-}" ;;
    --frontend-url)
      shift; FRONTEND_URL="${1:-}" ;;
    --skip-smoke)
      SKIP_SMOKE="1" ;;
    --force-restart)
      FORCE_RESTART="1" ;;
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

require_cmd bash
require_cmd curl
require_cmd cloudflared
require_cmd setsid
require_cmd nohup
require_cmd ss

if [ ! -f "$ENV_FILE" ]; then
  echo "ERROR: env file not found: $ENV_FILE" >&2
  exit 1
fi
if [ ! -f "$TOKEN_FILE" ]; then
  echo "ERROR: token file not found: $TOKEN_FILE" >&2
  exit 1
fi

mkdir -p "$STATE_DIR"
chmod 700 "$STATE_DIR"

BACKEND_PID_FILE="${STATE_DIR}/backend.pid"
TUNNEL_PID_FILE="${STATE_DIR}/cloudflared.pid"
BACKEND_LOG="${STATE_DIR}/backend.log"
TUNNEL_LOG="${STATE_DIR}/cloudflared.log"
STATE_ENV="${STATE_DIR}/state.env"

existing_backend_pid="$(cat "$BACKEND_PID_FILE" 2>/dev/null || true)"
existing_tunnel_pid="$(cat "$TUNNEL_PID_FILE" 2>/dev/null || true)"

if is_running_pid "$existing_backend_pid" && is_running_pid "$existing_tunnel_pid"; then
  if [ "$FORCE_RESTART" = "1" ]; then
    stop_pid_file "$TUNNEL_PID_FILE" "cloudflared"
    stop_pid_file "$BACKEND_PID_FILE" "backend"
  else
    echo "Runtime appears to already be running."
    echo "  backend_pid=${existing_backend_pid}"
    echo "  cloudflared_pid=${existing_tunnel_pid}"
    echo "Use --force-restart to replace it."
    exit 0
  fi
fi

# Clean up stale pid files if any.
stop_pid_file "$TUNNEL_PID_FILE" "cloudflared"
stop_pid_file "$BACKEND_PID_FILE" "backend"

if ss -ltn "( sport = :${BACKEND_PORT} )" | tail -n +2 | grep -q ":${BACKEND_PORT}"; then
  echo "ERROR: backend port ${BACKEND_PORT} is already in use" >&2
  ss -ltnp "( sport = :${BACKEND_PORT} )" || true
  exit 1
fi

: > "$BACKEND_LOG"
: > "$TUNNEL_LOG"

echo "[1/4] Starting backend on ${BACKEND_HOST}:${BACKEND_PORT}"
nohup setsid env \
  ROOT_DIR="$ROOT_DIR" \
  ENV_FILE="$ENV_FILE" \
  BACKEND_HOST="$BACKEND_HOST" \
  BACKEND_PORT="$BACKEND_PORT" \
  bash -c '
    set -euo pipefail
    export PATH="$HOME/.local/bin:$PATH"
    cd "$ROOT_DIR"
    set -a
    source "$ENV_FILE"
    export ENABLE_CASE_SEARCH=true
    set +a
    exec ./scripts/venv_exec.sh uvicorn immcad_api.main:app --app-dir src --host "$BACKEND_HOST" --port "$BACKEND_PORT"
  ' >>"$BACKEND_LOG" 2>&1 < /dev/null &
echo $! > "$BACKEND_PID_FILE"

for _ in $(seq 1 45); do
  if curl -fsS --max-time 3 "http://${BACKEND_HOST}:${BACKEND_PORT}/healthz" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done
if ! curl -fsS --max-time 3 "http://${BACKEND_HOST}:${BACKEND_PORT}/healthz" >/dev/null 2>&1; then
  echo "ERROR: backend failed local health check" >&2
  tail -n 120 "$BACKEND_LOG" >&2 || true
  exit 1
fi

echo "[2/4] Starting named tunnel connector"
nohup setsid cloudflared tunnel run --token-file "$TOKEN_FILE" >>"$TUNNEL_LOG" 2>&1 < /dev/null &
echo $! > "$TUNNEL_PID_FILE"

for _ in $(seq 1 60); do
  if grep -q "Registered tunnel connection" "$TUNNEL_LOG"; then
    break
  fi
  sleep 1
done
if ! grep -q "Registered tunnel connection" "$TUNNEL_LOG"; then
  echo "ERROR: cloudflared did not register a tunnel connection" >&2
  tail -n 120 "$TUNNEL_LOG" >&2 || true
  exit 1
fi

echo "[3/4] Verifying public backend health"
for _ in $(seq 1 45); do
  if curl -fsS --max-time 5 "${API_BASE_URL%/}/healthz" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done
if ! curl -fsS --max-time 5 "${API_BASE_URL%/}/healthz" >/dev/null 2>&1; then
  echo "ERROR: public backend health check failed at ${API_BASE_URL%/}/healthz" >&2
  exit 1
fi

if [ "$SKIP_SMOKE" != "1" ]; then
  echo "[4/4] Running smoke checks"
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
  token="${IMMCAD_API_BEARER_TOKEN:-${API_BEARER_TOKEN:-}}"

  curl -fsS --max-time 10 -X POST "${FRONTEND_URL%/}/api/search/cases" \
    -H 'content-type: application/json' \
    --data '{"query":"IRPA procedural fairness inadmissibility","top_k":1}' >/dev/null

  if [ -n "${token:-}" ]; then
    IMMCAD_API_BASE_URL="${API_BASE_URL}" \
    IMMCAD_API_BEARER_TOKEN="${token}" \
    bash "${ROOT_DIR}/scripts/run_chat_case_law_tool_smoke.sh" >/dev/null

    IMMCAD_API_BASE_URL="${API_BASE_URL}" \
    IMMCAD_API_BEARER_TOKEN="${token}" \
    bash "${ROOT_DIR}/scripts/run_canlii_live_smoke.sh" >/dev/null
  else
    echo "[warn] bearer token missing in env; skipping authenticated chat/CanLII smoke checks"
  fi
else
  echo "[4/4] Skipping smoke checks (--skip-smoke)"
fi

cat > "$STATE_ENV" <<EOF
STARTED_AT_UTC=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
STATE_DIR=${STATE_DIR}
BACKEND_PID=$(cat "$BACKEND_PID_FILE")
CLOUDFLARED_PID=$(cat "$TUNNEL_PID_FILE")
BACKEND_LOG=${BACKEND_LOG}
TUNNEL_LOG=${TUNNEL_LOG}
ENV_FILE=${ENV_FILE}
TOKEN_FILE=${TOKEN_FILE}
BACKEND_HOST=${BACKEND_HOST}
BACKEND_PORT=${BACKEND_PORT}
API_BASE_URL=${API_BASE_URL}
FRONTEND_URL=${FRONTEND_URL}
EOF
chmod 600 "$STATE_ENV"

echo "DONE: Codespaces named-tunnel runtime is ready"
echo "  state_file: ${STATE_ENV}"
echo "  backend_pid: $(cat "$BACKEND_PID_FILE")"
echo "  cloudflared_pid: $(cat "$TUNNEL_PID_FILE")"
echo "  backend_log: ${BACKEND_LOG}"
echo "  tunnel_log: ${TUNNEL_LOG}"
