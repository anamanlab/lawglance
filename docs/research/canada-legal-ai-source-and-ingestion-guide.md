# Canadian Legal AI Source and Ingestion Guide

**Date:** 2026-02-24  
**Project:** IMMCAD legal research agent  
**Audience:** Product, engineering, legal/compliance, operations

## 1. Purpose

This guide defines how IMMCAD can:

1. Discover relevant Canadian case law.
2. Retrieve and ingest full-text decisions where permitted.
3. Ingest user PDFs and selected websites as reference sources.
4. Operate within legal/licensing and technical constraints.

This document is based on a source feasibility audit completed on **February 24, 2026**.

## 2. Known Constraints

### 2.1 CanLII API constraints (confirmed)

- Metadata-only access (no full-text retrieval through API).
- Quotas:
  - `5000` requests/day
  - `2` requests/second
  - `1` in-flight request
- No quota increase offered.

### 2.2 Repository alignment

These limits are already enforced in backend code and runbooks:

- `backend-vercel/src/immcad_api/sources/canlii_usage_limiter.py`
- `docs/release/canlii-compliance-runbook.md`

## 3. Executive Recommendation

Use a **hybrid source strategy**:

1. Keep CanLII API for metadata discovery and candidate ranking only.
2. Build primary full-text ingestion from official court publication endpoints (SCC, FC, FCA).
3. Add a rights-filtered ingestion lane for user PDFs and approved websites.
4. Run commercial provider procurement in parallel (vLex/Lexum and similar) for coverage expansion and service guarantees.

This path gives immediate launch viability without blocking on procurement.

Production execution details are in:

- `docs/research/canada-legal-ai-production-implementation-plan.md`

## 4. Source Feasibility Matrix (as of 2026-02-24)

| Source | Full text available | Machine-readable entry points | Direct PDF path | Rights posture (initial) | Use in MVP |
|---|---|---|---|---|---|
| CanLII API | No (API) | API metadata only | No | Strict anti-bulk terms publicly stated | Yes, metadata only |
| SCC Decisions | Yes | RSS + JSON feeds + decision pages | Yes (`document.do`) | Terms page includes detailed reproduction conditions | Yes, primary |
| Federal Court (FC) | Yes | RSS + queryable search endpoints | Yes (`document.do`) | Public court site; legal review still required | Yes, primary |
| Federal Court of Appeal (FCA) | Yes | Search/date browse endpoints | Yes (`document.do`) | Public court site; legal review still required | Yes, primary |
| IRB Decisions | Partial/public selection | Web pages + linked collections; open datasets for aggregates | Mixed | Selection model, privacy-sensitive domain | Yes, scoped |
| Open Canada CKAN | Dataset metadata | CKAN Action API (GET-only) | Dataset-dependent | Open Government License per dataset | Yes, for discovery metadata |
| A2AJ Canadian Legal Data API | Yes (unofficial full text) | REST API (`/coverage`, `/search`, `/fetch`) | Source URL-dependent | Per-record upstream license caveats | Yes, accelerator lane |
| Refugee Law Lab bulk datasets | Yes (unofficial full text) | Bulk JSON/Parquet/Hugging Face | Source URL-dependent | CC BY-NC 4.0 + upstream obligations | Yes, accelerator lane |
| Commercial legal providers | Yes (license-dependent) | Vendor APIs | Vendor-specific | Contractual | Phase 2+ |

## 5. Detailed Findings by Source

## 5.1 CanLII

- API use remains valuable for:
  - Citation-level discovery
  - Court/date/title/case identifier enrichment
  - Candidate routing to other full-text sources
- Do not design architecture that depends on CanLII full-text API expansion.
- Public statements and terms indicate strong restrictions against bulk/systematic extraction without permission.

## 5.2 Supreme Court of Canada (SCC)

Verified endpoints:

- RSS index: `https://decisions.scc-csc.ca/scc-csc/en/rss/index.do`
- JSON feed index: `https://decisions.scc-csc.ca/scc-csc/en/rss/json/index.do`
- Example JSON feed: `https://decisions.scc-csc.ca/scc-csc/scc-csc/en/json/rss.do`
- Example decision page: `https://decisions.scc-csc.ca/scc-csc/scc-csc/en/item/<id>/index.do`
- Example PDF route: `https://decisions.scc-csc.ca/scc-csc/scc-csc/en/<id>/1/document.do`

Operational value:

- Reliable for incremental feed polling.
- Includes citation and metadata fields in JSON feed.
- Direct document retrieval available.

## 5.3 Federal Court (FC)

Verified endpoints:

- RSS page: `https://decisions.fct-cf.gc.ca/fc-cf/en/rss/index.do`
- RSS feed: `https://decisions.fct-cf.gc.ca/fc-cf/decisions/en/rss.do`
- Search endpoint: `https://decisions.fct-cf.gc.ca/fc-cf/en/d/s/index.do`

Observed search parameters:

- `cont` (full text)
- `ref` (case name / citation / file number)
- `d1`, `d2` (date range)
- `col` (collection id)
- `page` (pagination)

Document retrieval:

- Decision pages expose direct PDF download links using `document.do`.

## 5.4 Federal Court of Appeal (FCA)

Verified:

- Search endpoint works and supports `col=53`.
- Date navigation endpoint works:
  - `https://decisions.fca-caf.gc.ca/fca-caf/decisions/en/nav_date.do`
- Decision rows include direct PDF `document.do` links.

Note:

- A stable public RSS/JSON feed equivalent to SCC/FC was not conclusively verified for FCA during this audit.

## 5.5 Immigration and Refugee Board (IRB)

Findings:

- IRB decisions page states that a **selection** of IRB decisions is available through CanLII.
- IRB publishes some decision content and guidance materials on its own site.
- Open Government datasets found for IRB are primarily aggregate/statistical outputs, not a comprehensive full-text decision corpus.

Implication:

- IRB ingestion should be modeled as selective and policy-driven, not assumed to be exhaustive.

## 5.6 Open Government / CKAN

Verified:

- CKAN Action API available.
- GET-only API policy documented.
- Useful for automated dataset discovery, update polling, and metadata synchronization.
- IRB RPD open dataset is aggregate-oriented (for example: country/year/outcome/total), not full-text decisions.

## 5.7 A2AJ and Refugee Law Lab (open/freemium accelerators)

Verified:

- A2AJ API is publicly documented and exposes `coverage`, `search`, and `fetch` endpoints.
- A2AJ returns case full text in API responses and includes an `upstream_license` field per record.
- Coverage includes relevant datasets (for example SCC/FC/FCA and RAD/RPD), subject to their own source-specific conditions.
- Refugee Law Lab publishes bulk legal datasets (JSON/Parquet/Hugging Face) with explicit licensing notes.
- Refugee Law Lab licensing notes require both CC BY-NC compliance and compliance with upstream source terms.

Implication:

- These are strong accelerators for prototyping and internal research lanes.
- Keep them behind a policy gate until commercial-use compatibility is approved by legal/compliance.
- Refugee Law Lab-backed RAG/serving endpoints must be treated as **search-indexing-prohibited**: do not expose raw documents or crawlable/indexable representations to public internet crawlers.
- If HTTP exposure is necessary for internal tools, require authentication, deny anonymous/public bucket access, and send `X-Robots-Tag: noindex, nofollow` (plus `robots.txt` protections where applicable).
- Add automated checks/alerts for accidentally public or crawlable RLL-backed endpoints/storage before any environment promotion.
- **Current deployment decision (2026-02-24):**
  - **A2AJ:** `internal-only` approved; `production` blocked pending legal sign-off.
  - **Refugee Law Lab:** `internal-only` approved; `production` blocked pending legal sign-off.
  - Constraint tag for deployment decision table / policy metadata: `search-indexing-prohibited`.

## 5.8 Crawler and feed reliability caveats

- SCC JSON feeds are suitable for incremental updates but do not replace historical backfill; use year/date navigation for full corpus synchronization.
- FC RSS stream may contain cross-court citations in practice; enforce collection/citation validation in connector logic.
- Decisia year/date endpoints can return valid HTTP responses even when query intent is not met; validate selected year and document metadata before ingest.
- CanLII web endpoints are bot-protected and should not be used as a bulk crawling source; use approved API access and permitted alternatives.

## 6. Rights and Compliance Design

Treat rights as a first-class attribute for every document.

Minimum metadata fields to store per document:

- `source_system`
- `source_url`
- `retrieved_at`
- `license_type`
- `rights_notes`
- `commercial_redistribution_allowed` (boolean)
- `internal_research_allowed` (boolean)
- `citation_required_text`
- `provenance_hash`

Enforcement controls:

1. Block download/export when redistribution rights are unclear.
2. Allow answer-time citation snippets even when full export is blocked.
3. Apply per-source robots/terms policy profile in connector config.
4. Keep legal approval records per source in `artifacts/compliance/`.
5. Require source-level license assertions (`official`, `unofficial`, `upstream-restricted`) before promoting documents to production retrieval.
6. For `Refugee Law Lab` (and any derivative serving path), enforce `search-indexing-prohibited` controls: authentication required, no anonymous/public storage access, and `noindex`/crawler-deny headers for any HTTP-exposed endpoints.
7. Add automated checks/alerts for public hosting or crawler-accessible endpoints tied to `A2AJ`/`Refugee Law Lab` datasets before deployment promotion.

## 7. Target Architecture

## 7.1 Ingestion lanes

1. **Case-law lane**
   - SCC/FC/FCA connectors
   - Feed + search-driven incremental fetch
2. **User PDF lane**
   - Uploaded documents
   - OCR fallback and redaction support
3. **Website lane**
   - Curated domains only
   - Conditional requests (`ETag`, `Last-Modified`)

## 7.2 Processing pipeline

1. Fetch
2. Parse
3. Normalize (text + metadata)
4. Deduplicate
5. Chunk
6. Embed + keyword index
7. Persist with provenance
8. Evaluate quality gates

## 7.3 Retrieval strategy

- Hybrid retrieval:
  - Dense vector retrieval
  - Lexical/BM25 retrieval
  - Citation-aware reranking
- Always return source references.
- Answer policy:
  - If evidence confidence low, refuse or ask clarification.

## 8. PDF and Website Ingestion Best Practices

## 8.1 PDFs

1. Detect text PDF vs scanned PDF.
2. OCR only when required.
3. Preserve page mapping for citation anchors.
4. Keep original file hash and parser version.
5. Store language tag and extraction confidence.

## 8.2 Websites

1. Use source-specific selectors (avoid full-page noise).
2. Use conditional GET (`ETag`/`Last-Modified`) to reduce re-fetch cost.
3. Compute content hash and re-embed only when hash changes.
4. Keep crawl politeness limits per domain.
5. Track canonical URL and retrieval timestamp.

## 9. 2026 Agent Best Practices (Vendor Synthesis)

Cross-vendor alignment from OpenAI, Anthropic, and Google/Gemini:

1. Start with simple, deterministic workflows before multi-agent autonomy.
2. Use strict tool schemas and narrowly scoped tools.
3. Add human approval gates for high-impact or rights-sensitive actions.
4. Build observability from day one (traces, failure classes, evals).
5. Use retrieval-grounded answers and enforce citation requirements.
6. Keep retry, timeout, and rate-limit logic centralized in source adapters.
7. Version prompts/policies and run regression suites on every change.

Implementation implication for IMMCAD:

- Use source adapters + policy gate + eval harness as the default release pattern.

## 10. Phased Delivery Plan

## Phase 0: Compliance and source contracts (1 week)

- Finalize source rights matrix.
- Define allowed uses per source.
- Publish connector policy config template.

## Phase 1: Public-source ingestion baseline (2-3 weeks)

- Ship SCC + FC + FCA connectors.
- Add incremental sync and checkpointing.
- Add source-level throttling and resilience.
- Add optional A2AJ/RLL acceleration connectors behind feature flags and license-policy checks.

## Phase 2: IRB and curated web sources (1-2 weeks)

- Add selective IRB ingestion policy.
- Add curated website ingestion with change detection.

## Phase 3: Commercial expansion (parallel procurement)

- Evaluate vLex/Lexum and other licensed feeds.
- Integrate licensed connector behind feature flag.

## 11. Operational Metrics and SLOs

Track at minimum:

- Source fetch success rate
- Parse success rate
- OCR fallback rate
- Duplicate rate
- Mean ingest latency per source
- Index freshness lag
- Citation presence rate in answers
- Unsupported-source refusal rate

Target initial gates (Phase 1 launch):

- Citation presence: `>= 90%` for legal factual answers during Phase 1 onboarding (raise toward `>= 99%` as a steady-state SLO after Section 13 conformance + policy-enforcement onboarding steps are complete and metrics stabilize)
- Ingestion success: `>= 98%` on scheduled sources
- Freshness lag (SCC/FC/FCA): `< 24h`

## 12. Provider Due Diligence Checklist (Commercial/Freemium)

For each provider candidate:

1. Coverage scope (Canada immigration and federal jurisprudence depth).
2. Full-text rights and redistribution terms.
3. API reliability, quotas, and SLA.
4. Citation metadata quality.
5. Change-feed/update model.
6. Cost model and overage behavior.
7. Contractual constraints for AI training/inference usage.

## 13. Immediate Next Actions

1. Approve Phase 0 rights matrix template.
2. Implement SCC/FC/FCA connectors in a feature branch.
3. Add ingestion conformance tests:
   - endpoint health
   - PDF retrieval
   - metadata completeness
4. Add policy enforcement tests for source-based export permissions.
5. Use the conformance + policy-enforcement onboarding results above to tighten Phase 1 citation-presence gates from the initial threshold toward the `>= 99%` steady-state SLO in Section 11.

## 14. Verified Reference Links

### Core legal sources

- SCC judgments portal: https://www.scc-csc.ca/judgments-jugements/
- SCC RSS index: https://decisions.scc-csc.ca/scc-csc/en/rss/index.do
- SCC JSON feeds index: https://decisions.scc-csc.ca/scc-csc/en/rss/json/index.do
- FC decisions RSS: https://decisions.fct-cf.gc.ca/fc-cf/decisions/en/rss.do
- FC decisions/search: https://decisions.fct-cf.gc.ca/fc-cf/en/d/s/index.do
- FCA decisions/search: https://decisions.fca-caf.gc.ca/fca-caf/en/d/s/index.do
- FCA date browse: https://decisions.fca-caf.gc.ca/fca-caf/decisions/en/nav_date.do
- IRB decisions: https://www.irb-cisr.gc.ca/en/decisions/Pages/index.aspx

### Open data

- Open Canada CKAN API guide: https://open.canada.ca/en/access-our-application-programming-interface-api
- IRB RPD dataset: https://open.canada.ca/data/en/dataset/6e47f705-71ed-41f0-8fd5-d1a8508a3b63
- Justice Laws portal: https://laws-lois.justice.gc.ca/eng/
- Justice Laws FAQ (reproduction note): https://laws-lois.justice.gc.ca/eng/faq/
- A2AJ overview: https://a2aj.ca/canadian-legal-data/
- A2AJ API docs: https://api.a2aj.ca/docs
- A2AJ OpenAPI: https://api.a2aj.ca/openapi.json
- Refugee Law Lab bulk index: https://refugeelab.ca/bulk-data/

### Commercial/provider discovery

- vLex developer portal: https://developer.vlex.com/
- Fastcase legal data API: https://www.fastcase.com/solutions/legal-data-api/
- Lexum: https://lexum.com/en/

### Rights/compliance references

- SCC terms and reproduction conditions: https://scc-csc.ca/resources-ressources/terms-avis/
- Federal Court important notices: https://www.fct-cf.ca/en/pages/important-notices
- Federal Court of Appeal important notices: https://www.fca-caf.ca/en/pages/important-notices
- CanLII robots policy: https://www.canlii.org/robots.txt

### Agent best-practice references

- OpenAI practical agent guide: https://cdn.openai.com/business-guides-and-resources/a-practical-guide-to-building-agents.pdf
- OpenAI building agents: https://openai.com/index/building-agents/
- Anthropic effective agents: https://www.anthropic.com/engineering/building-effective-agents
- Anthropic tool-use implementation: https://docs.anthropic.com/en/docs/agents-and-tools/tool-use/implement-tool-use
- Google Gemini best practices: https://cloud.google.com/gemini/enterprise/docs/create-agentic-app-best-practices
- Gemini function calling: https://ai.google.dev/gemini-api/docs/function-calling
