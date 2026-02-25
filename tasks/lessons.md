# Lessons Learned

## Session Notes
- No user correction patterns recorded yet for this task.
- User clarified to continue step-by-step in a multi-agent dirty worktree and ignore unrelated concurrent edits.
- Review feedback highlighted that archive module path changes must also preserve internal importability after root-shim removals.
- Reviewer-identified P1 mismatch confirmed a key risk: hardened-environment alias rules must be shared consistently between backend and frontend runtime codepaths.
- Case-law chat integration work exposed a policy coupling: tool-generated official court citations can be dropped unless trusted-domain defaults include official feed hosts.
- User correction (2026-02-25): E2E setup must be resilient on headless servers and use Context7 documentation when requested.

## Reusable Rules
- Verify every legal-source claim with a directly tested endpoint or official policy page.
- Separate technical feasibility from legal permission in documentation.
- In shared/dirty worktrees, scope edits tightly to requested files and avoid touching unrelated agent changes.
- When enforcing hardened runtime config, mirror requirements in CI env blocks and workflow tests in the same change.
- For Vercel backend releases, avoid stale local `--prebuilt` artifacts unless they are freshly generated and audited; prebuilt manifests can pin deprecated runtimes and reference local `.env` files.
- For Vercel official Python runtime pinning, prefer project-root `.python-version` (or `pyproject.toml`) over forcing `functions.runtime` strings in `vercel.json`.
- When migrating modules into an archive package, convert internal imports to package-relative imports and add regression tests before removing root compatibility modules.
- When splitting modules and updating package `__init__` exports, ensure newly imported files are tracked/included in the same patch to avoid `ModuleNotFoundError` on clean checkouts.
- For optional auth configuration, gate middleware enforcement on the presence of a configured secret (not just request path) and add tests for both configured and unset modes.
- Keep exactly one active "Current Focus" plan block at the top of `tasks/todo.md`; archive or delete duplicate active-plan sections to avoid conflicting execution signals.
- If GitHub Issues are disabled, maintain a repo-local known-issues log in `docs/release/` with owners, severity, and status so production risks still have a canonical tracker.
- Close or reuse spawned agents after each major workstream; orphaned agent threads can hit the session cap and block parallel explorer workflows.
- In dirty multi-agent worktrees, scanning gates that enforce repository policy should default to tracked files only to avoid unrelated untracked artifacts creating false release blockers.
- Do not run frontend `typecheck` and `build` in parallel when `.next/types` is included in TypeScript config; run typecheck after build or serially to avoid transient missing-file errors.
- When introducing environment hardening wildcard support, enforce one canonical matcher pattern across backend settings, backend runtime behavior, frontend runtime config, and tests.
- When adding new retrieval/tool citation sources, update default trust policy and regression tests in the same PR so valid citations are not silently downgraded.
- For high-risk actions like document export, convert client-only approval flags into server-issued signed approval artifacts (short-lived tokens) at least in hardened environments.
- When users report intermittent frontend "Unexpected error" behavior in Next.js dev mode, check for `.next` module-cache corruption (`Cannot find module './*.js'`) and restart dev after rotating stale `.next` cache.
- For debugability and support operations, ensure frontend failure paths always surface a non-empty trace identifier (proxy header or client-generated fallback) instead of "Trace ID: Unavailable".
- For Playwright on headless Linux servers, default local project selection to Chromium/Firefox/Mobile Chrome and keep WebKit/Safari as explicit opt-in or CI jobs that install dependencies with `playwright install --with-deps`.
- When asked to use Context7, resolve the library first and anchor setup decisions in retrieved docs before implementing config changes.
- Do not return synthetic scaffold case-search results when backend case services are unreachable; surface structured `SOURCE_UNAVAILABLE` errors so users are not misled by non-exportable fake cases.
- Do not enable frontend chat scaffold fallback implicitly; require explicit env opt-in so backend misconfiguration is visible instead of silently masked.
- For user-facing case-search failures, map structured validation/policy errors to actionable UI guidance instead of generic "temporarily unavailable" copy.
- In dual-service chat + case-search UIs, always show whether displayed results correspond to the current query or a previous query to prevent stale-context confusion.
- If subagent spawn fails due thread-cap limits, do not stall implementation; report the limit once, continue sequential execution, and close any known agent IDs as soon as they are no longer needed.
- For Cloudflare cutovers, always record Worker version IDs, check custom-domain DNS from public resolvers (`1.1.1.1`/`8.8.8.8`), and keep a `workers.dev` fallback path active until 24h observation evidence is captured.
- Before any production deploy sequence, run an explicit clean-worktree preflight (`make release-preflight`) so migration evidence is not mixed with unrelated local edits.
- For Cloudflare Python Worker rollouts, keep migration staged: land scaffold + workflow tests first, then validate with authenticated perf smoke (`make backend-cf-perf-smoke`) before attempting full traffic cutover.
- Always run at least one real canary deploy attempt after scaffolding; local tests can pass while platform limits (for example Cloudflare Worker bundle-size `code: 10027`) block production viability.
- When reporting a production blocker to the user, implement at least one concrete mitigation in the same pass (for example a preflight gate, safer fallback path, or runbook check), not just a diagnosis.
- When wrapping synchronous service calls with `run_in_threadpool`, keep explicit `ApiError` handling in the route; otherwise `RateLimitError`/`SourceUnavailableError` can leak as raw 500s.
- During edge-proxy migrations, keep error envelope and trace-header contracts aligned with frontend parsing (`error.code` + `trace_id` + `x-trace-id`) and maintain temporary client-side fallback for legacy proxy shapes.
- For lawyer-research `source_status`, avoid hardcoded official source-id lists; prefer registry-driven classification so new official case-law sources are not misreported as unknown.
- Treat edge proxy contract checks as a preflight gate (script + CI workflow step), not just a unit test, so release/deploy paths fail fast when worker headers/envelope drift from frontend expectations.
