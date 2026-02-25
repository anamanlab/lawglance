#!/usr/bin/env bash
set -euo pipefail

WORKER_PATH="backend-cloudflare/src/worker.ts"
API_CLIENT_PATH="frontend-web/lib/api-client.ts"

log_info() {
  echo "[INFO] $*"
}

log_error() {
  echo "[ERROR] $*" >&2
}

require_file() {
  local file_path="$1"
  if [ ! -f "$file_path" ]; then
    log_error "Required file not found: ${file_path}"
    exit 1
  fi
}

require_literal() {
  local file_path="$1"
  local literal="$2"
  local description="$3"
  if ! grep -Fq "$literal" "$file_path"; then
    log_error "${description} (missing literal: ${literal})"
    exit 1
  fi
}

if [ ! -d "backend-cloudflare" ] || [ ! -d "frontend-web" ]; then
  log_error "Run this script from the repository root (backend-cloudflare/ and frontend-web/ required)."
  exit 1
fi

require_file "$WORKER_PATH"
require_file "$API_CLIENT_PATH"

log_info "Validating Cloudflare edge proxy contract literals..."

require_literal "$WORKER_PATH" 'const ALLOWED_PATH_PREFIXES = ["/api/", "/ops/"];' "Worker allowlist prefixes must include /api and /ops"
require_literal "$WORKER_PATH" 'const ALLOWED_EXACT_PATHS = new Set(["/healthz"]);' "Worker allowlist exact paths must include /healthz"
require_literal "$WORKER_PATH" '"x-trace-id": traceId,' "Worker error envelope must emit x-trace-id header"
require_literal "$WORKER_PATH" '"x-immcad-trace-id": traceId,' "Worker error envelope must emit legacy trace header"
require_literal "$WORKER_PATH" "error: {" "Worker error payload must be nested under error object"
require_literal "$WORKER_PATH" "trace_id: traceId," "Worker error payload must expose trace_id"
require_literal "$WORKER_PATH" "policy_reason: policyReason," "Worker error payload must expose policy_reason"
require_literal "$WORKER_PATH" 'headers.set("x-trace-id", traceId);' "Worker success proxy responses must emit x-trace-id header"
require_literal "$WORKER_PATH" 'headers.set("x-immcad-trace-id", traceId);' "Worker success proxy responses must emit legacy trace header"

log_info "Validating frontend API client compatibility for edge response envelopes..."

require_literal "$API_CLIENT_PATH" 'headers.get("x-trace-id") ?? headers.get("x-immcad-trace-id")' "Frontend client must prefer x-trace-id with legacy fallback"
require_literal "$API_CLIENT_PATH" 'typeof payload.error === "string"' "Frontend client must support legacy flat proxy error envelopes"
require_literal "$API_CLIENT_PATH" 'typeof payload.trace_id === "string" ? payload.trace_id : null' "Frontend client must parse legacy trace_id field"

echo "[OK] Cloudflare edge proxy contract checks passed."
