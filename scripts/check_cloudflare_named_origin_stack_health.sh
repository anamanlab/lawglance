#!/usr/bin/env bash
set -euo pipefail

BACKEND_LOCAL_URL="${BACKEND_LOCAL_URL:-http://127.0.0.1:8002/healthz}"
BACKEND_PUBLIC_URL="${BACKEND_PUBLIC_URL:-https://immcad-api.arkiteto.dpdns.org/healthz}"
FRONTEND_URL="${FRONTEND_URL:-https://immcad.arkiteto.dpdns.org}"
WITH_SEARCH="${WITH_SEARCH:-0}"

usage() {
  cat <<'EOF'
Validate the systemd-managed Cloudflare named-origin stack health.

Usage:
  scripts/check_cloudflare_named_origin_stack_health.sh [options]

Options:
  --with-search   Also run a lightweight frontend case-search smoke
  --help          Show help
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
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

command -v sudo >/dev/null 2>&1 || { echo "ERROR: sudo not found" >&2; exit 1; }
command -v curl >/dev/null 2>&1 || { echo "ERROR: curl not found" >&2; exit 1; }

sudo systemctl is-active --quiet immcad-backend-local.service
sudo systemctl is-active --quiet immcad-cloudflared-named-tunnel.service
sudo systemctl is-active --quiet immcad-cloudflare-origin-stack.target

curl -fsS --max-time 5 "$BACKEND_LOCAL_URL" >/dev/null
curl -fsS --max-time 8 "$BACKEND_PUBLIC_URL" >/dev/null

if [ "$WITH_SEARCH" = "1" ]; then
  curl -fsS --max-time 10 -X POST "${FRONTEND_URL}/api/search/cases" \
    -H 'content-type: application/json' \
    --data '{"query":"IRPA procedural fairness", "top_k": 1}' >/dev/null
fi

echo "OK: systemd-managed Cloudflare named-origin stack healthy"
echo "  local_backend: ${BACKEND_LOCAL_URL}"
echo "  public_backend: ${BACKEND_PUBLIC_URL}"
echo "  frontend: ${FRONTEND_URL}"
