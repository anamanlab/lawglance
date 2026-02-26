#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

TUNNEL_ENV_SOURCE="${TUNNEL_ENV_SOURCE:-/tmp/immcad_named_tunnel.env}"
TUNNEL_TOKEN_TARGET="${TUNNEL_TOKEN_TARGET:-/etc/immcad/immcad_named_tunnel.token}"
QUICK_BRIDGE_STATE_DIR="${QUICK_BRIDGE_STATE_DIR:-/tmp/immcad-cloudflare-bridge-managed}"
NAMED_TUNNEL_STATE_DIR="${NAMED_TUNNEL_STATE_DIR:-/tmp/immcad-named-tunnel-managed}"
SKIP_SEARCH_SMOKE="0"
KEEP_QUICK_FALLBACK="0"

usage() {
  cat <<'EOF'
Install and switch IMMCAD Cloudflare backend origin to systemd-managed services.

This installs and enables:
  - immcad-backend-local.service
  - immcad-cloudflared-named-tunnel.service
  - immcad-cloudflare-origin-stack.target

It also writes the named tunnel token to a persistent locked-down token file
owned by the runtime user (`ec2-user`) so cloudflared can read it without
exposing the token in process arguments.

Usage:
  scripts/install_cloudflare_named_tunnel_systemd_stack.sh [options]

Options:
  --tunnel-env-source PATH   Source env file with TUNNEL_TOKEN (default: /tmp/immcad_named_tunnel.env)
  --skip-search-smoke        Skip frontend case-search smoke after switchover
  --keep-quick-fallback      Keep the detached Quick Tunnel bridge running (default: stop it)
  --help                     Show help
EOF
}

require_arg() {
  local name="$1"
  local value="${2-}"
  if [ -z "$value" ] || [[ "$value" == --* ]]; then
    echo "ERROR: ${name} requires a value" >&2
    usage >&2
    exit 1
  fi
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --tunnel-env-source)
      require_arg "$1" "${2-}"
      TUNNEL_ENV_SOURCE="$2"
      shift 2
      ;;
    --skip-search-smoke)
      SKIP_SEARCH_SMOKE="1"
      shift
      ;;
    --keep-quick-fallback)
      KEEP_QUICK_FALLBACK="1"
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

command -v sudo >/dev/null 2>&1 || { echo "ERROR: sudo not found" >&2; exit 1; }
command -v curl >/dev/null 2>&1 || { echo "ERROR: curl not found" >&2; exit 1; }

check_public_backend_health() {
  for _ in $(seq 1 4); do
    if curl -fsS --max-time 12 "https://immcad-api.arkiteto.dpdns.org/healthz" >/dev/null 2>&1; then
      return 0
    fi
    sleep 2
  done
  return 1
}

if [ ! -f "$TUNNEL_ENV_SOURCE" ]; then
  echo "ERROR: Named tunnel env file not found: $TUNNEL_ENV_SOURCE" >&2
  exit 1
fi
if ! grep -q '^TUNNEL_TOKEN=' "$TUNNEL_ENV_SOURCE"; then
  echo "ERROR: $TUNNEL_ENV_SOURCE does not contain TUNNEL_TOKEN=" >&2
  exit 1
fi
if [ ! -f "$ROOT_DIR/backend-vercel/.env.production.vercel" ]; then
  echo "ERROR: Backend env file missing: $ROOT_DIR/backend-vercel/.env.production.vercel" >&2
  exit 1
fi
if [ ! -x "$ROOT_DIR/scripts/venv_exec.sh" ]; then
  echo "ERROR: Missing executable helper: $ROOT_DIR/scripts/venv_exec.sh" >&2
  exit 1
fi
if [ ! -x "/home/ec2-user/bin/cloudflared" ]; then
  echo "ERROR: cloudflared not found at /home/ec2-user/bin/cloudflared" >&2
  exit 1
fi

echo "[1/8] Preflight checks"
curl -fsS --max-time 5 "http://127.0.0.1:8002/healthz" >/dev/null
check_public_backend_health

echo "[2/8] Installing persistent named tunnel token file (locked down, runtime-user readable)"
sudo install -d -m 755 /etc/immcad
tmp_token_file="$(mktemp)"
cleanup_tmp_token() {
  rm -f "$tmp_token_file"
}
trap cleanup_tmp_token EXIT
(
  set -a
  # shellcheck disable=SC1090
  source "$TUNNEL_ENV_SOURCE"
  set +a
  if [ -z "${TUNNEL_TOKEN:-}" ]; then
    echo "ERROR: TUNNEL_TOKEN missing after sourcing $TUNNEL_ENV_SOURCE" >&2
    exit 1
  fi
  printf '%s' "$TUNNEL_TOKEN" > "$tmp_token_file"
)
sudo install -m 600 -o ec2-user -g ec2-user "$tmp_token_file" "$TUNNEL_TOKEN_TARGET"
sudo rm -f /etc/immcad/immcad_named_tunnel.env
cleanup_tmp_token
trap - EXIT

echo "[3/8] Installing systemd units"
sudo install -m 644 "$ROOT_DIR/ops/systemd/immcad-backend-local.service" /etc/systemd/system/immcad-backend-local.service
sudo install -m 644 "$ROOT_DIR/ops/systemd/immcad-cloudflared-named-tunnel.service" /etc/systemd/system/immcad-cloudflared-named-tunnel.service
sudo install -m 644 "$ROOT_DIR/ops/systemd/immcad-cloudflare-origin-stack.target" /etc/systemd/system/immcad-cloudflare-origin-stack.target
sudo systemctl daemon-reload

echo "[4/8] Enabling systemd units"
sudo systemctl enable immcad-backend-local.service immcad-cloudflared-named-tunnel.service immcad-cloudflare-origin-stack.target >/dev/null

echo "[5/8] Starting named tunnel connector service (can run alongside detached connector during switchover)"
sudo systemctl restart immcad-cloudflared-named-tunnel.service
sudo systemctl is-active --quiet immcad-cloudflared-named-tunnel.service

if [ "$KEEP_QUICK_FALLBACK" != "1" ]; then
  echo "[6/8] Switchover backend process to systemd and retire detached Quick Tunnel bridge"
  if [ -f "$QUICK_BRIDGE_STATE_DIR/state.env" ]; then
    bash "$ROOT_DIR/scripts/stop_cloudflare_quick_tunnel_bridge.sh" "$QUICK_BRIDGE_STATE_DIR"
  else
    echo "      [skip] No detached Quick Tunnel bridge state found at $QUICK_BRIDGE_STATE_DIR"
  fi
else
  echo "[6/8] Keeping detached Quick Tunnel fallback alive (per --keep-quick-fallback)"
fi

echo "[7/8] Starting backend service and target"
sudo systemctl restart immcad-backend-local.service
sudo systemctl start immcad-cloudflare-origin-stack.target
sudo systemctl is-active --quiet immcad-backend-local.service
sudo systemctl is-active --quiet immcad-cloudflared-named-tunnel.service
sudo systemctl is-active --quiet immcad-cloudflare-origin-stack.target

echo "[8/8] Smoke checks (local + Cloudflare)"
for _ in $(seq 1 30); do
  if curl -fsS --max-time 4 "http://127.0.0.1:8002/healthz" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done
curl -fsS --max-time 5 "http://127.0.0.1:8002/healthz" >/dev/null
check_public_backend_health

if [ "$SKIP_SEARCH_SMOKE" != "1" ]; then
  curl -fsS --max-time 10 -X POST "https://immcad.arkiteto.dpdns.org/api/search/cases" \
    -H 'content-type: application/json' \
    --data '{"query":"IRPA procedural fairness", "top_k": 1}' >/dev/null
fi

if [ -f "$NAMED_TUNNEL_STATE_DIR/cloudflared.pid" ]; then
  named_pid="$(cat "$NAMED_TUNNEL_STATE_DIR/cloudflared.pid" 2>/dev/null || true)"
  if [ -n "$named_pid" ] && kill -0 "$named_pid" 2>/dev/null; then
    echo "[cleanup] Stopping detached named tunnel connector pid=${named_pid} (systemd service is active)"
    kill "$named_pid" 2>/dev/null || true
  fi
fi

echo
echo "Systemd switchover complete."
echo "Active services:"
sudo systemctl --no-pager --full --lines=0 status immcad-backend-local.service immcad-cloudflared-named-tunnel.service immcad-cloudflare-origin-stack.target | sed -n '1,80p' || true
echo
echo "Run health check:"
echo "  bash scripts/check_cloudflare_named_origin_stack_health.sh --with-search"
