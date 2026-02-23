# Ingestion Checkpoint Recovery Runbook

Use this runbook to recover Canada ingestion checkpoint state after file corruption or unexpected runner failures.

## Checkpoint File Location

- Default checkpoint file: `artifacts/ingestion/checkpoints.json`
- Default runner command: `uv run python scripts/run_ingestion_jobs.py --cadence <cadence>`
- Override location with `--state-path <path>` when needed.

The ingestion runner reads checkpoint state before fetching and writes updated state after execution. If the checkpoint file is missing, the runner starts with empty state and performs a full refresh.

## When to Use This

Run this procedure when:

- ingestion exits with JSON decode/parsing errors for checkpoint state;
- checkpoint content is truncated or malformed;
- checkpoint metadata is inconsistent after interrupted writes.

## Recovery Procedure

1. Pause scheduled ingestion triggers so no concurrent job writes to checkpoint state.
2. Back up the current checkpoint file (if present):

```bash
ts="$(date -u +%Y%m%dT%H%M%SZ)"
if [ -f artifacts/ingestion/checkpoints.json ]; then
  mv artifacts/ingestion/checkpoints.json "artifacts/ingestion/checkpoints.corrupt.${ts}.json"
fi
```

3. Replay ingestion to rebuild checkpoint state:

```bash
uv run python scripts/run_ingestion_jobs.py \
  --cadence all \
  --state-path artifacts/ingestion/checkpoints.json \
  --output "artifacts/ingestion/ingestion-recovery-${ts}.json" \
  --fail-on-error
```

4. If you must replay by cadence (for targeted recovery), run:

```bash
for cadence in daily weekly scheduled_incremental; do
  uv run python scripts/run_ingestion_jobs.py \
    --cadence "$cadence" \
    --state-path artifacts/ingestion/checkpoints.json \
    --output "artifacts/ingestion/ingestion-recovery-${cadence}-${ts}.json" \
    --fail-on-error
done
```

## Verification Checklist

- [ ] Recovery replay exits successfully (`exit 0`).
- [ ] Replay report shows zero failed sources:

```bash
jq '.failed' "artifacts/ingestion/ingestion-recovery-${ts}.json"
```

- [ ] Checkpoint JSON is valid and has expected top-level keys:

```bash
jq -e '.version == 1 and (.checkpoints | type == "object")' artifacts/ingestion/checkpoints.json >/dev/null
```

- [ ] Checkpoint entries were repopulated:

```bash
jq '.checkpoints | keys | length' artifacts/ingestion/checkpoints.json
```

- [ ] Follow-up incremental run completes and produces expected `not_modified`/`success` statuses.
- [ ] Corrupted checkpoint snapshot and replay report are retained for incident review.

## Notes

- Keep this recovery flow scoped to Canada ingestion sources only.
- Do not manually edit checkpoint fields unless incident response requires forensic correction.
