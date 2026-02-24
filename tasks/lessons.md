# Lessons Learned

## Session Notes
- No user correction patterns recorded yet for this task.
- User clarified to continue step-by-step in a multi-agent dirty worktree and ignore unrelated concurrent edits.
- Review feedback highlighted that archive module path changes must also preserve internal importability after root-shim removals.

## Reusable Rules
- Verify every legal-source claim with a directly tested endpoint or official policy page.
- Separate technical feasibility from legal permission in documentation.
- In shared/dirty worktrees, scope edits tightly to requested files and avoid touching unrelated agent changes.
- When enforcing hardened runtime config, mirror requirements in CI env blocks and workflow tests in the same change.
- When migrating modules into an archive package, convert internal imports to package-relative imports and add regression tests before removing root compatibility modules.
- When splitting modules and updating package `__init__` exports, ensure newly imported files are tracked/included in the same patch to avoid `ModuleNotFoundError` on clean checkouts.
- For optional auth configuration, gate middleware enforcement on the presence of a configured secret (not just request path) and add tests for both configured and unset modes.
