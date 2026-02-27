#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Run a Vercel-free Cloudflare backend bridge:
  local uvicorn backend -> Cloudflare Quick Tunnel -> Cloudflare backend proxy Worker

Usage:
  scripts/run_cloudflare_quick_tunnel_bridge.sh [options]

Options:
  --env-file PATH          Env file to source (default: ops/runtime/.env.backend-origin)
  --host HOST              Local backend bind host (default: 127.0.0.1)
  --port PORT              Local backend port (default: 8001)
  --state-dir PATH         Runtime state/log directory (default: /tmp/immcad-cloudflare-bridge)
  --cloudflared-bin PATH   cloudflared binary (default: ~/bin/cloudflared or PATH)
  --detach-mode MODE       Process detach mode: auto|setsid|nohup (default: auto)
  --skip-deploy            Start backend+tunnel but do not redeploy Cloudflare backend proxy
  --skip-smoke             Skip post-deploy smoke checks
  --help                   Show help

Environment overrides:
  BACKEND_PROXY_WORKER_URL         (default: https://immcad-api.arkiteto.dpdns.org)
  FRONTEND_URL                     (default: https://immcad.arkiteto.dpdns.org)
  BACKEND_REQUEST_TIMEOUT_MS       (default: 15000)
  BACKEND_RETRY_ATTEMPTS           (default: 1)
  WRANGLER_CONFIG_PATH             (default: backend-cloudflare/wrangler.backend-proxy.jsonc)
  IMMCAD_API_BEARER_TOKEN / API_BEARER_TOKEN (optional; enables authenticated lawyer-research smoke)
EOF
}

require_option_value() {
  local option_name="$1"
  local option_value="${2-}"
  if [ -z "$option_value" ] || [[ "$option_value" == --* ]]; then
    echo "ERROR: ${option_name} requires a value." >&2
    usage >&2
    exit 1
  fi
}

port_is_listening() {
  local port="$1"
  if command -v ss >/dev/null 2>&1; then
    ss -ltn "( sport = :${port} )" | tail -n +2 | grep -q .
    return $?
  fi

  if command -v lsof >/dev/null 2>&1; then
    lsof -nP -iTCP:"${port}" -sTCP:LISTEN >/dev/null 2>&1
    return $?
  fi

  echo "ERROR: neither ss nor lsof is available; cannot verify whether port ${port} is free." >&2
  exit 1
}

cleanup_on_error() {
  local exit_code="$?"
  if [ "$exit_code" -eq 0 ]; then
    return
  fi
  echo "[cleanup] Script failed (exit=${exit_code}). Stopping bridge processes started in this run..." >&2
  if [ -n "${CF_PID:-}" ] && kill -0 "${CF_PID}" 2>/dev/null; then
    kill "${CF_PID}" 2>/dev/null || true
  fi
  if [ -n "${UVI_PID:-}" ] && kill -0 "${UVI_PID}" 2>/dev/null; then
    kill "${UVI_PID}" 2>/dev/null || true
  fi
}
trap cleanup_on_error EXIT

resolve_detach_mode() {
  local requested="${1:-auto}"
  case "$requested" in
    auto)
      if command -v setsid >/dev/null 2>&1; then
        echo "setsid"
      else
        echo "nohup"
      fi
      ;;
    setsid|nohup)
      if [ "$requested" = "setsid" ] && ! command -v setsid >/dev/null 2>&1; then
        echo "ERROR: --detach-mode setsid requested but 'setsid' was not found" >&2
        return 1
      fi
      echo "$requested"
      ;;
    *)
      echo "ERROR: Invalid --detach-mode '$requested' (expected: auto|setsid|nohup)" >&2
      return 1
      ;;
  esac
}

spawn_detached() {
  local pid_file="$1"
  local log_file="$2"
  shift 2

  case "${BRIDGE_DETACH_MODE_RESOLVED:-nohup}" in
    setsid)
      nohup setsid "$@" >"$log_file" 2>&1 < /dev/null &
      ;;
    nohup)
      nohup "$@" >"$log_file" 2>&1 < /dev/null &
      ;;
    *)
      echo "ERROR: Unsupported detach mode '${BRIDGE_DETACH_MODE_RESOLVED:-}'" >&2
      return 1
      ;;
  esac

  echo "$!" > "$pid_file"
}

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ROOT_DIR}/ops/runtime/.env.backend-origin"
BACKEND_HOST="127.0.0.1"
BACKEND_PORT="8001"
STATE_DIR="/tmp/immcad-cloudflare-bridge"
BRIDGE_DETACH_MODE="${BRIDGE_DETACH_MODE:-auto}"
SKIP_DEPLOY="0"
SKIP_SMOKE="0"

while [ "$#" -gt 0 ]; do
  case "$1" in
    --env-file)
      require_option_value "$1" "${2-}"
      ENV_FILE="$2"
      shift 2
      ;;
    --host)
      require_option_value "$1" "${2-}"
      BACKEND_HOST="$2"
      shift 2
      ;;
    --port)
      require_option_value "$1" "${2-}"
      BACKEND_PORT="$2"
      shift 2
      ;;
    --state-dir)
      require_option_value "$1" "${2-}"
      STATE_DIR="$2"
      shift 2
      ;;
    --cloudflared-bin)
      require_option_value "$1" "${2-}"
      export CLOUDFLARED_BIN="$2"
      shift 2
      ;;
    --detach-mode)
      require_option_value "$1" "${2-}"
      BRIDGE_DETACH_MODE="$2"
      shift 2
      ;;
    --skip-deploy)
      SKIP_DEPLOY="1"
      shift
      ;;
    --skip-smoke)
      SKIP_SMOKE="1"
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

if [ ! -f "$ENV_FILE" ]; then
  echo "ERROR: Env file not found: $ENV_FILE" >&2
  exit 1
fi

if ! [[ "$BACKEND_PORT" =~ ^[0-9]+$ ]]; then
  echo "ERROR: --port must be numeric" >&2
  exit 1
fi

BRIDGE_DETACH_MODE_RESOLVED="$(resolve_detach_mode "$BRIDGE_DETACH_MODE")"

CLOUDFLARED_BIN="${CLOUDFLARED_BIN:-}"
if [ -z "$CLOUDFLARED_BIN" ]; then
  if [ -x "$HOME/bin/cloudflared" ]; then
    CLOUDFLARED_BIN="$HOME/bin/cloudflared"
  else
    CLOUDFLARED_BIN="$(command -v cloudflared || true)"
  fi
fi
if [ -z "${CLOUDFLARED_BIN:-}" ] || [ ! -x "$CLOUDFLARED_BIN" ]; then
  echo "ERROR: cloudflared not found. Install it or pass --cloudflared-bin." >&2
  exit 1
fi

command -v curl >/dev/null 2>&1 || { echo "ERROR: curl not found" >&2; exit 1; }
command -v npx >/dev/null 2>&1 || { echo "ERROR: npx not found" >&2; exit 1; }

mkdir -p "$STATE_DIR"
chmod 700 "$STATE_DIR"

UVI_LOG="$STATE_DIR/uvicorn.log"
CF_LOG="$STATE_DIR/cloudflared.log"
DEPLOY_LOG="$STATE_DIR/wrangler-deploy.log"
STATE_ENV="$STATE_DIR/state.env"

if port_is_listening "$BACKEND_PORT"; then
  echo "ERROR: Port ${BACKEND_PORT} is already in use. Stop the existing backend or choose another --port." >&2
  exit 1
fi

echo "[1/6] Starting local backend on ${BACKEND_HOST}:${BACKEND_PORT} ..."
echo "      detach mode: ${BRIDGE_DETACH_MODE_RESOLVED}"
(
  cd "$ROOT_DIR"
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  export ENABLE_CASE_SEARCH=true
  set +a
  spawn_detached \
    "$STATE_DIR/uvicorn.pid" \
    "$UVI_LOG" \
    ./scripts/venv_exec.sh uvicorn immcad_api.main:app --app-dir src --host "$BACKEND_HOST" --port "$BACKEND_PORT"
)

UVI_PID="$(cat "$STATE_DIR/uvicorn.pid")"
for _ in $(seq 1 30); do
  if curl -fsS "http://${BACKEND_HOST}:${BACKEND_PORT}/healthz" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done
if ! curl -fsS "http://${BACKEND_HOST}:${BACKEND_PORT}/healthz" >/dev/null 2>&1; then
  echo "ERROR: Local backend failed health check. See $UVI_LOG" >&2
  exit 1
fi

echo "[2/6] Starting Cloudflare Quick Tunnel ..."
spawn_detached \
  "$STATE_DIR/cloudflared.pid" \
  "$CF_LOG" \
  "$CLOUDFLARED_BIN" tunnel --url "http://${BACKEND_HOST}:${BACKEND_PORT}" --no-autoupdate
CF_PID="$(cat "$STATE_DIR/cloudflared.pid")"

QUICK_TUNNEL_URL=""
for _ in $(seq 1 45); do
  QUICK_TUNNEL_URL="$(grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' "$CF_LOG" | tail -n 1 || true)"
  if [ -n "$QUICK_TUNNEL_URL" ]; then
    break
  fi
  sleep 1
done
if [ -z "$QUICK_TUNNEL_URL" ]; then
  echo "ERROR: Failed to obtain Quick Tunnel URL. See $CF_LOG" >&2
  exit 1
fi

echo "[3/6] Validating Quick Tunnel health ..."
quick_tunnel_health_ok="0"
quick_tunnel_connector_ok="0"
for attempt in $(seq 1 30); do
  if curl -fsS --max-time 2 "${QUICK_TUNNEL_URL}/healthz" >/dev/null 2>&1; then
    quick_tunnel_health_ok="1"
    break
  fi
  if [ "$attempt" -ge 8 ] && grep -q "Registered tunnel connection" "$CF_LOG"; then
    quick_tunnel_connector_ok="1"
    break
  fi
  sleep 1
done
if [ "$quick_tunnel_health_ok" != "1" ]; then
  if [ "$quick_tunnel_connector_ok" = "1" ] || grep -q "Registered tunnel connection" "$CF_LOG"; then
    echo "[warn] Quick Tunnel URL was not locally reachable after waiting (likely local resolver lag), but cloudflared reports a registered tunnel connection. Continuing to Cloudflare-side deploy + smoke checks."
  else
    echo "ERROR: Quick Tunnel health check failed after waiting and no registered tunnel connection was observed. See $CF_LOG" >&2
    exit 1
  fi
fi

BACKEND_REQUEST_TIMEOUT_MS="${BACKEND_REQUEST_TIMEOUT_MS:-15000}"
BACKEND_RETRY_ATTEMPTS="${BACKEND_RETRY_ATTEMPTS:-1}"
WRANGLER_CONFIG_PATH="${WRANGLER_CONFIG_PATH:-backend-cloudflare/wrangler.backend-proxy.jsonc}"
BACKEND_PROXY_WORKER_URL="${BACKEND_PROXY_WORKER_URL:-https://immcad-api.arkiteto.dpdns.org}"
FRONTEND_URL="${FRONTEND_URL:-https://immcad.arkiteto.dpdns.org}"

if [ "$SKIP_DEPLOY" != "1" ]; then
  echo "[4/6] Redeploying Cloudflare backend proxy to Quick Tunnel origin ..."
  (
    cd "$ROOT_DIR"
    npx --yes wrangler@4.68.1 deploy \
      --config "$WRANGLER_CONFIG_PATH" \
      --var "BACKEND_ORIGIN:${QUICK_TUNNEL_URL}" \
      --var "BACKEND_REQUEST_TIMEOUT_MS:${BACKEND_REQUEST_TIMEOUT_MS}" \
      --var "BACKEND_RETRY_ATTEMPTS:${BACKEND_RETRY_ATTEMPTS}" \
      --keep-vars
  ) | tee "$DEPLOY_LOG"
else
  echo "[4/6] Skipping backend proxy redeploy (--skip-deploy)"
  : > "$DEPLOY_LOG"
fi

PROXY_VERSION_ID="$(grep -oE 'Current Version ID: [a-f0-9-]+' "$DEPLOY_LOG" | awk '{print $4}' | tail -n 1 || true)"

if [ "$SKIP_SMOKE" != "1" ] && [ "$SKIP_DEPLOY" != "1" ]; then
  echo "[5/6] Running live smoke checks on Cloudflare custom domains ..."
  curl -fsS "${BACKEND_PROXY_WORKER_URL}/healthz" >/dev/null
  curl -fsS -X POST "${FRONTEND_URL}/api/search/cases" \
    -H 'content-type: application/json' \
    --data '{"query":"Express Entry procedural fairness","jurisdiction":"ca"}' >/dev/null

  bearer="${IMMCAD_API_BEARER_TOKEN:-${API_BEARER_TOKEN:-}}"
  if [ -n "$bearer" ]; then
    curl -fsS -X POST "${BACKEND_PROXY_WORKER_URL}/api/research/lawyer-cases" \
      -H 'content-type: application/json' \
      -H "authorization: Bearer ${bearer}" \
      --data '{"session_id":"bridge-smoke","matter_summary":"Federal Court appeal on procedural fairness"}' >/dev/null
  else
    echo "[5/6] Skipping authenticated lawyer-research smoke (no bearer token in environment)."
  fi
else
  echo "[5/6] Skipping smoke checks (--skip-smoke or --skip-deploy)"
fi

cat > "$STATE_ENV" <<EOF
BRIDGE_STARTED_AT_UTC=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
BACKEND_HOST=${BACKEND_HOST}
BACKEND_PORT=${BACKEND_PORT}
BRIDGE_DETACH_MODE_REQUESTED=${BRIDGE_DETACH_MODE}
BRIDGE_DETACH_MODE_RESOLVED=${BRIDGE_DETACH_MODE_RESOLVED}
UVI_PID=${UVI_PID}
CF_PID=${CF_PID}
QUICK_TUNNEL_URL=${QUICK_TUNNEL_URL}
BACKEND_PROXY_WORKER_URL=${BACKEND_PROXY_WORKER_URL}
FRONTEND_URL=${FRONTEND_URL}
BACKEND_PROXY_VERSION_ID=${PROXY_VERSION_ID}
ENV_FILE=${ENV_FILE}
EOF
chmod 600 "$STATE_ENV"

echo "[6/6] Bridge ready"
echo "  state_file: $STATE_ENV"
echo "  quick_tunnel: $QUICK_TUNNEL_URL"
if [ -n "$PROXY_VERSION_ID" ]; then
  echo "  backend_proxy_version: $PROXY_VERSION_ID"
fi
echo "  uvicorn_pid: $UVI_PID"
echo "  cloudflared_pid: $CF_PID"
echo "  logs: $UVI_LOG | $CF_LOG | $DEPLOY_LOG"

trap - EXIT
