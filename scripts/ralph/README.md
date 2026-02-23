# Ralph in IMMCAD

This directory contains a Ralph loop setup adapted for IMMCAD.

## Files

- `ralph.sh` - autonomous iteration loop (`amp` or `claude`)
- `prd.json` - executable story backlog for the loop
- `progress.txt` - append-only iteration log
- `CLAUDE.md` - prompt template for Claude Code
- `prompt.md` - prompt template for Amp

## Run

From repo root:

```bash
bash scripts/ralph/ralph.sh --tool claude 10
```

or

```bash
bash scripts/ralph/ralph.sh --tool amp 10
```

## Notes

- Branch is controlled by `scripts/ralph/prd.json` `branchName`.
- Previous run state is archived under `scripts/ralph/archive/` when branch changes.
- Keep stories small enough for one context window.
