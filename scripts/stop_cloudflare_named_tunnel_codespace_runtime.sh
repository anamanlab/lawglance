#!/usr/bin/env bash
set -euo pipefail

STATE_DIR="${1:-/tmp/immcad-codespace-named-origin}"

stop_pid_file() {
  local pid_file="$1"
  local label="$2"
  if [ ! -f "$pid_file" ]; then
    echo "[skip] ${label} pid file not found: $pid_file"
    return 0
  fi
  local pid
  pid="$(cat "$pid_file" 2>/dev/null || true)"
  if [ -z "${pid}" ]; then
    echo "[skip] ${label} pid file empty: $pid_file"
    rm -f "$pid_file"
    return 0
  fi
  if kill -0 "$pid" 2>/dev/null; then
    echo "[stop] ${label} pid=${pid}"
    kill "$pid" 2>/dev/null || true
    for _ in $(seq 1 10); do
      if ! kill -0 "$pid" 2>/dev/null; then
        rm -f "$pid_file"
        return 0
      fi
      sleep 1
    done
    echo "[kill] ${label} pid=${pid}"
    kill -9 "$pid" 2>/dev/null || true
  else
    echo "[skip] ${label} pid=${pid} is not running"
  fi
  rm -f "$pid_file"
}

stop_pid_file "${STATE_DIR}/cloudflared.pid" "cloudflared"
stop_pid_file "${STATE_DIR}/backend.pid" "backend"

echo "[done] Codespaces named-tunnel runtime processes stopped (if running)"
echo "State dir retained: ${STATE_DIR}"
