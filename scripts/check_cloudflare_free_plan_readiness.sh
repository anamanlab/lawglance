#!/usr/bin/env bash
set -euo pipefail

CLOUDFLARE_BACKEND_MODE="${CLOUDFLARE_BACKEND_MODE:-proxy}"
CLOUDFLARE_CHECK_NATIVE="${CLOUDFLARE_CHECK_NATIVE:-1}"
CLOUDFLARE_FREE_WORKER_GZIP_LIMIT_KIB="${CLOUDFLARE_FREE_WORKER_GZIP_LIMIT_KIB:-3072}"

log_info() {
  echo "[INFO] $*"
}

log_warn() {
  echo "[WARN] $*"
}

log_error() {
  echo "[ERROR] $*"
}

extract_gzip_kib() {
  local output="$1"
  local line
  line="$(printf '%s\n' "$output" | grep -m1 'Total Upload:' || true)"
  if [ -z "$line" ]; then
    return 1
  fi
  printf '%s\n' "$line" | sed -E 's#.*gzip: ([0-9]+(\.[0-9]+)?) KiB.*#\1#'
}

is_greater_than() {
  local value="$1"
  local limit="$2"
  awk -v value="$value" -v limit="$limit" 'BEGIN { exit !(value > limit) }'
}

run_wrangle_dry_run() {
  local workdir="$1"
  local config="$2"
  (
    cd "$workdir"
    npx --yes wrangler@4.68.1 deploy --config "$config" --dry-run --outdir /tmp/immcad-cloudflare-free-plan-check
  )
}

if [ ! -d "frontend-web" ] || [ ! -d "backend-cloudflare" ]; then
  log_error "Run this script from the repository root (frontend-web/ and backend-cloudflare/ required)."
  exit 1
fi

if [[ "$CLOUDFLARE_BACKEND_MODE" != "proxy" && "$CLOUDFLARE_BACKEND_MODE" != "native" ]]; then
  log_error "CLOUDFLARE_BACKEND_MODE must be 'proxy' or 'native'."
  exit 1
fi

log_info "Evaluating Cloudflare free-plan readiness (mode=${CLOUDFLARE_BACKEND_MODE}, gzip_limit_kib=${CLOUDFLARE_FREE_WORKER_GZIP_LIMIT_KIB})"

log_info "Running frontend Worker dry-run bundle check..."
if ! frontend_output="$(run_wrangle_dry_run "frontend-web" "wrangler.jsonc" 2>&1)"; then
  log_error "Frontend dry-run failed."
  printf '%s\n' "$frontend_output"
  exit 1
fi
frontend_gzip_kib="$(extract_gzip_kib "$frontend_output")"
log_info "Frontend dry-run gzip size: ${frontend_gzip_kib} KiB"
if is_greater_than "$frontend_gzip_kib" "$CLOUDFLARE_FREE_WORKER_GZIP_LIMIT_KIB"; then
  log_error "Frontend worker bundle exceeds free-plan gzip size limit (${frontend_gzip_kib} > ${CLOUDFLARE_FREE_WORKER_GZIP_LIMIT_KIB} KiB)."
  exit 1
fi

log_info "Running backend proxy Worker dry-run bundle check..."
if ! backend_proxy_output="$(run_wrangle_dry_run "backend-cloudflare" "wrangler.backend-proxy.jsonc" 2>&1)"; then
  log_error "Backend proxy dry-run failed."
  printf '%s\n' "$backend_proxy_output"
  exit 1
fi
backend_proxy_gzip_kib="$(extract_gzip_kib "$backend_proxy_output")"
log_info "Backend proxy dry-run gzip size: ${backend_proxy_gzip_kib} KiB"
if is_greater_than "$backend_proxy_gzip_kib" "$CLOUDFLARE_FREE_WORKER_GZIP_LIMIT_KIB"; then
  log_error "Backend proxy bundle exceeds free-plan gzip size limit (${backend_proxy_gzip_kib} > ${CLOUDFLARE_FREE_WORKER_GZIP_LIMIT_KIB} KiB)."
  exit 1
fi

if [ "$CLOUDFLARE_CHECK_NATIVE" = "1" ] || [ "$CLOUDFLARE_BACKEND_MODE" = "native" ]; then
  log_info "Running native Python Worker dry-run bundle check..."
  if ! backend_native_output="$(run_wrangle_dry_run "backend-cloudflare" "wrangler.toml" 2>&1)"; then
    if [ "$CLOUDFLARE_BACKEND_MODE" = "native" ]; then
      log_error "Native backend dry-run failed in native mode."
      printf '%s\n' "$backend_native_output"
      exit 1
    fi
    log_warn "Native backend dry-run failed; continuing because mode=proxy."
    printf '%s\n' "$backend_native_output"
    echo "[OK] Proxy-mode free-plan readiness checks passed."
    exit 0
  fi

  backend_native_gzip_kib="$(extract_gzip_kib "$backend_native_output")"
  log_info "Native backend dry-run gzip size: ${backend_native_gzip_kib} KiB"

  if is_greater_than "$backend_native_gzip_kib" "$CLOUDFLARE_FREE_WORKER_GZIP_LIMIT_KIB"; then
    if [ "$CLOUDFLARE_BACKEND_MODE" = "native" ]; then
      log_error "Native backend bundle exceeds free-plan gzip size limit (${backend_native_gzip_kib} > ${CLOUDFLARE_FREE_WORKER_GZIP_LIMIT_KIB} KiB)."
      exit 1
    fi
    log_warn "Native backend is blocked on free plan (${backend_native_gzip_kib} > ${CLOUDFLARE_FREE_WORKER_GZIP_LIMIT_KIB} KiB). Keep production mode on proxy until native footprint is reduced."
  fi
fi

echo "[OK] Cloudflare free-plan readiness checks passed for backend mode '${CLOUDFLARE_BACKEND_MODE}'."
