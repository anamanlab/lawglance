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

## Current baseline analysis

The current codebase already provides a strong foundation:
- Streamlit chat UI in `app.py`
- RAG pipeline with LangChain + Chroma in `chains.py`
- Session history + caching with Redis in `cache.py` and `lawglance_main.py` (legacy filename retained for compatibility during IMMCAD migration)
- Prompt templates in `prompts.py`

### Gaps to adapt for Canada

The repository is still jurisdiction-specific to Indian legal context and needs Canadian adaptation in 4 main areas:

1. Legal corpus
- Current vectors/prompt references are not Canada-focused.
- Need a curated Canadian immigration corpus.

2. Prompting and safety policy
- System prompt must be rewritten for Canadian immigration law.
- Must enforce legal disclaimers, scope boundaries, and escalation guidance.

3. Retrieval quality and citations
- Must add source metadata and citation quality controls.
- Need grounding checks to reduce hallucinations.

4. Product localization
- Canada requires clear English-first support and planned French support.
- UX should reflect IRCC terminology and user journeys.

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

1. Replace domain prompts in `prompts.py` with Canadian immigration scope and strict disclaimer behavior.
2. Create `data/sources/canada-immigration/` and ingest official IRPA/IRPR + IRCC sources.
3. Rebuild vector store and validate retrieval quality on 30-50 benchmark questions.
4. Add citation-required response template and fail-safe refusal when context is missing.
5. Build a small evaluation harness for repeatable quality checks before UI launch.

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

Run:

```bash
uv run streamlit run app.py
```

App URL:

```bash
http://127.0.0.1:8501
```

### API scaffold (new feature)

Run API service scaffold:

```bash
uv run uvicorn immcad_api.main:app --app-dir src --reload --port 8000
```

Health check:

```bash
http://127.0.0.1:8000/healthz
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
