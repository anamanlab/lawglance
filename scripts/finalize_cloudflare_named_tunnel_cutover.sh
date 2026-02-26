#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Finalize Cloudflare named-tunnel cutover for the IMMCAD backend proxy.

This script automates everything possible and only pauses for an interactive
Cloudflare login if DNS routing requires `cloudflared tunnel route dns` and
`cert.pem` is not present yet.

Usage:
  scripts/finalize_cloudflare_named_tunnel_cutover.sh [options]

Options:
  --tunnel-env PATH        Named tunnel env file (default: /tmp/immcad_named_tunnel.env)
  --bridge-state PATH      Active Quick Tunnel bridge state dir (default: /tmp/immcad-cloudflare-bridge-managed)
  --hostname HOSTNAME      Public hostname to route to the named tunnel
                           (default: immcad-origin-tunnel.arkiteto.dpdns.org)
  --zone-name ZONE         Zone name for DNS lookup (default: arkiteto.dpdns.org)
  --service-url URL        Origin service behind the named tunnel (default: derived from bridge state)
  --non-interactive        Do not run `cloudflared tunnel login` if cert.pem is missing
  --doctor                 Diagnose only (no DNS route creation, no deploy)
  --skip-deploy            Skip backend proxy redeploy
  --skip-smoke             Skip live smoke tests
  --no-rollback            Do not rollback backend proxy to Quick Tunnel on cutover failure
  --help                   Show help

Environment:
  CLOUDFLARE_API_TOKEN     Optional API token with DNS edit permission. If set, the script
                           will attempt DNS record creation via API before falling back to
                           `cloudflared tunnel route dns`.
EOF
}

require_cmd() {
  local cmd="$1"
  command -v "$cmd" >/dev/null 2>&1 || {
    echo "ERROR: Required command not found: $cmd" >&2
    exit 1
  }
}

log() { printf '%s\n' "$*"; }
warn() { printf '[warn] %s\n' "$*" >&2; }
err() { printf '[error] %s\n' "$*" >&2; }

parse_wrangler_toml_value() {
  local key="$1"
  local file="$2"
  grep -E "^${key}[[:space:]]*=" "$file" | head -n1 | sed -E 's/.*=[[:space:]]*"([^"]+)".*/\1/' || true
}

resolve_cloudflared_bin() {
  if [ -x "$HOME/bin/cloudflared" ]; then
    printf '%s\n' "$HOME/bin/cloudflared"
    return
  fi
  command -v cloudflared || true
}

dns_query_public_cname() {
  local host="$1"
  if command -v dig >/dev/null 2>&1; then
    dig +short @"1.1.1.1" "$host" CNAME 2>/dev/null | tail -n1
    return 0
  fi
  if command -v nslookup >/dev/null 2>&1; then
    nslookup "$host" 1.1.1.1 2>/dev/null | awk '/canonical name =/ {print $4}' | sed 's/\.$//' | tail -n1
    return 0
  fi
  return 1
}

dns_query_public_ipv4() {
  local host="$1"
  if command -v dig >/dev/null 2>&1; then
    dig +short @"1.1.1.1" "$host" A 2>/dev/null | tail -n1
    return 0
  fi
  return 1
}

probe_public_named_hostname_health() {
  local host="$1"
  if curl -fsS --max-time 5 "https://${host}/healthz" >/dev/null 2>&1; then
    return 0
  fi

  # Local resolvers can lag after Cloudflare DNS changes. If we can get a public
  # resolver answer, test reachability by pinning the hostname to that address.
  local public_ip
  public_ip="$(dns_query_public_ipv4 "$host" || true)"
  if [ -n "${public_ip:-}" ]; then
    curl -fsS --max-time 5 --resolve "${host}:443:${public_ip}" "https://${host}/healthz" >/dev/null 2>&1
    return $?
  fi

  return 1
}

curl_cf_api() {
  local method="$1"
  local url="$2"
  local token="$3"
  local body="${4-}"
  if [ -n "$body" ]; then
    curl -sS -X "$method" \
      -H "Authorization: Bearer ${token}" \
      -H 'Content-Type: application/json' \
      --data "$body" \
      "$url"
  else
    curl -sS -X "$method" \
      -H "Authorization: Bearer ${token}" \
      -H 'Content-Type: application/json' \
      "$url"
  fi
}

BACKEND_PROXY_DEPLOYED_TO_NAMED="0"
CURRENT_DEPLOY_TARGET=""

rollback_backend_proxy_if_needed() {
  local exit_code="$?"
  if [ "$exit_code" -eq 0 ]; then
    return
  fi
  if [ "${ROLLBACK_ON_FAIL}" != "1" ]; then
    return
  fi
  if [ "$BACKEND_PROXY_DEPLOYED_TO_NAMED" != "1" ]; then
    return
  fi
  if [ -z "${QUICK_TUNNEL_URL:-}" ]; then
    warn "Cutover failed and no QUICK_TUNNEL_URL was available for rollback."
    return
  fi
  warn "Cutover failed after backend proxy deploy. Rolling back to Quick Tunnel origin: ${QUICK_TUNNEL_URL}"
  (
    cd "$ROOT_DIR"
    npx --yes wrangler@4.68.1 deploy \
      --config "$WRANGLER_CONFIG_PATH" \
      --var "BACKEND_ORIGIN:${QUICK_TUNNEL_URL}" \
      --var "BACKEND_REQUEST_TIMEOUT_MS:${BACKEND_REQUEST_TIMEOUT_MS}" \
      --var "BACKEND_RETRY_ATTEMPTS:${BACKEND_RETRY_ATTEMPTS}" \
      --keep-vars >/dev/null
  ) || warn "Rollback deploy failed; manual rollback may be required."
}
trap rollback_backend_proxy_if_needed EXIT

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TUNNEL_ENV="/tmp/immcad_named_tunnel.env"
BRIDGE_STATE_DIR="/tmp/immcad-cloudflare-bridge-managed"
HOSTNAME="immcad-origin-tunnel.arkiteto.dpdns.org"
ZONE_NAME="arkiteto.dpdns.org"
SERVICE_URL=""
INTERACTIVE_LOGIN="1"
DOCTOR_MODE="0"
SKIP_DEPLOY="0"
SKIP_SMOKE="0"
ROLLBACK_ON_FAIL="1"

while [ "$#" -gt 0 ]; do
  case "$1" in
    --tunnel-env)
      shift; TUNNEL_ENV="${1:-}";;
    --bridge-state)
      shift; BRIDGE_STATE_DIR="${1:-}";;
    --hostname)
      shift; HOSTNAME="${1:-}";;
    --zone-name)
      shift; ZONE_NAME="${1:-}";;
    --service-url)
      shift; SERVICE_URL="${1:-}";;
    --non-interactive)
      INTERACTIVE_LOGIN="0";;
    --doctor)
      DOCTOR_MODE="1";;
    --skip-deploy)
      SKIP_DEPLOY="1";;
    --skip-smoke)
      SKIP_SMOKE="1";;
    --no-rollback)
      ROLLBACK_ON_FAIL="0";;
    --help|-h)
      usage; exit 0;;
    *)
      err "Unknown argument: $1"
      usage >&2
      exit 1;;
  esac
  shift || true
done

require_cmd curl
require_cmd jq
require_cmd npx

CLOUDFLARED_BIN="$(resolve_cloudflared_bin)"
if [ -z "${CLOUDFLARED_BIN:-}" ] || [ ! -x "$CLOUDFLARED_BIN" ]; then
  err "cloudflared not found (expected in ~/bin/cloudflared or PATH)"
  exit 1
fi

WRANGLER_CONFIG_FILE="${HOME}/.config/.wrangler/config/default.toml"
if [ ! -f "$WRANGLER_CONFIG_FILE" ]; then
  err "Wrangler OAuth config not found: $WRANGLER_CONFIG_FILE"
  exit 1
fi

CF_OAUTH_TOKEN="$(parse_wrangler_toml_value oauth_token "$WRANGLER_CONFIG_FILE")"
CF_ACCOUNT_ID="$(parse_wrangler_toml_value account_id "$WRANGLER_CONFIG_FILE")"
if [ -z "$CF_OAUTH_TOKEN" ]; then
  err "Unable to read oauth_token from $WRANGLER_CONFIG_FILE"
  exit 1
fi
if [ -z "$CF_ACCOUNT_ID" ]; then
  CF_ACCOUNT_ID="89533fd25e868dce4cc47cb813054205"
fi

if [ ! -f "$TUNNEL_ENV" ]; then
  err "Named tunnel env file not found: $TUNNEL_ENV"
  exit 1
fi
set -a
# shellcheck disable=SC1090
source "$TUNNEL_ENV"
set +a

for required in TUNNEL_ID TUNNEL_TOKEN; do
  if [ -z "${!required:-}" ]; then
    err "Missing ${required} in ${TUNNEL_ENV}"
    exit 1
  fi
done

BRIDGE_STATE_ENV="${BRIDGE_STATE_DIR}/state.env"
if [ ! -f "$BRIDGE_STATE_ENV" ]; then
  err "Quick bridge state file not found: $BRIDGE_STATE_ENV"
  exit 1
fi
set -a
# shellcheck disable=SC1090
source "$BRIDGE_STATE_ENV"
set +a

for required in BACKEND_HOST BACKEND_PORT BACKEND_PROXY_WORKER_URL FRONTEND_URL QUICK_TUNNEL_URL; do
  if [ -z "${!required:-}" ]; then
    err "Missing ${required} in ${BRIDGE_STATE_ENV}"
    exit 1
  fi
done

if [ -z "$SERVICE_URL" ]; then
  SERVICE_URL="http://${BACKEND_HOST}:${BACKEND_PORT}"
fi

BACKEND_REQUEST_TIMEOUT_MS="${BACKEND_REQUEST_TIMEOUT_MS:-15000}"
BACKEND_RETRY_ATTEMPTS="${BACKEND_RETRY_ATTEMPTS:-1}"
WRANGLER_CONFIG_PATH="${WRANGLER_CONFIG_PATH:-backend-cloudflare/wrangler.backend-proxy.jsonc}"

NAMED_TUNNEL_STATE_DIR="/tmp/immcad-named-tunnel-managed"
mkdir -p "$NAMED_TUNNEL_STATE_DIR"
chmod 700 "$NAMED_TUNNEL_STATE_DIR"
NAMED_TUNNEL_LOG="${NAMED_TUNNEL_STATE_DIR}/cloudflared.log"
NAMED_TUNNEL_PID_FILE="${NAMED_TUNNEL_STATE_DIR}/cloudflared.pid"

log "[1/7] Validating local backend service (${SERVICE_URL})"
curl -fsS --max-time 3 "${SERVICE_URL}/healthz" >/dev/null

log "[2/7] Updating named tunnel remote config (hostname -> ${SERVICE_URL})"
PUT_BODY="$(jq -nc --arg h "$HOSTNAME" --arg s "$SERVICE_URL" '{config:{ingress:[{hostname:$h,service:$s},{service:"http_status:404"}]}}')"
CFG_PUT_JSON="$(curl_cf_api PUT "https://api.cloudflare.com/client/v4/accounts/${CF_ACCOUNT_ID}/cfd_tunnel/${TUNNEL_ID}/configurations" "$CF_OAUTH_TOKEN" "$PUT_BODY")"
if [ "$(printf '%s' "$CFG_PUT_JSON" | jq -r '.success')" != "true" ]; then
  err "Failed to update named tunnel config: $(printf '%s' "$CFG_PUT_JSON" | jq -c '.errors')"
  exit 1
fi
log "  remote config updated"

log "[3/7] Ensuring named tunnel connector is running (detached)"
if [ -f "$NAMED_TUNNEL_PID_FILE" ]; then
  oldpid="$(cat "$NAMED_TUNNEL_PID_FILE" 2>/dev/null || true)"
  if [ -n "${oldpid:-}" ] && kill -0 "$oldpid" 2>/dev/null; then
    log "  existing named tunnel connector is running (pid=${oldpid})"
  else
    rm -f "$NAMED_TUNNEL_PID_FILE"
  fi
fi
if [ ! -f "$NAMED_TUNNEL_PID_FILE" ]; then
  nohup setsid "$CLOUDFLARED_BIN" tunnel run --token "$TUNNEL_TOKEN" >"$NAMED_TUNNEL_LOG" 2>&1 < /dev/null &
  echo $! > "$NAMED_TUNNEL_PID_FILE"
  log "  started named tunnel connector pid=$(cat "$NAMED_TUNNEL_PID_FILE")"
fi

for _ in $(seq 1 20); do
  if grep -q "Registered tunnel connection" "$NAMED_TUNNEL_LOG" 2>/dev/null; then
    break
  fi
  sleep 1
done
if ! grep -q "Registered tunnel connection" "$NAMED_TUNNEL_LOG" 2>/dev/null; then
  err "Named tunnel connector did not register. See $NAMED_TUNNEL_LOG"
  exit 1
fi
log "  named tunnel connector registered"

log "[4/7] Checking DNS route for ${HOSTNAME}"
ZONE_LOOKUP_JSON="$(curl_cf_api GET "https://api.cloudflare.com/client/v4/zones?name=${ZONE_NAME}" "$CF_OAUTH_TOKEN")"
if [ "$(printf '%s' "$ZONE_LOOKUP_JSON" | jq -r '.success')" != "true" ]; then
  err "Zone lookup failed: $(printf '%s' "$ZONE_LOOKUP_JSON" | jq -c '.errors')"
  exit 1
fi
ZONE_ID="$(printf '%s' "$ZONE_LOOKUP_JSON" | jq -r '.result[0].id // empty')"
if [ -z "$ZONE_ID" ]; then
  err "Zone not found for ${ZONE_NAME}"
  exit 1
fi

dns_record_exists() {
  local lookup_json
  lookup_json="$(curl_cf_api GET "https://api.cloudflare.com/client/v4/zones/${ZONE_ID}/dns_records?type=CNAME&name=${HOSTNAME}" "$CF_OAUTH_TOKEN")"
  if [ "$(printf '%s' "$lookup_json" | jq -r '.success')" != "true" ]; then
    printf 'api_error:%s\n' "$(printf '%s' "$lookup_json" | jq -c '.errors')"
    return 2
  fi
  local count
  count="$(printf '%s' "$lookup_json" | jq -r '(.result | length)')"
  if [ "$count" -gt 0 ]; then
    local content
    content="$(printf '%s' "$lookup_json" | jq -r '.result[0].content')"
    printf 'present:%s\n' "$content"
    return 0
  fi
  printf 'missing\n'
  return 1
}

dns_status="$(dns_record_exists || true)"
log "  dns status: ${dns_status}"
public_cname_initial="$(dns_query_public_cname "$HOSTNAME" || true)"
if [ -n "${public_cname_initial:-}" ]; then
  log "  public resolver CNAME: ${public_cname_initial}"
else
  log "  public resolver CNAME: (none visible yet or resolver tool unavailable)"
fi

try_dns_create_via_api() {
  local token="$1"
  local body
  body="$(jq -nc --arg name "$HOSTNAME" --arg target "${TUNNEL_ID}.cfargotunnel.com" '{type:"CNAME",name:$name,content:$target,proxied:true}')"
  curl_cf_api POST "https://api.cloudflare.com/client/v4/zones/${ZONE_ID}/dns_records" "$token" "$body"
}

if [ "${DOCTOR_MODE}" = "1" ]; then
  log "[doctor] Skipping DNS route creation / deploy / smoke."
  if probe_public_named_hostname_health "$HOSTNAME"; then
    log "[doctor] Public hostname health: reachable (https://${HOSTNAME}/healthz)"
  else
    log "[doctor] Public hostname health: not reachable yet"
  fi
  exit 0
fi

if [[ "$dns_status" != present:* ]]; then
  if [ -n "${CLOUDFLARE_API_TOKEN:-}" ]; then
    log "  attempting DNS record create via CLOUDFLARE_API_TOKEN ..."
    dns_create_json="$(try_dns_create_via_api "$CLOUDFLARE_API_TOKEN")"
    if [ "$(printf '%s' "$dns_create_json" | jq -r '.success')" = "true" ]; then
      log "  DNS record created via API token"
    else
      warn "DNS create via CLOUDFLARE_API_TOKEN failed: $(printf '%s' "$dns_create_json" | jq -c '.errors')"
    fi
  else
    log "  CLOUDFLARE_API_TOKEN not set; skipping DNS create via API"
  fi

  dns_status="$(dns_record_exists || true)"
  log "  dns status after API attempt: ${dns_status}"

  if [[ "$dns_status" != present:* ]]; then
    if [ ! -f "$HOME/.cloudflared/cert.pem" ]; then
      if [ "$INTERACTIVE_LOGIN" != "1" ]; then
        err "DNS route still missing and cert.pem not present. Re-run without --non-interactive to complete cloudflared login."
        exit 1
      fi
      log "  cert.pem not found. Starting interactive Cloudflare login (one browser click required)..."
      mkdir -p "$HOME/.cloudflared"
      "$CLOUDFLARED_BIN" tunnel login
    fi

    log "  creating DNS route via cloudflared tunnel route dns ..."
    "$CLOUDFLARED_BIN" tunnel route dns --overwrite-dns "$TUNNEL_ID" "$HOSTNAME"
    dns_status="$(dns_record_exists || true)"
    log "  dns status after cloudflared route dns: ${dns_status}"
  fi
fi

if [[ "$dns_status" != present:* && "$dns_status" != api_error:* ]]; then
  err "DNS route was not created. Manual fallback: create CNAME ${HOSTNAME} -> ${TUNNEL_ID}.cfargotunnel.com in Cloudflare DNS."
  exit 1
fi

log "[5/7] Waiting for public named-hostname reachability (${HOSTNAME})"
resolved_ok="0"
for _ in $(seq 1 45); do
  if probe_public_named_hostname_health "$HOSTNAME"; then
    log "  public hostname is reachable: https://${HOSTNAME}/healthz"
    resolved_ok="1"
    break
  fi
  sleep 2
done
if [ "$resolved_ok" != "1" ]; then
  warn "Named hostname was not reachable from this host after waiting."
  if [ -n "$(dns_query_public_cname "$HOSTNAME" || true)" ]; then
    warn "A public CNAME is visible, but /healthz did not respond yet."
  else
    warn "No public CNAME was visible from this host (or DNS tools unavailable)."
  fi
  err "Aborting cutover before backend proxy redeploy to avoid outage."
  exit 1
fi

if [ "$SKIP_DEPLOY" != "1" ]; then
  log "[6/7] Redeploying backend proxy to named tunnel hostname"
  CURRENT_DEPLOY_TARGET="https://${HOSTNAME}"
  (
    cd "$ROOT_DIR"
    npx --yes wrangler@4.68.1 deploy \
      --config "$WRANGLER_CONFIG_PATH" \
      --var "BACKEND_ORIGIN:https://${HOSTNAME}" \
      --var "BACKEND_REQUEST_TIMEOUT_MS:${BACKEND_REQUEST_TIMEOUT_MS}" \
      --var "BACKEND_RETRY_ATTEMPTS:${BACKEND_RETRY_ATTEMPTS}" \
      --keep-vars
  ) | tee "${NAMED_TUNNEL_STATE_DIR}/wrangler-named-cutover.log"
  BACKEND_PROXY_DEPLOYED_TO_NAMED="1"
else
  log "[6/7] Skipping backend proxy redeploy (--skip-deploy)"
fi

if [ "$SKIP_SMOKE" != "1" ] && [ "$SKIP_DEPLOY" != "1" ]; then
  log "[7/7] Running live Cloudflare smoke checks"
  curl -fsS --max-time 8 "${BACKEND_PROXY_WORKER_URL}/healthz" >/dev/null
  curl -fsS --max-time 10 -X POST "${FRONTEND_URL}/api/search/cases" \
    -H 'content-type: application/json' \
    --data '{"query":"IRPA procedural fairness inadmissibility","top_k":1}' >/dev/null
  curl -fsS --max-time 12 -X POST "${FRONTEND_URL}/api/research/lawyer-cases" \
    -H 'content-type: application/json' \
    --data '{"session_id":"named-tunnel-cutover-smoke","matter_summary":"Federal Court procedural fairness inadmissibility appeal decision","jurisdiction":"ca","court":"fc","limit":1}' >/dev/null
else
  log "[7/7] Skipping smoke checks"
fi

log "DONE: Named tunnel cutover finalized"
log "  hostname: ${HOSTNAME}"
log "  tunnel_id: ${TUNNEL_ID}"
log "  named_tunnel_connector_pid: $(cat "$NAMED_TUNNEL_PID_FILE")"
if [ -f "${NAMED_TUNNEL_STATE_DIR}/wrangler-named-cutover.log" ]; then
  version_id="$(grep -oE 'Current Version ID: [a-f0-9-]+' "${NAMED_TUNNEL_STATE_DIR}/wrangler-named-cutover.log" | awk '{print $4}' | tail -n1 || true)"
  if [ -n "${version_id:-}" ]; then
    log "  backend_proxy_version: ${version_id}"
  fi
fi

trap - EXIT
