#!/usr/bin/env bash
set -euo pipefail

# Sync selected backend runtime secrets to the Cloudflare native Python Worker.
# Only secrets present in the current shell environment are updated.
# Unset variables are skipped so existing Cloudflare secrets remain unchanged.

WRANGLER_VERSION="${WRANGLER_VERSION:-4.69.0}"
WRANGLER_CONFIG="${WRANGLER_CONFIG:-backend-cloudflare/wrangler.toml}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

usage() {
  cat <<'EOF'
Usage:
  bash scripts/sync_cloudflare_backend_native_secrets.sh [SECRET_NAME ...]

Behavior:
  - Updates only secrets that are set and non-empty in the current shell.
  - Skips unset secrets (does not delete or overwrite existing Cloudflare values).
  - Reads values from environment variables with the same names.

Default secret set (when no args are passed):
  IMMCAD_API_BEARER_TOKEN
  API_BEARER_TOKEN
  GEMINI_API_KEY
  CANLII_API_KEY
  REDIS_URL

Options via environment:
  WRANGLER_CONFIG   Wrangler config path (default: backend-cloudflare/wrangler.toml)
  WRANGLER_VERSION  Wrangler version pin (default: 4.69.0)

Examples:
  export CANLII_API_KEY='...'
  bash scripts/sync_cloudflare_backend_native_secrets.sh CANLII_API_KEY

  export IMMCAD_API_BEARER_TOKEN='...'
  export GEMINI_API_KEY='...'
  export CANLII_API_KEY='...'
  bash scripts/sync_cloudflare_backend_native_secrets.sh
EOF
}

DEFAULT_SECRETS=(
  "IMMCAD_API_BEARER_TOKEN"
  "API_BEARER_TOKEN"
  "GEMINI_API_KEY"
  "CANLII_API_KEY"
  "REDIS_URL"
)

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

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

if [[ ! -f "${WRANGLER_CONFIG}" ]]; then
  echo "[ERROR] Wrangler config not found: ${WRANGLER_CONFIG}" >&2
  exit 1
fi

mkdir -p "${REPO_ROOT}/.cache/wrangler-logs" "${NPM_CONFIG_CACHE:-/tmp/npmcache}"
export WRANGLER_LOG_PATH="${WRANGLER_LOG_PATH:-${REPO_ROOT}/.cache/wrangler-logs}"
export NPM_CONFIG_CACHE="${NPM_CONFIG_CACHE:-/tmp/npmcache}"

if [[ $# -gt 0 ]]; then
  SECRETS=("$@")
else
  SECRETS=("${DEFAULT_SECRETS[@]}")
fi

if [[ -n "${IMMCAD_API_BEARER_TOKEN:-}" && -n "${API_BEARER_TOKEN:-}" ]]; then
  if [[ "${IMMCAD_API_BEARER_TOKEN}" != "${API_BEARER_TOKEN}" ]]; then
    echo "[ERROR] IMMCAD_API_BEARER_TOKEN and API_BEARER_TOKEN are both set but differ." >&2
    echo "        Align them before syncing to avoid backend/frontend auth mismatch." >&2
    exit 1
  fi
fi

if [[ -z "${CLOUDFLARE_API_TOKEN:-}" ]]; then
  echo "[WARN] CLOUDFLARE_API_TOKEN is not set in this shell. Wrangler may prompt/fail depending on local auth state."
fi
if [[ -z "${CLOUDFLARE_ACCOUNT_ID:-}" ]]; then
  echo "[WARN] CLOUDFLARE_ACCOUNT_ID is not set in this shell. Wrangler may prompt/fail depending on local auth state."
fi

updated=0
skipped=0

for secret_name in "${SECRETS[@]}"; do
  if [[ -z "${!secret_name+x}" ]]; then
    echo "[SKIP] ${secret_name}: not set in shell environment (Cloudflare value left unchanged)"
    skipped=$((skipped + 1))
    continue
  fi

  secret_value="${!secret_name}"
  if [[ -z "${secret_value}" ]]; then
    echo "[SKIP] ${secret_name}: set but empty (Cloudflare value left unchanged)"
    skipped=$((skipped + 1))
    continue
  fi

  if printf '%s' "${secret_value}" | grep -qiE '^(your-|changeme|replace-|placeholder)'; then
    echo "[SKIP] ${secret_name}: looks like a placeholder value"
    skipped=$((skipped + 1))
    continue
  fi

  echo "[PUT ] ${secret_name} -> ${WRANGLER_CONFIG}"
  printf '%s' "${secret_value}" \
    | run_wrangler secret put "${secret_name}" --config "${WRANGLER_CONFIG}"
  updated=$((updated + 1))
done

echo "[DONE] Updated ${updated} secret(s); skipped ${skipped}."
