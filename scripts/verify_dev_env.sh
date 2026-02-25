#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

command_exists() {
  command -v "$1" >/dev/null 2>&1
}

failures=0
warnings=0

ok() {
  printf "[OK] %s\n" "$1"
}

warn() {
  printf "[WARN] %s\n" "$1"
  warnings=$((warnings + 1))
}

fail() {
  printf "[FAIL] %s\n" "$1"
  failures=$((failures + 1))
}

detect_python() {
  local candidate
  local major_minor
  local venv_python="${ROOT_DIR}/.venv/bin/python"

  if [[ -x "$venv_python" ]]; then
    major_minor="$(
      PYTHONHASHSEED=0 \
      IMMCAD_ENABLE_URANDOM_FALLBACK=1 \
      PYTHONPATH="${ROOT_DIR}/src:${ROOT_DIR}${PYTHONPATH:+:${PYTHONPATH}}" \
      "$venv_python" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null || true
    )"
    if [[ "$major_minor" == "3.11" || "$major_minor" == "3.12" || "$major_minor" == "3.13" ]]; then
      echo "$venv_python"
      return 0
    fi
  fi

  if command_exists python3.11; then
    echo "python3.11"
    return 0
  fi

  if command_exists python3; then
    candidate="python3"
    major_minor="$("$candidate" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
    if [[ "$major_minor" == "3.11" || "$major_minor" == "3.12" || "$major_minor" == "3.13" ]]; then
      echo "$candidate"
      return 0
    fi
  fi

  return 1
}

echo "Environment verification for IMMCAD"
echo "OS: $(uname -s)"
echo "ARCH: $(uname -m)"
echo

if PYTHON_BIN="$(detect_python)"; then
  ok "Python runtime found: $("$PYTHON_BIN" --version)"
else
  fail "Python 3.11+ not found (required by pyproject.toml)."
fi

if command_exists uv; then
  ok "uv found: $(uv --version)"
else
  fail "uv is not installed."
fi

if [[ $failures -eq 0 ]]; then
  if [[ -x "${ROOT_DIR}/scripts/venv_exec.sh" ]]; then
    run_cmd=("${ROOT_DIR}/scripts/venv_exec.sh")
  else
    run_cmd=("$PYTHON_BIN")
  fi

  if "${run_cmd[@]}" python - <<'PY'
import importlib.util

modules = ["streamlit", "chromadb", "langchain", "openai", "redis"]
missing = [module for module in modules if importlib.util.find_spec(module) is None]
if missing:
    raise SystemExit(f"missing modules: {', '.join(missing)}")
print("python module imports check passed")
PY
  then
    ok "Core Python dependencies are importable"
  else
    fail "Core Python dependency imports failed. Run ./scripts/setup_dev_env.sh."
  fi

  if "${run_cmd[@]}" ruff --version >/dev/null 2>&1; then
    ok "ruff is available"
  else
    fail "ruff is unavailable in environment"
  fi

  if "${run_cmd[@]}" pytest --version >/dev/null 2>&1; then
    ok "pytest is available"
  else
    fail "pytest is unavailable in environment"
  fi

  if "${run_cmd[@]}" mypy --version >/dev/null 2>&1; then
    ok "mypy is available"
  else
    fail "mypy is unavailable in environment"
  fi
fi

if [[ -f .env ]]; then
  key_line="$(grep -E '^[[:space:]]*OPENAI_API_KEY[[:space:]]*=' .env | tail -n 1 || true)"
  if [[ -z "$key_line" ]]; then
    warn ".env exists but OPENAI_API_KEY is not defined."
  else
    key_value="${key_line#*=}"
    key_value="${key_value%%#*}"
    key_value="$(printf '%s' "$key_value" | sed -E 's/^[[:space:]]+|[[:space:]]+$//g' | tr -d '"' | tr -d "'")"
    if [[ -z "$key_value" || "$key_value" == "your-openai-api-key" ]]; then
      warn "OPENAI_API_KEY is still a placeholder."
    else
      ok "OPENAI_API_KEY is configured"
    fi
  fi
else
  warn ".env file is missing. Copy .env.example to .env."
fi

if command_exists redis-cli; then
  if redis-cli ping >/dev/null 2>&1; then
    ok "Redis is reachable (redis-cli ping)"
  else
    warn "redis-cli is present but Redis server is not reachable."
  fi
else
  warn "redis-cli not found (Redis is optional but recommended for chat history cache)."
fi

echo
echo "Verification summary: $failures failure(s), $warnings warning(s)"
if [[ $failures -gt 0 ]]; then
  exit 1
fi
