# Developer Onboarding Guide (IMMCAD)

Last updated: 2026-02-24

This guide is the entry point for engineers joining IMMCAD (Canada immigration legal information assistant). It complements existing setup and architecture docs with a practical onboarding path, role-specific learning tracks, and first-task milestones.

Use this guide with:

- `README.md` for product/project context
- `docs/development-environment.md` for local environment setup details
- `docs/architecture/README.md` for system architecture docs
- `AGENTS.md` for repository-specific engineering workflow rules (if using AI coding agents)

## 1. Onboarding Requirements Analysis

### Project context (what you are joining)

IMMCAD is an AI-assisted legal information product focused on Canadian immigration law. The current production path is:

- Next.js frontend: `frontend-web`
- Python API backend (FastAPI): `src/immcad_api`
- Observability and quality/reporting scripts: `scripts/`, `artifacts/`
- Legal/source governance assets: `config/`, `data/sources/`, `docs/release/`

There is also legacy code retained for migration and troubleshooting:

- Streamlit UI: `app.py`
- Legacy RAG modules: `lawglance_main.py`, `chains.py`, `cache.py`, `prompts.py`

### Key knowledge areas for new contributors

- Backend/API: FastAPI routing, request middleware, error envelopes, provider routing, source policy enforcement
- Frontend: Next.js app, API contract consumption, auth headers, error/trace-id handling
- Legal/data compliance: source registry, source policy, CanLII constraints, disclaimer behavior
- Quality/release: CI quality gates, jurisdictional evaluation suite, runbooks, architecture docs

### Common onboarding pain points (likely)

- Two runtime paths exist (production path vs legacy path)
- Repo contains both active code and legacy/notebook artifacts
- Quality checks are broader than simple unit tests (`make quality` runs many validations)
- Legal/compliance constraints affect implementation choices (especially sources/citations/exports)

### Suggested onboarding timeline (role-agnostic baseline)

- Day 0: Access requests, local tool installation, repository clone
- Day 1: Local environment setup, run API/frontend, read architecture overview
- Days 2-3: Run quality checks, trace a request through backend/frontend, complete a guided exercise
- Days 4-5: Ship a small documentation/test-only PR
- Week 2: Ship a scoped code change in your primary role area (backend/frontend/data/ops)

### Role tracks (pick one primary, one secondary)

- Backend/API engineer
- Frontend engineer
- Data ingestion / source governance engineer
- Platform / release / ops engineer
- QA / reliability-focused contributor

## 2. Development Environment Setup Guide

This repo already has a strong setup flow. Use the existing scripts first.

### System requirements

- OS: Linux/macOS (Windows via WSL recommended)
- Python: `3.11+`
- `uv` package manager/runtime wrapper
- Node.js: `20+` (for `frontend-web`)
- Optional but recommended: Redis
- Recommended: `gh` (GitHub CLI), `jq`, Docker

### Quick start (recommended)

From repo root:

```bash
make setup
make verify
```

Then start the production runtime:

```bash
# Terminal 1
make api-dev

# Terminal 2
make frontend-install
make frontend-dev
```

Primary local URLs:

```text
Frontend: http://127.0.0.1:3000
API:      http://127.0.0.1:8000
Health:   http://127.0.0.1:8000/healthz
```

### Environment variables

Minimum local requirement:

```dotenv
OPENAI_API_KEY=...
```

Recommended:

```dotenv
REDIS_URL=redis://localhost:6379/0
```

Production/CI hardening notes:

- `IMMCAD_API_BEARER_TOKEN` is required in `ENVIRONMENT=production|prod|ci` (`API_BEARER_TOKEN` is accepted as a compatibility alias)
- `ALLOW_SCAFFOLD_SYNTHETIC_CITATIONS` must be disabled in hardened modes
- Never commit `.env` files

### Frontend environment (production path)

Create `frontend-web/.env.local`:

```dotenv
NEXT_PUBLIC_IMMCAD_API_BASE_URL=/api
IMMCAD_API_BASE_URL=http://127.0.0.1:8000
IMMCAD_API_BEARER_TOKEN=your-api-bearer-token
```

### Environment validation and troubleshooting

Use the built-in scripts:

- `make verify`
- `./scripts/verify_dev_env.sh`

Key troubleshooting docs:

- `docs/development-environment.md`
- `docs/release/git-secret-runbook.md` (only if the team is using encrypted repo-stored env bundles; does not replace GitHub/Vercel runtime secrets)

## 3. Project and Codebase Overview

### Business and product scope

- IMMCAD provides informational guidance for Canadian immigration workflows
- It is not legal advice
- Accuracy, citation quality, and policy-safe behavior are core requirements

### Technology stack (current)

- Backend: Python, FastAPI, Pydantic, Uvicorn
- AI/provider routing: OpenAI + Gemini abstractions
- Frontend: Next.js (TypeScript)
- Data/RAG components: LangChain, Chroma (mixed active + legacy paths)
- Caching/state helpers: Redis (optional for local)
- Tooling: `uv`, `ruff`, `pytest`, GitHub Actions

### Codebase map (high-value paths)

- `src/immcad_api/main.py`: app factory, middleware, exception handlers, router wiring
- `src/immcad_api/api/routes/`: HTTP endpoints (`chat`, `cases`, etc.)
- `src/immcad_api/services/`: business logic / orchestration layer
- `src/immcad_api/schemas.py`: API request/response contracts and error envelope
- `src/immcad_api/policy/`: compliance logic, prompts, source policy checks
- `src/immcad_api/sources/`: source clients + source registry loading
- `frontend-web/`: production frontend
- `tests/`: API contract and behavior tests
- `config/`: prompts, source policy, operational thresholds
- `data/sources/canada-immigration/`: canonical source registry
- `docs/architecture/`: authoritative architecture documentation
- `docs/release/`: operational and compliance runbooks

### How to explore the codebase (recommended order)

1. `README.md`
2. `docs/architecture/README.md`
3. `docs/architecture/api-contracts.md`
4. `docs/development-environment.md`
5. `src/immcad_api/main.py`
6. `src/immcad_api/api/routes/chat.py` and `src/immcad_api/api/routes/cases.py`
7. `tests/test_api_scaffold.py`

## 4. Development Workflow Documentation

### Version control and branching

Recommended branch naming:

- `feat/<scope>`
- `fix/<scope>`
- `chore/<scope>`

Conventional commit style is preferred:

- `feat(api): add policy-gated source export endpoint`
- `fix(policy): block unsupported source export`

### Worktree workflow (recommended for parallel work)

This repo commonly uses local worktrees for isolated feature work.

Example:

```bash
git worktree add .worktrees/<branch-name> -b <branch-name>
```

Notes:

- `.worktrees/` is the preferred local directory when present
- Verify baseline tests before implementing changes
- Keep worktree cleanup explicit (do not auto-delete active worktrees)

### Local quality workflow

Fast loop (backend-focused):

```bash
make lint-api
make test
```

Full project quality gates (mirrors CI intent):

```bash
make quality
```

Notes:

- `make lint-api` is the preferred lint command for active backend/test work
- `make lint` scans the entire repository (including legacy/notebook artifacts) and may produce extra noise

### PR workflow

Before PR:

- Run relevant tests (`make test` minimum; `make quality` when touching compliance/architecture paths)
- Update docs if behavior/contracts changed
- Include test evidence in PR description
- Include screenshots for frontend changes

### CI/CD overview (GitHub Actions)

Key workflows:

- `.github/workflows/quality-gates.yml`
- `.github/workflows/release-gates.yml`
- `.github/workflows/codeql.yml`
- `.github/workflows/staging-smoke.yml`
- `.github/workflows/ingestion-jobs.yml`
- `.github/workflows/architecture-docs.yml`
- `.github/workflows/canlii-live-smoke.yml`

What `quality-gates` validates (high level):

- Python + frontend build/typecheck/tests
- backend lint/tests
- architecture docs validation
- source registry validation
- legal review checklist validation
- domain leak scanning
- jurisdiction evaluation + behavior suite
- repository hygiene checks

## 5. Team Communication and Collaboration

This section is intentionally structured as a fill-in template because org-specific details are not in the repository.

### Communication channels (fill in)

- Engineering chat: `<Slack/Teams channel>`
- Incidents/on-call: `<channel + escalation alias>`
- Product/legal coordination: `<channel>`
- Async updates: `<issue tracker / project board>`

### Meeting cadence (fill in)

- Daily/weekly engineering sync: `<day/time/timezone>`
- Release readiness review: `<cadence>`
- Architecture review / ADR review: `<cadence>`
- Legal/compliance check-in: `<cadence>`

### Collaboration expectations

- Open a draft PR early for architecture- or contract-impacting changes
- Link related docs/runbooks in PR descriptions
- Raise compliance questions before implementing source ingestion/export behavior
- Capture trace IDs and exact error envelopes when reporting backend issues

### Escalation path (fill in)

- Build/test pipeline failures: `<platform owner>`
- Source/compliance questions: `<legal/compliance owner>`
- API contract changes: `<backend maintainer>`
- Frontend release regressions: `<frontend owner>`

## 6. Learning Resources and Training Materials

### Project-specific reading list (first)

- `README.md`
- `docs/development-environment.md`
- `docs/architecture/README.md`
- `docs/architecture/api-contracts.md`
- `docs/release/canlii-compliance-runbook.md`
- `docs/release/incident-observability-runbook.md`
- `docs/release/legal-review-checklist.md`
- `docs/release/git-secret-runbook.md` (if enabled for env bundle workflow)

### External docs (role-based)

- FastAPI, Pydantic, pytest, Ruff (backend)
- Next.js and React (frontend)
- GitHub Actions (CI workflows)
- LangChain/Chroma (if touching retrieval/ingestion/legacy RAG paths)

### Guided exercises (interactive tutorials)

#### Tutorial 1: Run the stack locally (30-45 min)

Goal:

- Boot API + frontend and confirm `/healthz` and UI load

Steps:

1. Run `make setup`
2. Run `make verify`
3. Start API (`make api-dev`)
4. Start frontend (`make frontend-install && make frontend-dev`)
5. Open local URLs and capture a screenshot for your onboarding checklist

#### Tutorial 2: Quality gate basics (20-30 min)

Goal:

- Understand the local validation commands and what they protect

Steps:

1. Run `make lint-api`
2. Run `make test`
3. Run `make source-registry-validate`
4. Read `.github/workflows/quality-gates.yml`

#### Tutorial 3: Trace a request through the backend (30 min)

Goal:

- Learn how trace IDs and error envelopes are used

Steps:

1. Read `src/immcad_api/main.py`
2. Read `docs/architecture/api-contracts.md` (Error Envelope + trace correlation sections)
3. Call an API endpoint and inspect `x-trace-id`
4. Trigger a validation error and compare `error.trace_id` with `x-trace-id`

#### Tutorial 4: Contract test drill (30-60 min)

Goal:

- Make a safe, test-first change in API contracts

Steps:

1. Read `tests/test_api_scaffold.py`
2. Add a small test for a non-breaking endpoint behavior (or update an existing doc-only assertion)
3. Run `./scripts/venv_exec.sh pytest -q tests/test_api_scaffold.py`
4. Open a draft PR with the test evidence

## 7. First Tasks and Milestones

### First-week milestone checklist

- [ ] Local environment bootstrapped and verified
- [ ] API + frontend running locally
- [ ] Read architecture overview and API contracts docs
- [ ] Completed Tutorials 1-3
- [ ] Shipped one doc/test-only PR
- [ ] Observed CI run on your PR

### Suggested starter tasks (progressive)

1. Documentation or runbook clarity improvement (low risk)
2. Add/extend API contract tests in `tests/test_api_scaffold.py`
3. Add validation test coverage for source registry or source policy modules
4. Improve frontend error-state handling using existing `ErrorEnvelope` contract
5. Implement a small backend feature behind existing policy/compliance guardrails

### Pairing/shadowing opportunities (fill in)

- Pair with backend maintainer on one route change
- Pair with frontend maintainer on one UI contract integration
- Shadow release owner during `quality-gates` review and smoke checks

## 8. Security and Compliance Training

### Core security rules

- Never commit secrets (`.env`, API tokens, service credentials)
- Use `.env.example` as the template only
- Treat `IMMCAD_API_BEARER_TOKEN` (and `API_BEARER_TOKEN` alias) as sensitive server-side config
- Follow `.editorconfig` and repo lint/test rules before PR

### Legal/compliance rules (important)

- IMMCAD is informational, not legal advice
- Preserve disclaimer behavior in UI/API responses
- Citation-required behavior is a release-critical quality attribute
- CanLII usage is metadata-only and rate-limited per documented constraints
- Do not implement source ingestion/export behavior that bypasses policy or source registry controls

### Required runbooks/checklists to review

- `docs/release/canlii-compliance-runbook.md`
- `docs/release/legal-review-checklist.md`
- `docs/release/incident-observability-runbook.md`
- `docs/release/git-secret-runbook.md` (if enabled for env bundle workflow)

### Incident handling basics for new engineers

- Capture `x-trace-id` for any failing API request
- Verify `error.trace_id` matches header for error responses
- Check `/ops/metrics` before escalating provider/source incidents
- Attach trace IDs and relevant command output to incident reports

## 9. Tools and Resources Access

### Access checklist (role-based)

Required for most engineers:

- [ ] GitHub repo access (fork + PR permissions)
- [ ] OpenAI API key (local dev minimum)
- [ ] Access to deployment platform logs (if on-call or release role)
- [ ] Access to CI workflow logs/artifacts (GitHub Actions)

Optional / role-specific:

- [ ] CanLII API key (backend/source integrations)
- [ ] Redis access in shared environments
- [ ] Vercel/project hosting access (frontend/platform)
- [ ] Monitoring/dashboard access for `/ops/metrics` consumers

### Tool-specific notes

- GitHub CLI (`gh`) is recommended for PR creation/review
- `jq` is useful for inspecting `/ops/metrics` JSON
- Docker simplifies local Redis setup
- `./scripts/venv_exec.sh` is the safest wrapper for local Python commands in constrained environments

### Troubleshooting access issues

- Missing repo access: ask project admin / repo owner
- Missing API key: request through approved secrets process (do not share in chat/email)
- CI artifact visibility issues: confirm repo permission level and Actions access
- CanLII onboarding issues: use `docs/release/canlii-compliance-runbook.md`

## 10. Feedback and Continuous Improvement

### Onboarding feedback process (recommended)

Collect feedback at:

- End of Day 1
- End of Week 1
- First PR merged
- 30-day check-in

Ask:

- Which docs were sufficient vs outdated?
- Which commands failed or were unclear?
- What was the first “blocked for >30 minutes” issue?
- Which team/process access was missing?
- Which tutorial felt highest/lowest value?

### Onboarding success metrics (recommended)

- Time-to-first-local-run
- Time-to-first-PR
- Time-to-first-merged-PR
- Number of onboarding blockers per new engineer
- % of new engineers completing Tutorials 1-3 in week 1

### Guide maintenance

Owners (fill in):

- Primary owner: `<engineering productivity owner>`
- Secondary owner: `<backend/frontend maintainer>`
- Compliance reviewer: `<legal/compliance owner>`

Review cadence:

- Review monthly while architecture is changing rapidly
- Review after any of:
  - `Makefile` command changes
  - CI workflow changes
  - new required secrets/access
  - major API contract changes
  - source policy/compliance workflow changes

## Appendix A: New Engineer Checklist (Copy/Paste)

```md
- [ ] Repo access granted
- [ ] Local clone completed
- [ ] `make setup` completed
- [ ] `make verify` completed
- [ ] API running (`/healthz` checked)
- [ ] Frontend running locally
- [ ] Read `README.md`
- [ ] Read `docs/development-environment.md`
- [ ] Read `docs/architecture/README.md`
- [ ] Read `docs/architecture/api-contracts.md`
- [ ] Read CanLII compliance runbook
- [ ] Completed Tutorials 1-3
- [ ] Opened first PR
```

## Appendix B: Manager/Buddy Onboarding Checklist (Copy/Paste)

```md
- [ ] Access requests submitted before Day 0
- [ ] Buddy assigned
- [ ] Role track selected (primary + secondary)
- [ ] First-week task list prepared
- [ ] Check-ins scheduled (Day 1 / Week 1 / 30-day)
- [ ] First PR scope reviewed for risk/compliance impact
- [ ] Feedback captured and doc improvements filed
```
