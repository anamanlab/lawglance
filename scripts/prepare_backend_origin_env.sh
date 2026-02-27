#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Prepare the backend-origin runtime env file used by Cloudflare-managed origin processes.

Usage:
  scripts/prepare_backend_origin_env.sh [options]

Options:
  --from-file PATH     Source env file to copy into runtime location
  --from-vercel        Source from legacy backend-vercel/.env.production.vercel
  --output PATH        Runtime env output path (default: ops/runtime/.env.backend-origin)
  --no-backup          Skip backup when output already exists
  --skip-validate      Skip ENVIRONMENT/IMMCAD_ENVIRONMENT validation
  --help               Show help
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

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUTPUT_PATH="${ROOT_DIR}/ops/runtime/.env.backend-origin"
SOURCE_PATH=""
NO_BACKUP="0"
SKIP_VALIDATE="0"

while [ "$#" -gt 0 ]; do
  case "$1" in
    --from-file)
      require_option_value "$1" "${2-}"
      SOURCE_PATH="$2"
      shift 2
      ;;
    --from-vercel)
      SOURCE_PATH="${ROOT_DIR}/backend-vercel/.env.production.vercel"
      shift
      ;;
    --output)
      require_option_value "$1" "${2-}"
      OUTPUT_PATH="$2"
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

if [ -z "${SOURCE_PATH}" ]; then
  if [ -f "${OUTPUT_PATH}" ]; then
    echo "[OK] Runtime env already present: ${OUTPUT_PATH}"
    echo "     No source specified; leaving existing file unchanged."
    exit 0
  fi
  echo "ERROR: no source env file selected." >&2
  echo "Use --from-file PATH or --from-vercel." >&2
  exit 1
fi

if [ ! -f "${SOURCE_PATH}" ]; then
  echo "ERROR: source env file not found: ${SOURCE_PATH}" >&2
  exit 1
fi

mkdir -p "$(dirname "${OUTPUT_PATH}")"
chmod 700 "$(dirname "${OUTPUT_PATH}")"

if [ -f "${OUTPUT_PATH}" ] && [ "${NO_BACKUP}" != "1" ]; then
  backup_path="${OUTPUT_PATH}.bak.$(date +%Y%m%d_%H%M%S)"
  cp "${OUTPUT_PATH}" "${backup_path}"
  chmod 600 "${backup_path}"
  echo "[BACKUP] ${backup_path}"
fi

cp "${SOURCE_PATH}" "${OUTPUT_PATH}"
chmod 600 "${OUTPUT_PATH}"

upsert_env_key() {
  local file_path="$1"
  local key_name="$2"
  local key_value="$3"
  python3 - <<'PY' "${file_path}" "${key_name}" "${key_value}"
import re
import sys
from pathlib import Path

path = Path(sys.argv[1])
key = sys.argv[2]
value = sys.argv[3]

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
        continue
    result.append(line)

if not updated:
    if result and result[-1].strip():
        result.append("")
    result.append(replacement)

path.write_text("\n".join(result) + "\n", encoding="utf-8")
PY
}

if [ "${SKIP_VALIDATE}" != "1" ]; then
  environment_value="$(
    awk -F= '/^[[:space:]]*(export[[:space:]]+)?ENVIRONMENT=/{sub(/^[^=]*=/,"",$0); print $0; exit}' "${OUTPUT_PATH}" | tr -d '\r'
  )"
  immcad_environment_value="$(
    awk -F= '/^[[:space:]]*(export[[:space:]]+)?IMMCAD_ENVIRONMENT=/{sub(/^[^=]*=/,"",$0); print $0; exit}' "${OUTPUT_PATH}" | tr -d '\r'
  )"
  if [ -n "${environment_value}" ] && [ -z "${immcad_environment_value}" ]; then
    upsert_env_key "${OUTPUT_PATH}" "IMMCAD_ENVIRONMENT" "${environment_value}"
    immcad_environment_value="${environment_value}"
    echo "[INFO] Added IMMCAD_ENVIRONMENT alias from ENVIRONMENT"
  fi
  if [ -z "${environment_value}" ] && [ -n "${immcad_environment_value}" ]; then
    upsert_env_key "${OUTPUT_PATH}" "ENVIRONMENT" "${immcad_environment_value}"
    environment_value="${immcad_environment_value}"
    echo "[INFO] Added ENVIRONMENT from IMMCAD_ENVIRONMENT alias"
  fi
  if [ -z "${environment_value}" ]; then
    echo "ERROR: ENVIRONMENT is required in ${OUTPUT_PATH}" >&2
    exit 1
  fi
  if [ -z "${immcad_environment_value}" ]; then
    echo "ERROR: IMMCAD_ENVIRONMENT is required in ${OUTPUT_PATH}" >&2
    exit 1
  fi
  if [ "${environment_value}" != "${immcad_environment_value}" ]; then
    echo "ERROR: ENVIRONMENT and IMMCAD_ENVIRONMENT must match in ${OUTPUT_PATH}" >&2
    exit 1
  fi
fi

echo "[DONE] Prepared Cloudflare backend runtime env file."
echo "       source: ${SOURCE_PATH}"
echo "       output: ${OUTPUT_PATH}"
