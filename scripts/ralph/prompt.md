# Ralph Agent Instructions (IMMCAD / Amp)

You are an autonomous coding agent working on IMMCAD.

## Loop

1. Read `scripts/ralph/prd.json`.
2. Read `scripts/ralph/progress.txt`.
3. Ensure branch matches `branchName` from PRD.
4. Execute one highest-priority story with `passes: false`.
5. Run `make quality`.
6. Commit with `feat: [Story ID] - [Story Title]`.
7. Set the story `passes: true` in `scripts/ralph/prd.json`.
8. Append learnings to `scripts/ralph/progress.txt`.

If all stories pass, output exactly:

`<promise>COMPLETE</promise>`
