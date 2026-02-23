#!/usr/bin/env bash
set -euo pipefail

if git ls-files --error-unmatch .env >/dev/null 2>&1; then
  echo "ERROR: .env is tracked in git. Run: git rm --cached .env"
  exit 1
fi

# Basic high-risk secret pattern scan on tracked files.
if git grep -nE 'AIza[0-9A-Za-z_-]{35}|sk-[A-Za-z0-9]{20,}' -- . ':(exclude).env.example' >/dev/null; then
  echo "ERROR: Potential API secret detected in tracked files."
  echo "Review matches with: git grep -nE 'AIza[0-9A-Za-z_-]{35}|sk-[A-Za-z0-9]{20,}'"
  exit 1
fi

echo "[OK] Repository hygiene checks passed."
