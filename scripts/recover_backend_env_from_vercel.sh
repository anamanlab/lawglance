#!/usr/bin/env bash
set -euo pipefail

# Recover the backend origin runtime env file from Vercel production variables.
# Safe-by-default:
# - Backs up existing local target file before overwrite
# - Pulls from Vercel into backend-vercel/.env.production.vercel
# - Only mutates CANLII_API_KEY when explicitly requested via env variable

usage() {
  cat <<'EOF'
Recover backend origin env from Vercel production env (transitional Cloudflare path).

Usage:
  scripts/recover_backend_env_from_vercel.sh [options]

Options:
  --project-dir PATH    Vercel-linked backend project directory (default: backend-vercel)
  --output PATH         Output env file path (default: backend-vercel/.env.production.vercel)
  --environment ENV     Vercel env to pull (default: production)
  --no-backup           Skip local backup before overwriting output
  --skip-validate       Skip post-pull validation
  --apply-canlii        Upsert CANLII_API_KEY from current shell into output file
  --help                Show help

Requirements:
  - Vercel project access (interactive login or VERCEL_TOKEN)
  - Project linked to the correct backend Vercel project (run `npx --yes vercel@50.23.2 link --cwd backend-vercel` if needed)

Notes:
  - This does not deploy anything.
  - Current Cloudflare backend proxy mode still requires the recovered file to be used by your origin backend runtime.
EOF
}

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROJECT_DIR="${ROOT_DIR}/backend-vercel"
OUTPUT_PATH="${ROOT_DIR}/backend-vercel/.env.production.vercel"
ENVIRONMENT="production"
NO_BACKUP="0"
SKIP_VALIDATE="0"
APPLY_CANLII="0"

require_option_value() {
  local option_name="$1"
  local option_value="${2-}"
  if [ -z "$option_value" ] || [[ "$option_value" == --* ]]; then
    echo "ERROR: ${option_name} requires a value." >&2
    usage >&2
    exit 1
  fi
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --project-dir)
      require_option_value "$1" "${2-}"
      PROJECT_DIR="$2"
      shift 2
      ;;
    --output)
      require_option_value "$1" "${2-}"
      OUTPUT_PATH="$2"
      shift 2
      ;;
    --environment)
      require_option_value "$1" "${2-}"
      ENVIRONMENT="$2"
      shift 2
      ;;
    --no-backup)
      NO_BACKUP="1"
      shift
      ;;
    --skip-validate)
      SKIP_VALIDATE="1"
      shift
      ;;
    --apply-canlii)
      APPLY_CANLII="1"
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

PROJECT_DIR="$(cd "${PROJECT_DIR}" && pwd)"
if [ -z "${PROJECT_DIR}" ] || [ ! -d "${PROJECT_DIR}" ]; then
  echo "ERROR: Project directory not found: ${PROJECT_DIR}" >&2
  exit 1
fi

if [ "${ENVIRONMENT}" != "production" ] && [ "${ENVIRONMENT}" != "preview" ] && [ "${ENVIRONMENT}" != "development" ]; then
  echo "ERROR: --environment must be one of: production, preview, development" >&2
  exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "ERROR: python3 is required" >&2
  exit 1
fi

SYNC_SCRIPT="${ROOT_DIR}/scripts/vercel_env_sync.py"
if [ ! -f "${SYNC_SCRIPT}" ]; then
  echo "ERROR: Missing sync script: ${SYNC_SCRIPT}" >&2
  exit 1
fi

if [ ! -f "${PROJECT_DIR}/.vercel/project.json" ]; then
  echo "[WARN] ${PROJECT_DIR}/.vercel/project.json not found."
  echo "       If this Codespace is not linked yet, run:"
  echo "       npx --yes vercel@50.23.2 link --cwd ${PROJECT_DIR}"
fi

if [ -z "${VERCEL_TOKEN:-}" ]; then
  echo "[INFO] VERCEL_TOKEN is not set. The Vercel CLI may prompt for interactive login."
fi

mkdir -p "$(dirname "${OUTPUT_PATH}")"

PULL_ARGS=(
  "pull"
  "--project-dir" "${PROJECT_DIR}"
  "--environment" "${ENVIRONMENT}"
  "--output" "${OUTPUT_PATH}"
)
if [ "${NO_BACKUP}" = "1" ]; then
  PULL_ARGS+=("--no-backup")
fi

echo "[1/3] Pulling ${ENVIRONMENT} env from Vercel into ${OUTPUT_PATH}"
python3 "${SYNC_SCRIPT}" "${PULL_ARGS[@]}"

upsert_env_key_from_shell() {
  local file_path="$1"
  local key_name="$2"
  local key_value="${!key_name:-}"
  if [ -z "${key_value}" ]; then
    echo "[WARN] ${key_name} is not set in shell; skipping upsert."
    return 0
  fi

  python3 - <<'PY' "${file_path}" "${key_name}"
import os
import re
import sys
from pathlib import Path

path = Path(sys.argv[1])
key = sys.argv[2]
value = os.environ.get(key, "")
if not value:
    raise SystemExit(0)

lines = path.read_text(encoding="utf-8").splitlines()
pattern = re.compile(rf"^\s*(?:export\s+)?{re.escape(key)}\s*=")
replacement = f"{key}={value}"

updated = False
result: list[str] = []
for line in lines:
    if pattern.match(line):
        if not updated:
            result.append(replacement)
            updated = True
        # Drop duplicate definitions of the same key.
        continue
    result.append(line)

if not updated:
    if result and result[-1].strip():
        result.append("")
    result.append(replacement)

path.write_text("\n".join(result) + "\n", encoding="utf-8")
PY
  echo "[2/3] Upserted ${key_name} from shell into ${file_path}"
}

if [ "${APPLY_CANLII}" = "1" ]; then
  upsert_env_key_from_shell "${OUTPUT_PATH}" "CANLII_API_KEY"
else
  echo "[2/3] Skipping CANLII_API_KEY upsert (--apply-canlii not set)"
fi

if [ "${SKIP_VALIDATE}" = "1" ]; then
  echo "[3/3] Skipping validation (--skip-validate)"
else
  echo "[3/3] Validating recovered env file"
  python3 "${SYNC_SCRIPT}" validate \
    --project-dir "${PROJECT_DIR}" \
    --environment "${ENVIRONMENT}" \
    --file "${OUTPUT_PATH}" || true
  echo "       (Validation warnings may be expected; inspect output before deployment.)"
fi

echo
echo "[DONE] Backend env recovery completed."
echo "Next steps:"
echo "  - Review ${OUTPUT_PATH}"
echo "  - Ensure CANLII_API_KEY is present (use --apply-canlii with CANLII_API_KEY exported)"
echo "  - Start a replacement origin backend (or temporary Cloudflare quick-tunnel bridge) using this file"
