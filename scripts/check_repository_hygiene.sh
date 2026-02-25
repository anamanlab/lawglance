#!/usr/bin/env bash
set -euo pipefail

list_tracked_plaintext_env_files() {
  git ls-files 2>/dev/null | while IFS= read -r path; do
    base_name="${path##*/}"
    case "$base_name" in
      .env)
        printf '%s\n' "$path"
        ;;
      .env.*)
        case "$base_name" in
          .env.example | *.secret)
            continue
            ;;
        esac
        printf '%s\n' "$path"
        ;;
    esac
  done
}

filter_secret_scan_matches() {
  while IFS= read -r line; do
    case "$line" in
      *.env.example:* | \
      *.secret:* | \
      Binary\ file\ *.secret\ matches | \
      .gitsecret/*:* | \
      Binary\ file\ .gitsecret/*\ matches)
        continue
        ;;
    esac
    printf '%s\n' "$line"
  done
}

if git ls-files --error-unmatch .env >/dev/null 2>&1; then
  echo "ERROR: .env is tracked in git. Run: git rm --cached .env"
  exit 1
fi

if git ls-files --error-unmatch .gitsecret/keys/random_seed >/dev/null 2>&1; then
  echo "ERROR: .gitsecret/keys/random_seed is tracked in git. Run: git rm --cached .gitsecret/keys/random_seed"
  exit 1
fi

tracked_plaintext_env_files=""
if tracked_plaintext_env_files="$(list_tracked_plaintext_env_files)"; then
  if [ -n "$tracked_plaintext_env_files" ]; then
    echo "ERROR: Found tracked plaintext .env files (excluding templates/encrypted artifacts)."
    echo "$tracked_plaintext_env_files"
    echo "Remediation: git rm --cached <path> (keep templates as .env.example and encrypted files as *.secret)"
    exit 1
  fi
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
    filtered_grep_output="$(printf '%s\n' "$grep_output" | filter_secret_scan_matches)"
    if [ -z "$filtered_grep_output" ]; then
      echo "[OK] Repository hygiene checks passed."
      exit 0
    fi
    echo "ERROR: Potential API secret detected in tracked files."
    echo "$filtered_grep_output"
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
