#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

command_exists() {
  command -v "$1" >/dev/null 2>&1
}

print_step() {
  printf "\n==> %s\n" "$1"
}

detect_python() {
  local candidate
  local major_minor

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

print_step "Detecting platform"
echo "OS: $(uname -s)"
echo "ARCH: $(uname -m)"

print_step "Checking Python version"
if ! PYTHON_BIN="$(detect_python)"; then
  cat <<'EOF'
Python 3.11+ is required for this project.

Install one of:
- macOS (Homebrew): brew install python@3.11
- Ubuntu/Debian: sudo apt-get install python3.11 python3.11-venv
- pyenv: pyenv install 3.11.11 && pyenv local 3.11.11
EOF
  exit 1
fi
echo "Using: $PYTHON_BIN ($("$PYTHON_BIN" --version))"

print_step "Checking uv"
if ! command_exists uv; then
  cat <<'EOF'
uv is required but not installed.
Install:
curl -LsSf https://astral.sh/uv/install.sh | sh
EOF
  exit 1
fi
echo "uv version: $(uv --version)"

print_step "Syncing dependencies"
SYNC_ARGS=(--dev)
if [[ -f uv.lock ]]; then
  SYNC_ARGS+=(--frozen)
fi
UV_PYTHON="$PYTHON_BIN" uv sync "${SYNC_ARGS[@]}"

print_step "Bootstrapping .env"
if [[ ! -f .env ]]; then
  if [[ -f .env.example ]]; then
    cp .env.example .env
    echo "Created .env from .env.example. Update OPENAI_API_KEY before running the app."
  else
    cat >.env <<'EOF'
OPENAI_API_KEY=your-openai-api-key
REDIS_URL=redis://localhost:6379/0
EOF
    echo "Created .env template. Update OPENAI_API_KEY before running the app."
  fi
else
  echo ".env already exists. Keeping current values."
fi

print_step "Checking optional Redis runtime"
if command_exists redis-server; then
  echo "redis-server detected."
else
  cat <<'EOF'
redis-server is not installed (optional but recommended).
If needed, run Redis via Docker:
docker run --name immcad-redis -p 6379:6379 -d redis:7-alpine
EOF
fi

print_step "Setup complete"
cat <<'EOF'
Next steps:
1. Update OPENAI_API_KEY in .env
2. Verify setup: ./scripts/verify_dev_env.sh
3. Start app: uv run streamlit run app.py
EOF
