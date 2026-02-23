#!/usr/bin/env bash
# Ralph loop for IMMCAD
# Usage: ./scripts/ralph/ralph.sh [--tool codex|amp|claude] [max_iterations]

set -euo pipefail

TOOL="codex"
MAX_ITERATIONS=10

while [[ $# -gt 0 ]]; do
  case "$1" in
    --tool)
      TOOL="$2"
      shift 2
      ;;
    --tool=*)
      TOOL="${1#*=}"
      shift
      ;;
    *)
      if [[ "$1" =~ ^[0-9]+$ ]]; then
        MAX_ITERATIONS="$1"
      fi
      shift
      ;;
  esac
done

if [[ "$TOOL" != "codex" && "$TOOL" != "amp" && "$TOOL" != "claude" ]]; then
  echo "Error: invalid tool '$TOOL' (must be codex, amp, or claude)"
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PRD_FILE="$SCRIPT_DIR/prd.json"
PROGRESS_FILE="$SCRIPT_DIR/progress.txt"
ARCHIVE_DIR="$SCRIPT_DIR/archive"
LAST_BRANCH_FILE="$SCRIPT_DIR/.last-branch"

if [[ ! -f "$PRD_FILE" ]]; then
  echo "Error: missing $PRD_FILE"
  exit 1
fi

if ! command -v jq >/dev/null 2>&1; then
  echo "Error: jq is required"
  exit 1
fi

if [[ "$TOOL" == "amp" ]] && ! command -v amp >/dev/null 2>&1; then
  echo "Error: amp CLI is not installed"
  exit 1
fi
if [[ "$TOOL" == "codex" ]] && ! command -v codex >/dev/null 2>&1; then
  echo "Error: codex CLI is not installed"
  exit 1
fi
if [[ "$TOOL" == "claude" ]] && ! command -v claude >/dev/null 2>&1; then
  echo "Error: claude CLI is not installed"
  exit 1
fi

if [[ ! -f "$PROGRESS_FILE" ]]; then
  cat > "$PROGRESS_FILE" <<'EOF'
# Ralph Progress Log
Started: INIT

## Codebase Patterns
- Run `make quality` before each commit.
- Keep architecture docs in sync with implementation changes.
- Preserve Canada-only legal scope; avoid India-domain references.

---
EOF
fi

if [[ -f "$LAST_BRANCH_FILE" ]]; then
  CURRENT_BRANCH_FROM_PRD=$(jq -r '.branchName // empty' "$PRD_FILE" 2>/dev/null || echo "")
  LAST_BRANCH=$(cat "$LAST_BRANCH_FILE" 2>/dev/null || echo "")
  if [[ -n "$CURRENT_BRANCH_FROM_PRD" && -n "$LAST_BRANCH" && "$CURRENT_BRANCH_FROM_PRD" != "$LAST_BRANCH" ]]; then
    DATE=$(date +%Y-%m-%d)
    FOLDER_NAME=$(echo "$LAST_BRANCH" | sed 's|^ralph/||')
    ARCHIVE_FOLDER="$ARCHIVE_DIR/$DATE-$FOLDER_NAME"
    mkdir -p "$ARCHIVE_FOLDER"
    cp "$PRD_FILE" "$ARCHIVE_FOLDER/prd.json"
    cp "$PROGRESS_FILE" "$ARCHIVE_FOLDER/progress.txt"
  fi
fi

TARGET_BRANCH=$(jq -r '.branchName // empty' "$PRD_FILE")
if [[ -z "$TARGET_BRANCH" ]]; then
  echo "Error: branchName missing in prd.json"
  exit 1
fi

cd "$REPO_ROOT"
CURRENT_GIT_BRANCH=$(git branch --show-current)
if [[ "$CURRENT_GIT_BRANCH" != "$TARGET_BRANCH" ]]; then
  if git show-ref --verify --quiet "refs/heads/$TARGET_BRANCH"; then
    git checkout "$TARGET_BRANCH"
  else
    if git show-ref --verify --quiet "refs/remotes/origin/main"; then
      git checkout -b "$TARGET_BRANCH" origin/main
    else
      git checkout -b "$TARGET_BRANCH" main
    fi
  fi
fi

echo "$TARGET_BRANCH" > "$LAST_BRANCH_FILE"

echo "Starting Ralph for IMMCAD (tool=$TOOL, iterations=$MAX_ITERATIONS, branch=$TARGET_BRANCH)"

DONE_COUNT=$(jq '[.userStories[] | select(.passes==true)] | length' "$PRD_FILE")
TOTAL_COUNT=$(jq '.userStories | length' "$PRD_FILE")
if [[ "$TOTAL_COUNT" -gt 0 && "$DONE_COUNT" -eq "$TOTAL_COUNT" ]]; then
  echo "All PRD stories are already complete ($DONE_COUNT/$TOTAL_COUNT)."
  echo "<promise>COMPLETE</promise>"
  exit 0
fi

PROMPT_FILE="$SCRIPT_DIR/prompt.md"
if [[ "$TOOL" == "codex" ]]; then
  PROMPT_FILE="$SCRIPT_DIR/CODEX.md"
elif [[ "$TOOL" == "claude" ]]; then
  PROMPT_FILE="$SCRIPT_DIR/CLAUDE.md"
fi

for i in $(seq 1 "$MAX_ITERATIONS"); do
  echo
  echo "==============================================================="
  echo "  Ralph Iteration $i/$MAX_ITERATIONS ($TOOL)"
  echo "==============================================================="

  LAST_MESSAGE_FILE=""
  if [[ "$TOOL" == "amp" ]]; then
    OUTPUT=$(cat "$PROMPT_FILE" | amp --dangerously-allow-all 2>&1 | tee /dev/stderr) || true
  elif [[ "$TOOL" == "codex" ]]; then
    LAST_MESSAGE_FILE=$(mktemp)
    OUTPUT=$(cat "$PROMPT_FILE" | codex exec --color never --dangerously-bypass-approvals-and-sandbox --output-last-message "$LAST_MESSAGE_FILE" 2>&1 | tee /dev/stderr) || true
  else
    OUTPUT=$(claude --dangerously-skip-permissions --print < "$PROMPT_FILE" 2>&1 | tee /dev/stderr) || true
  fi

  if [[ "$TOOL" == "codex" ]]; then
    if [[ -n "$LAST_MESSAGE_FILE" && -f "$LAST_MESSAGE_FILE" ]] && grep -q "<promise>COMPLETE</promise>" "$LAST_MESSAGE_FILE"; then
      rm -f "$LAST_MESSAGE_FILE"
      echo
      echo "Ralph completed all tasks at iteration $i."
      exit 0
    fi
    rm -f "$LAST_MESSAGE_FILE"
  elif echo "$OUTPUT" | grep -q "<promise>COMPLETE</promise>"; then
    echo
    echo "Ralph completed all tasks at iteration $i."
    exit 0
  fi

  DONE_COUNT=$(jq '[.userStories[] | select(.passes==true)] | length' "$PRD_FILE")
  TOTAL_COUNT=$(jq '.userStories | length' "$PRD_FILE")
  if [[ "$TOTAL_COUNT" -gt 0 && "$DONE_COUNT" -eq "$TOTAL_COUNT" ]]; then
    echo
    echo "Ralph detected all tasks complete from PRD state at iteration $i."
    echo "<promise>COMPLETE</promise>"
    exit 0
  fi
  echo "Progress: $DONE_COUNT/$TOTAL_COUNT stories complete"

  sleep 2
done

echo

echo "Ralph reached max iterations without full completion."
exit 1
