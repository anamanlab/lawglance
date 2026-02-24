# Ralph in IMMCAD (Codex-first)

This directory contains the Ralph autonomous loop configured for IMMCAD.

## Files

- `ralph.sh` - autonomous iteration loop (`codex` default, also `amp` and `claude`)
- `CODEX.md` - prompt template for Codex
- `CLAUDE.md` - prompt template for Claude Code
- `prompt.md` - prompt template for Amp
- `prd.json` - executable story backlog for the loop
- `progress.txt` - append-only iteration log

## Run

From repo root:

```bash
# Codex default
bash scripts/ralph/ralph.sh 25

# Codex explicit
bash scripts/ralph/ralph.sh --tool codex 25
```

Optional:

```bash
bash scripts/ralph/ralph.sh --tool amp 25
bash scripts/ralph/ralph.sh --tool claude 25
```

Preflight (no iteration execution):

```bash
bash scripts/ralph/ralph.sh --tool codex --check
```

## Setup hardening

- Runner fails fast when the selected prompt file is missing or empty.
- Branch is controlled by `scripts/ralph/prd.json` `branchName`.
- Previous run state is archived under `scripts/ralph/archive/` when branch changes.

If you see prompt errors, validate:

```bash
ls -la scripts/ralph/CODEX.md
```
