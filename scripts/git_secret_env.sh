#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

RUNBOOK_PATH="docs/release/git-secret-runbook.md"

command_exists() {
  command -v "$1" >/dev/null 2>&1
}

git_secret_available() {
  if command_exists git-secret; then
    return 0
  fi
  git secret --version >/dev/null 2>&1
}

default_gpg_cmd() {
  if [[ -n "${SECRETS_GPG_COMMAND:-}" ]]; then
    printf '%s\n' "$SECRETS_GPG_COMMAND"
    return 0
  fi
  printf 'gpg\n'
}

print_install_help() {
  cat <<EOF
git-secret is not installed.

This repo treats git-secret as optional unless you need to reveal/edit encrypted repo-stored env bundles.
See: ${RUNBOOK_PATH}

Install prerequisites:
- gpg (GnuPG)
- git-secret

Examples:
- macOS (Homebrew): brew install git-secret
- Linux: use your distro package or a pinned/manual install method (see upstream docs + repo runbook)
EOF
}

print_usage() {
  cat <<EOF
Usage: scripts/git_secret_env.sh <command> [args...]

Commands:
  check     Print git-secret/gpg availability and repo initialization status
  reveal    Run: git secret reveal [args...]
  hide      Run: git secret hide [args...]
  list      Run: git secret list [args...]
  changes   Run: git secret changes [args...]

Notes:
- git-secret is optional in IMMCAD unless you are working with encrypted repo-stored env bundles.
- Production runtime secrets remain in GitHub/Vercel secret managers.
- Runbook: ${RUNBOOK_PATH}
EOF
}

require_git_secret() {
  if git_secret_available; then
    return 0
  fi
  print_install_help
  exit 1
}

require_gpg() {
  local gpg_cmd
  gpg_cmd="$(default_gpg_cmd)"
  if command_exists "$gpg_cmd"; then
    return 0
  fi
  cat <<EOF
Configured GPG command not found: ${gpg_cmd}

Install GnuPG or set SECRETS_GPG_COMMAND to a valid executable.
Runbook: ${RUNBOOK_PATH}
EOF
  exit 1
}

print_check_status() {
  local gpg_cmd
  local repo_status

  gpg_cmd="$(default_gpg_cmd)"

  echo "IMMCAD git-secret helper"
  echo "Repo: ${ROOT_DIR}"
  echo "Runbook: ${RUNBOOK_PATH}"
  echo

  if git_secret_available; then
    echo "[OK] git-secret: $(git secret --version)"
  else
    echo "[WARN] git-secret: not installed (optional unless you work with encrypted repo-stored env bundles)"
  fi

  if command_exists "$gpg_cmd"; then
    echo "[OK] ${gpg_cmd}: $("${gpg_cmd}" --version | head -n1)"
  else
    echo "[WARN] ${gpg_cmd}: not found"
  fi

  if [[ -d .gitsecret ]]; then
    repo_status="initialized"
    echo "[INFO] .gitsecret/: present (${repo_status})"
  else
    repo_status="not initialized"
    echo "[INFO] .gitsecret/: not present (${repo_status})"
  fi

  echo
  echo "Note: IMMCAD uses platform-managed runtime secrets (GitHub/Vercel) for production."
}

require_initialized_repo() {
  if [[ -d .gitsecret ]]; then
    return 0
  fi
  cat <<EOF
This repository is not initialized for git-secret (.gitsecret/ not found).

If you intend to enable the workflow, follow: ${RUNBOOK_PATH}
EOF
  exit 1
}

cmd="${1:-check}"
if [[ $# -gt 0 ]]; then
  shift
fi

case "$cmd" in
  check)
    print_check_status
    ;;
  reveal | hide | list | changes)
    require_git_secret
    require_gpg
    require_initialized_repo
    exec git secret "$cmd" "$@"
    ;;
  -h | --help | help)
    print_usage
    ;;
  *)
    echo "Unknown command: $cmd" >&2
    print_usage
    exit 2
    ;;
esac
