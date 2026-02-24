#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_BIN="${ROOT_DIR}/.venv/bin"

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <command> [args...]"
  exit 1
fi

if [[ ! -x "${VENV_BIN}/python" ]]; then
  echo "Error: ${VENV_BIN}/python not found. Create the virtualenv first."
  exit 1
fi

# Work around sandbox entropy restrictions that break this Python runtime.
export PYTHONHASHSEED="${PYTHONHASHSEED:-0}"
if [[ -z "${IMMCAD_ENABLE_URANDOM_FALLBACK:-}" ]]; then
  if PYTHONHASHSEED="${PYTHONHASHSEED}" "${VENV_BIN}/python" -c 'import os; os.urandom(1)' >/dev/null 2>&1; then
    export IMMCAD_ENABLE_URANDOM_FALLBACK=0
  else
    export IMMCAD_ENABLE_URANDOM_FALLBACK=1
  fi
fi
if [[ -z "${IMMCAD_ENABLE_ASYNCIO_THREADSAFE_POLL:-}" ]]; then
  if PYTHONHASHSEED="${PYTHONHASHSEED}" "${VENV_BIN}/python" - <<'PY' >/dev/null 2>&1
import asyncio
import threading

loop = asyncio.new_event_loop()
event = threading.Event()

def _runner() -> None:
    asyncio.set_event_loop(loop)
    loop.run_forever()

thread = threading.Thread(target=_runner, daemon=True)
thread.start()

def _mark_done() -> None:
    event.set()
    loop.stop()

ok = False
try:
    loop.call_soon_threadsafe(_mark_done)
    ok = event.wait(0.3)
finally:
    if loop.is_running():
        try:
            loop.call_soon_threadsafe(loop.stop)
        except Exception:
            pass
    thread.join(timeout=0.5)
    loop.close()

raise SystemExit(0 if ok else 1)
PY
  then
    export IMMCAD_ENABLE_ASYNCIO_THREADSAFE_POLL=0
  else
    export IMMCAD_ENABLE_ASYNCIO_THREADSAFE_POLL=1
  fi
fi
export PYTHONPATH="${ROOT_DIR}/src:${ROOT_DIR}${PYTHONPATH:+:${PYTHONPATH}}"

cmd="$1"
shift || true

case "$cmd" in
  python|python3)
    exec "${VENV_BIN}/python" "$@"
    ;;
  *)
    if [[ -x "${VENV_BIN}/${cmd}" ]]; then
      exec "${VENV_BIN}/${cmd}" "$@"
    fi
    exec "$cmd" "$@"
    ;;
esac
