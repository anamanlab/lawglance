#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

WRANGLER_VERSION="${WRANGLER_VERSION:-4.69.0}"
BACKEND_WRANGLER_CONFIG="${BACKEND_WRANGLER_CONFIG:-backend-cloudflare/wrangler.toml}"
FRONTEND_WRANGLER_CONFIG="${FRONTEND_WRANGLER_CONFIG:-frontend-web/wrangler.jsonc}"
BACKEND_HEALTH_URL="${BACKEND_HEALTH_URL:-}"
ALLOW_GENERATE_BEARER_TOKEN="${ALLOW_GENERATE_BEARER_TOKEN:-false}"
ENV_FILE_CANDIDATES=(
  ".env"
  "backend-vercel/.env.production.vercel"
  "ops/runtime/.env.backend-origin"
)

log() {
  printf '[INFO] %s\n' "$*"
}

warn() {
  printf '[WARN] %s\n' "$*" >&2
}

fail() {
  printf '[ERROR] %s\n' "$*" >&2
  exit 1
}

is_placeholder_value() {
  local value="$1"
  [[ "${value}" =~ ^(your-|changeme|replace-|placeholder) ]]
}

read_env_key_from_file() {
  local key="$1"
  local env_file="$2"
  if [[ ! -f "${env_file}" ]]; then
    return 1
  fi
  awk -F= -v k="${key}" '
    $0 ~ "^[[:space:]]*"k"[[:space:]]*=" {
      value = substr($0, index($0, "=") + 1)
      gsub(/^[[:space:]]+|[[:space:]]+$/, "", value)
      gsub(/^"|"$/, "", value)
      gsub(/^'\''|'\''$/, "", value)
      print value
      exit
    }
  ' "${env_file}"
}

load_key_from_candidate_files() {
  local key="$1"
  local candidate_file
  local loaded_value=""
  for candidate_file in "${ENV_FILE_CANDIDATES[@]}"; do
    loaded_value="$(read_env_key_from_file "${key}" "${candidate_file}" || true)"
    if [[ -n "${loaded_value}" ]]; then
      printf '%s\n' "${loaded_value}"
      printf '[INFO] Loaded %s from %s\n' "${key}" "${candidate_file}" >&2
      return 0
    fi
  done
  return 1
}

require_command() {
  local cmd="$1"
  command -v "${cmd}" >/dev/null 2>&1 || fail "Required command not found: ${cmd}"
}

run_wrangler() {
  if command -v wrangler >/dev/null 2>&1; then
    wrangler "$@"
    return 0
  fi
  if [[ -x "${REPO_ROOT}/frontend-web/node_modules/.bin/wrangler" ]]; then
    "${REPO_ROOT}/frontend-web/node_modules/.bin/wrangler" "$@"
    return 0
  fi
  npx --yes "wrangler@${WRANGLER_VERSION}" "$@"
}

resolve_backend_health_url_from_frontend_config() {
  local frontend_wrangler_config="$1"
  python3 scripts/cloudflare_runtime_config.py \
    --frontend-wrangler "${frontend_wrangler_config}"
}

generate_bearer_token() {
  python3 - <<'PY'
import secrets
print(secrets.token_urlsafe(48))
PY
}

cloudflare_secret_exists() {
  local secret_name="$1"
  local wrangler_config="$2"
  local secret_json
  if ! secret_json="$(
    run_wrangler secret list \
      --format json \
      --config "${wrangler_config}" 2>/dev/null
  )"; then
    return 1
  fi
  python3 -c '
import json
import sys

target = sys.argv[1]
payload = json.loads(sys.stdin.read() or "[]")
exists = any(
    isinstance(item, dict) and item.get("name") == target
    for item in payload
)
print("yes" if exists else "no")
' "${secret_name}" <<<"${secret_json}"
}

main() {
  require_command bash
  require_command uv
  require_command npm
  require_command curl
  require_command python3

  cd "${REPO_ROOT}"
  mkdir -p "${REPO_ROOT}/.cache/wrangler-logs" "${NPM_CONFIG_CACHE:-/tmp/npmcache}" /tmp/uv-cache
  export WRANGLER_LOG_PATH="${WRANGLER_LOG_PATH:-${REPO_ROOT}/.cache/wrangler-logs}"
  export NPM_CONFIG_CACHE="${NPM_CONFIG_CACHE:-/tmp/npmcache}"
  export UV_CACHE_DIR="${UV_CACHE_DIR:-/tmp/uv-cache}"

  log "Validating Wrangler authentication"
  if ! run_wrangler whoami >/dev/null 2>&1; then
    fail "Wrangler auth unavailable. Run: npx --yes wrangler@${WRANGLER_VERSION} login"
  fi

  if [[ -z "${GEMINI_API_KEY:-}" ]]; then
    GEMINI_API_KEY="$(load_key_from_candidate_files "GEMINI_API_KEY" || true)"
    if [[ -n "${GEMINI_API_KEY}" ]]; then
      export GEMINI_API_KEY
    fi
  fi
  if [[ -n "${GEMINI_API_KEY:-}" ]] && is_placeholder_value "${GEMINI_API_KEY}"; then
    warn "Local GEMINI_API_KEY looks like a placeholder; will require existing Cloudflare secret."
    unset GEMINI_API_KEY
  fi

  if [[ -z "${GEMINI_API_KEY:-}" ]]; then
    backend_has_gemini_secret="$(
      cloudflare_secret_exists GEMINI_API_KEY "${BACKEND_WRANGLER_CONFIG}" || true
    )"
    if [[ "${backend_has_gemini_secret}" != "yes" ]]; then
      fail "Cloudflare backend secret GEMINI_API_KEY is missing. Set GEMINI_API_KEY and rerun."
    fi
  fi

  local generated_bearer_token="false"
  if [[ -z "${IMMCAD_API_BEARER_TOKEN:-}" ]]; then
    IMMCAD_API_BEARER_TOKEN="$(
      load_key_from_candidate_files "IMMCAD_API_BEARER_TOKEN" || true
    )"
  fi
  if [[ -n "${IMMCAD_API_BEARER_TOKEN:-}" ]] && is_placeholder_value "${IMMCAD_API_BEARER_TOKEN}"; then
    IMMCAD_API_BEARER_TOKEN=""
  fi
  if [[ -z "${IMMCAD_API_BEARER_TOKEN:-}" ]]; then
    IMMCAD_API_BEARER_TOKEN="$(
      load_key_from_candidate_files "API_BEARER_TOKEN" || true
    )"
    if [[ -n "${IMMCAD_API_BEARER_TOKEN:-}" ]] && is_placeholder_value "${IMMCAD_API_BEARER_TOKEN}"; then
      IMMCAD_API_BEARER_TOKEN=""
    fi
  fi
  if [[ -z "${IMMCAD_API_BEARER_TOKEN:-}" ]]; then
    if [[ "${ALLOW_GENERATE_BEARER_TOKEN}" == "true" ]]; then
      IMMCAD_API_BEARER_TOKEN="$(generate_bearer_token)"
      generated_bearer_token="true"
      warn "IMMCAD_API_BEARER_TOKEN was missing; generated a new token for this deploy."
    else
      fail "IMMCAD_API_BEARER_TOKEN is missing. Set it in shell/.env or run with ALLOW_GENERATE_BEARER_TOKEN=true."
    fi
  fi
  export IMMCAD_API_BEARER_TOKEN
  export API_BEARER_TOKEN="${IMMCAD_API_BEARER_TOKEN}"

  log "Syncing backend native runtime source"
  bash scripts/sync_backend_cloudflare_native_source.sh

  log "Syncing backend worker secrets (Gemini MVP baseline)"
  backend_secret_args=(
    IMMCAD_API_BEARER_TOKEN \
    API_BEARER_TOKEN \
  )
  if [[ -n "${GEMINI_API_KEY:-}" ]]; then
    backend_secret_args+=(GEMINI_API_KEY)
  fi
  if [[ -n "${CANLII_API_KEY:-}" ]] && ! is_placeholder_value "${CANLII_API_KEY}"; then
    backend_secret_args+=(CANLII_API_KEY)
  fi
  if [[ -n "${REDIS_URL:-}" ]] && ! is_placeholder_value "${REDIS_URL}"; then
    backend_secret_args+=(REDIS_URL)
  fi
  bash scripts/sync_cloudflare_backend_native_secrets.sh "${backend_secret_args[@]}"

  log "Deploying backend native worker"
  (
    cd backend-cloudflare
    uv sync --dev
    NPM_CONFIG_CACHE="${NPM_CONFIG_CACHE:-/tmp/npmcache}" uv run pywrangler deploy
  )

  log "Syncing frontend proxy bearer token secrets"
  printf '%s' "${IMMCAD_API_BEARER_TOKEN}" \
    | run_wrangler secret put IMMCAD_API_BEARER_TOKEN --config "${FRONTEND_WRANGLER_CONFIG}"
  printf '%s' "${IMMCAD_API_BEARER_TOKEN}" \
    | run_wrangler secret put API_BEARER_TOKEN --config "${FRONTEND_WRANGLER_CONFIG}"

  log "Deploying frontend worker"
  npm run cf:build --prefix frontend-web
  run_wrangler deploy --config "${FRONTEND_WRANGLER_CONFIG}"

  log "Running backend health check"
  if [[ -z "${BACKEND_HEALTH_URL}" ]]; then
    resolved_backend_health_url="$(
      resolve_backend_health_url_from_frontend_config "${FRONTEND_WRANGLER_CONFIG}"
    )"
    if [[ -n "${resolved_backend_health_url}" ]]; then
      BACKEND_HEALTH_URL="${resolved_backend_health_url%/}/healthz"
      log "Derived BACKEND_HEALTH_URL from frontend runtime config: ${BACKEND_HEALTH_URL}"
    fi
  fi
  if [[ -z "${BACKEND_HEALTH_URL}" ]]; then
    fail "BACKEND_HEALTH_URL is required for deploy verification."
  fi
  if ! curl -fsS "${BACKEND_HEALTH_URL}" >/dev/null; then
    fail "Backend health check failed: ${BACKEND_HEALTH_URL}"
  fi

  if [[ "${generated_bearer_token}" == "true" ]]; then
    printf '\n[IMPORTANT] Generated IMMCAD_API_BEARER_TOKEN (save in password manager):\n%s\n\n' "${IMMCAD_API_BEARER_TOKEN}"
  fi

  log "Gemini-only MVP Cloudflare deploy completed without GitHub dependency."
}

main "$@"
