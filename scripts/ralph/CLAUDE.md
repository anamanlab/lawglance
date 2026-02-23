# Ralph Agent Instructions (IMMCAD)

You are an autonomous coding agent working on IMMCAD.

## Task Loop

1. Read `scripts/ralph/prd.json`.
2. Read `scripts/ralph/progress.txt` (start with `## Codebase Patterns`).
3. Ensure you are on `branchName` from PRD (create from `main` if missing).
4. Pick the highest-priority story where `passes: false`.
5. Implement exactly one story.
6. Run quality checks:
   - `make quality`
7. Update nearby `AGENTS.md` only when learnings are reusable.
8. Commit all changes with: `feat: [Story ID] - [Story Title]`.
9. Update that story in `scripts/ralph/prd.json` to `passes: true`.
10. Append progress to `scripts/ralph/progress.txt`.

## Progress Entry Format

Append:

```text
## [Date/Time] - [Story ID]
- What was implemented
- Files changed
- Learnings for future iterations:
  - Reusable pattern
  - Gotcha
  - Useful context
---
```

## Constraints

- One story per iteration.
- Keep changes minimal and verifiable.
- Never skip `make quality`.
- Preserve Canada-only legal scope.

## Browser Verification

If story changes UI, include and execute:
- `Verify in browser using dev-browser skill`

## Stop Condition

If all stories in `scripts/ralph/prd.json` have `passes: true`, output:

```text
<promise>COMPLETE</promise>
```
