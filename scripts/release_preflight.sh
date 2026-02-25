#!/usr/bin/env bash
set -euo pipefail

ALLOW_DIRTY=0
SKIP_WRANGLER_AUTH_CHECK="${SKIP_WRANGLER_AUTH_CHECK:-0}"
SKIP_CLOUDFLARE_FREE_PLAN_CHECK="${SKIP_CLOUDFLARE_FREE_PLAN_CHECK:-0}"
SKIP_CLOUDFLARE_EDGE_CONTRACT_CHECK="${SKIP_CLOUDFLARE_EDGE_CONTRACT_CHECK:-0}"

while (($# > 0)); do
  case "$1" in
    --allow-dirty)
      ALLOW_DIRTY=1
      shift
      ;;
    *)
      echo "Unknown argument: $1" >&2
      echo "Usage: $0 [--allow-dirty]" >&2
      exit 2
      ;;
  esac
done

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "ERROR: release preflight must run inside a git repository."
  exit 1
fi

branch_name="$(git rev-parse --abbrev-ref HEAD)"
echo "[INFO] Branch: ${branch_name}"

if [ "$ALLOW_DIRTY" -ne 1 ]; then
  if ! git diff --quiet || ! git diff --cached --quiet || [ -n "$(git ls-files --others --exclude-standard)" ]; then
    echo "ERROR: Working tree is not clean."
    echo "Run 'git status --short' and commit/stash/remove local changes before release preflight."
    echo "Use '--allow-dirty' only for diagnostic runs (never for production deploy execution)."
    exit 1
  fi
fi

echo "[INFO] Running repository hygiene checks..."
bash scripts/check_repository_hygiene.sh

if [ "$SKIP_CLOUDFLARE_FREE_PLAN_CHECK" != "1" ]; then
  echo "[INFO] Running Cloudflare free-plan readiness checks..."
  bash scripts/check_cloudflare_free_plan_readiness.sh
else
  echo "[WARN] Skipping Cloudflare free-plan readiness checks (SKIP_CLOUDFLARE_FREE_PLAN_CHECK=1)."
fi

if [ "$SKIP_CLOUDFLARE_EDGE_CONTRACT_CHECK" != "1" ]; then
  echo "[INFO] Running Cloudflare edge-proxy contract checks..."
  bash scripts/check_cloudflare_edge_proxy_contract.sh
else
  echo "[WARN] Skipping Cloudflare edge-proxy contract checks (SKIP_CLOUDFLARE_EDGE_CONTRACT_CHECK=1)."
fi

echo "[INFO] Verifying Wrangler CLI availability..."
npx --yes wrangler@4.68.1 --version >/dev/null

if [ "$SKIP_WRANGLER_AUTH_CHECK" != "1" ]; then
  echo "[INFO] Verifying Cloudflare authentication..."
  npx --yes wrangler@4.68.1 whoami >/dev/null
else
  echo "[WARN] Skipping Wrangler authentication check (SKIP_WRANGLER_AUTH_CHECK=1)."
fi

echo "[OK] Release preflight checks passed."
