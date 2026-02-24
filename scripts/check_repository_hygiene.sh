#!/usr/bin/env bash
set -euo pipefail

if git ls-files --error-unmatch .env >/dev/null 2>&1; then
  echo "ERROR: .env is tracked in git. Run: git rm --cached .env"
  exit 1
fi

# High-risk secret pattern scan on tracked files.
SECRET_PATTERN='AIza[0-9A-Za-z_-]{35}|sk-[A-Za-z0-9]{20,}|sk-proj-[A-Za-z0-9_-]{20,}|AKIA[0-9A-Z]{16}|gh[pousr]_[A-Za-z0-9]{36,}|xox[baprs]-[A-Za-z0-9-]{10,}'
grep_output=""
if grep_output="$(git grep -nE "$SECRET_PATTERN" -- . ':(exclude).env.example' 2>&1)"; then
  grep_rc=0
else
  grep_rc=$?
fi

case "$grep_rc" in
  0)
    echo "ERROR: Potential API secret detected in tracked files."
    echo "$grep_output"
    echo "Review matches with: git grep -nE \"$SECRET_PATTERN\" -- . ':(exclude).env.example'"
    exit 1
    ;;
  1)
    # No matches found.
    ;;
  *)
    echo "ERROR: git grep failed during secret scan (exit code: $grep_rc)"
    echo "Command: git grep -nE \"$SECRET_PATTERN\" -- . ':(exclude).env.example'"
    if [ -n "$grep_output" ]; then
      echo "$grep_output"
    fi
    exit 2
    ;;
esac

echo "[OK] Repository hygiene checks passed."
