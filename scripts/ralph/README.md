# Ralph in IMMCAD (Codex-First)

This is an IMMCAD adaptation of upstream Ralph (`https://github.com/snarktank/ralph`) with first-class `codex` support.

## Prerequisites

- `codex` CLI installed and authenticated
- `jq` installed
- git repo with `scripts/ralph/prd.json`

## Files

- `ralph.sh`: autonomous loop (`codex` default, also `amp|claude`)
- `CODEX.md`: Codex prompt template used by `--tool codex`
- `CLAUDE.md`: Claude template (optional)
- `prompt.md`: Amp template (optional)
- `prd.json`: executable story backlog
- `progress.txt`: append-only run memory

## Install / Verify

```bash
chmod +x scripts/ralph/ralph.sh
codex --version
jq --version
```

## Run

```bash
# Codex (default)
bash scripts/ralph/ralph.sh 10

# Codex (explicit)
bash scripts/ralph/ralph.sh --tool codex 10
```

Optional:

```bash
bash scripts/ralph/ralph.sh --tool amp 10
bash scripts/ralph/ralph.sh --tool claude 10
```

## Behavior Notes

- Branch is controlled by `scripts/ralph/prd.json` `branchName`.
- Previous run state is archived under `scripts/ralph/archive/` when branch changes.
- Script short-circuits with `<promise>COMPLETE</promise>` when all stories are already `passes: true`.
