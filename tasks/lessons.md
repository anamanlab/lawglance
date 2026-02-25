# Lessons Learned

## Session Notes
- No user correction patterns recorded yet for this task.
- User clarified to continue step-by-step in a multi-agent dirty worktree and ignore unrelated concurrent edits.
- Review feedback highlighted that archive module path changes must also preserve internal importability after root-shim removals.
- User correction: initial auth fix was too superficial because it patched only frontend behavior without fully reconciling backend env alias handling and test/env drift paths.
- User correction: do a stricter self-review ("do not lie, find issues/bugs and make further improvements") before finalizing plans or implementations.

## Reusable Rules
- Verify every legal-source claim with a directly tested endpoint or official policy page.
- Separate technical feasibility from legal permission in documentation.
- In shared/dirty worktrees, scope edits tightly to requested files and avoid touching unrelated agent changes.
- When enforcing hardened runtime config, mirror requirements in CI env blocks and workflow tests in the same change.
- When migrating modules into an archive package, convert internal imports to package-relative imports and add regression tests before removing root compatibility modules.
- When splitting modules and updating package `__init__` exports, ensure newly imported files are tracked/included in the same patch to avoid `ModuleNotFoundError` on clean checkouts.
- For optional auth configuration, gate middleware enforcement on the presence of a configured secret (not just request path) and add tests for both configured and unset modes.
- For auth/config incidents, perform cross-stack closure (frontend proxy, backend settings, env templates, docs, and tests) before marking complete.
- When introducing env aliases, add explicit mismatch detection when both variables are set and extend tests to clear ambient env vars to avoid false confidence.
- For ranking heuristics, avoid negative boosts that can erase literal query matches; add regression tests for domain terms that previously got suppressed.
- For multi-source caches, track freshness per source ID; never use a single global refresh timestamp when requests can target different source subsets.
- When user asks for production finalization, prioritize direct blocker remediation with verified fixes over status-heavy summaries.
- After editing mirrored data assets (not just Python sources), run mirror-sync checks and full tests to catch backend-vercel drift early.
- For shell gate scripts, add explicit behavioral tests for success/failure/error exit-code branches to prevent CI contract regressions.
- Close checklist gates only after running the exact verification commands; idempotence regressions (for example TOC spacing drift) are easiest to catch with targeted tests before full-suite runs.
- When typecheck is part of release gates, keep the typechecker in dev dependencies and make local `typecheck` targets fail fast if the tool is missing.
- Before marking work complete, run an explicit adversarial review pass on your own changes and patch any real issues found (incorrect commands, false-positive risks, or verification gaps).
