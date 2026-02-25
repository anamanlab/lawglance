# IMMCAD

AI-powered legal information assistant focused on **Canadian immigration law**.

> Disclaimer: IMMCAD is an informational tool and **not legal advice**. It does not create a lawyer-client relationship. Users should consult a licensed immigration lawyer or RCIC for legal advice.

## Why this project

IMMCAD starts from the LawGlance architecture (RAG + legal documents + chat interface) and adapts it to the Canadian immigration context.

The goal is to help users quickly understand:
- Eligibility pathways (study, work, PR, citizenship)
- Official process steps
- Required documents and timelines
- Common policy constraints and risks

## Current runtime status

The current implementation is converging on a single production runtime:
- Next.js chat UI in `frontend-web` (production path)
- Python API backend in `src/immcad_api` (production path)
- Streamlit UI in `app.py` is now a legacy dev-only **thin API client** to `/api/chat`
- Legacy local-RAG modules are archived under `legacy/local_rag/` for compatibility and historical evaluation workflows
- CI quality gates include ingestion smoke, dependency review, jurisdiction suite, and repository hygiene

### Remaining Canada-readiness gaps

1. Legal corpus completeness
- Complete IRPA/IRPR/IRCC source coverage and enforce freshness cadence.

2. Grounding enforcement
- Add runtime citation-grounding verification beyond template-level constraints.

3. Product localization
- Deliver bilingual-ready user journeys (English now, French next).

4. Legacy retirement
- Fully decommission legacy local-RAG modules once all evaluation dependencies are migrated.

## Canadian legal scope (V1)

### Primary sources (must-have)
- Immigration and Refugee Protection Act (IRPA)
- Immigration and Refugee Protection Regulations (IRPR)
- Citizenship Act and related regulations (as applicable)
- IRCC official pages and Program Delivery Instructions
- Ministerial Instructions relevant to Express Entry and category-based selection

### Secondary sources (phase 2+)
- Federal Court immigration decisions (selected, high-impact)
- IRB policy/process references where publicly available
- Provincial Nominee Program (PNP) official program pages

## Architecture adaptation plan

### Phase 0 - Foundation (1-2 days)
- Rename/rebrand project artifacts to IMMCAD
- Replace README and legal disclaimers
- Create a dedicated data ingestion folder for Canadian sources
- Define document metadata schema: `jurisdiction`, `source_type`, `program`, `effective_date`, `url`

### Phase 1 - Data ingestion (3-5 days)
- Build ingestion pipeline for official sources (PDF + HTML)
- Normalize text and chunk with legal-structure awareness
- Rebuild Chroma index from Canadian corpus only
- Remove or archive legacy vector database artifacts

### Phase 2 - Prompt and retrieval hardening (2-4 days)
- Rewrite `SYSTEM_PROMPT` and `QA_PROMPT` for Canadian immigration domain
- Add strict answer format:
  - Plain-language summary
  - Applicable rule/policy
  - Source citation(s)
  - Confidence + when to seek licensed counsel
- Tune retriever thresholds and context window strategy

### Phase 3 - Quality and evaluation (3-5 days)
- Create evaluation dataset of real immigration questions
- Measure:
  - Citation coverage
  - Groundedness
  - Hallucination rate
  - Refusal correctness (out-of-scope handling)
- Add regression tests for prompts and retrieval behavior

### Phase 4 - Canadian UX and release readiness (3-5 days)
- Add jurisdiction-aware UX copy and legal notices
- Add bilingual-ready UI structure (English/French)
- Add observability (request logs, failure analytics)
- Prepare private beta release with feedback loop

## Immediate next steps (recommended order)

1. Keep `src/immcad_api/policy/prompts.py` as the single canonical prompt source.
2. Finalize Canadian source coverage and run ingestion refresh + smoke validation in CI on schedule.
3. Implement grounding-verification checks in response assembly before delivery.
4. Add bilingual-ready locale handling to production UI/API contracts (`en-CA`, `fr-CA`) with coverage tests.
5. Remove archive references once `legacy/local_rag/` is fully retired.

## Suggested task breakdown

### Workstream A - Legal knowledge
- Source inventory and version control (effective dates)
- Corpus quality review and deduplication
- Citation policy definition

### Workstream B - RAG engineering
- Ingestion scripts + chunking strategy
- Metadata filtering and retriever tuning
- Evaluation pipeline and benchmark dataset

### Workstream C - Product and compliance
- Disclaimer placement and user consent flows
- Out-of-scope response policy
- Bilingual content strategy (EN now, FR next)

## Local development

### Prerequisites
- Python 3.11+
- `uv`
- Node.js 20+
- OpenAI API key
- Redis (recommended)

### Setup

```bash
git clone <your-private-repo-url>  # obtain this URL from your project admin or internal repository portal
cd IMMCAD
uv sync
```

Access note: this repository is private; request access through your project admin before cloning.

Create `.env`:

```bash
OPENAI_API_KEY=your-api-key-here
```

Run the production path locally:

Terminal 1 (API):

```bash
make api-dev
```

Terminal 2 (frontend):

```bash
make frontend-install
make frontend-dev
```

App URLs:

```bash
Frontend: http://127.0.0.1:3000
API:      http://127.0.0.1:8000
```

### Backend API (production runtime)

Run API service scaffold:

```bash
uv run uvicorn immcad_api.main:app --app-dir src --reload --port 8000
```

Health check:

```bash
http://127.0.0.1:8000/healthz
```

### Next.js frontend (`frontend-web`, production runtime)

Install frontend dependencies:

```bash
make frontend-install
```

Run frontend:

```bash
make frontend-dev
```

Frontend URL:

```bash
http://127.0.0.1:3000
```

Create `frontend-web/.env.local` with:

```bash
NEXT_PUBLIC_IMMCAD_API_BASE_URL=/api
IMMCAD_API_BASE_URL=http://127.0.0.1:8000
IMMCAD_API_BEARER_TOKEN=your-api-bearer-token
```

Production safety notes:
- `NEXT_PUBLIC_IMMCAD_API_BASE_URL` should remain `/api` so browser calls stay on the same origin.
- `IMMCAD_API_BASE_URL` must use `https://` in `NODE_ENV=production`.
- Keep `IMMCAD_API_BEARER_TOKEN` server-only; do not publish it via `NEXT_PUBLIC_*`.
- If using `git-secret` for encrypted repo-stored env bundles, follow `docs/release/git-secret-runbook.md` and keep production runtime secrets in GitHub/Vercel secret managers.

### Legacy Streamlit UI (`app.py`) - dev-only

Use this only for local prototyping or migration troubleshooting. It is not the production runtime path.

```bash
uv run streamlit run app.py
```

Legacy UI URL:

```bash
http://127.0.0.1:8501
```

### Ingestion + jurisdiction evaluation workflows

Generate ingestion execution report from the Canada source registry:

```bash
make ingestion-run
```

This runner now keeps a checkpoint file (`artifacts/ingestion/checkpoints.json`) and uses
`ETag` / `Last-Modified` conditional requests to mark unchanged sources as `not_modified`.

Generate jurisdictional readiness scoring report (JSON + Markdown):

```bash
make jurisdiction-eval
```

Run behavior-focused jurisdictional suite (policy refusal + citation behavior):

```bash
make jurisdiction-suite
```

Outputs are written under `artifacts/` (gitignored) and uploaded by CI in `quality-gates` as `jurisdiction-eval-report`.

### Documentation maintenance

Run documentation quality audit (link/style/content/freshness checks):

```bash
make docs-audit
```

Apply safe documentation auto-fixes (TOC refresh):

```bash
make docs-fix
```

Reports are generated to:

```bash
artifacts/docs/doc-maintenance-report.md
artifacts/docs/doc-maintenance-report.json
```

### Ralph autonomous loop

Ralph is now wired in this repo under `scripts/ralph/`.

Run with Codex (default):

```bash
make ralph-run
```

Run with Codex (explicit target):

```bash
make ralph-run-codex
```

Run with Amp:

```bash
make ralph-run-amp
```

Run with Claude Code (optional):

```bash
make ralph-run-claude
```

Preflight validation (no iterations):

```bash
bash scripts/ralph/ralph.sh --tool codex --check
```

Check story progress:

```bash
make ralph-status
```

Ralph execution state is in:
- `scripts/ralph/prd.json`
- `scripts/ralph/progress.txt`

## Definition of done for “Canadian adaptation”

IMMCAD is considered Canada-ready when:
- All production retrieval sources are Canadian immigration sources
- Every answer includes citation(s) or a safe refusal
- Hallucination rate is within agreed threshold on benchmark set
- Legal disclaimer and escalation guidance are consistently applied
- Beta users can complete top immigration question flows with useful outcomes

## License (Authoritative Text: `LICENSE.md`)

This project is licensed under the Apache License, Version 2.0.
Maintainers may relicense in the future; see `LICENSE.md` and project governance for updates.
