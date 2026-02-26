#!/usr/bin/env bash
set -euo pipefail

STATE_DIR="${1:-/tmp/immcad-cloudflare-bridge}"

stop_pid_file() {
  local file="$1"
  local label="$2"
  if [ ! -f "$file" ]; then
    echo "[skip] ${label} pid file not found: $file"
    return
  fi
  local pid
  pid="$(cat "$file" 2>/dev/null || true)"
  if [ -z "$pid" ]; then
    echo "[skip] ${label} pid file empty: $file"
    return
  fi
  if kill -0 "$pid" 2>/dev/null; then
    echo "[stop] ${label} pid=${pid}"
    kill "$pid" 2>/dev/null || true
    for _ in $(seq 1 10); do
      if ! kill -0 "$pid" 2>/dev/null; then
        break
      fi
      sleep 1
    done
    if kill -0 "$pid" 2>/dev/null; then
      echo "[kill] ${label} pid=${pid}"
      kill -9 "$pid" 2>/dev/null || true
    fi
  else
    echo "[skip] ${label} pid=${pid} is not running"
  fi
}

stop_pid_file "${STATE_DIR}/cloudflared.pid" "cloudflared"
stop_pid_file "${STATE_DIR}/uvicorn.pid" "uvicorn"

echo "[done] Bridge processes stopped (if they were running)."
echo "State dir retained: ${STATE_DIR}"
