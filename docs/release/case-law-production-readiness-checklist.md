# Case-Law Production Readiness Checklist

Use this checklist before promoting a deployment that includes `/api/search/cases` and `/api/export/cases`.

## 1) Hardened Environment Configuration

- Set `ENVIRONMENT` (or `IMMCAD_ENVIRONMENT`) to a hardened value:
  - `production`
  - `prod`
  - `ci`
  - hardened aliases like `production-us-east`, `prod_blue`, `ci-smoke`
- Set `IMMCAD_API_BEARER_TOKEN` (or matching `API_BEARER_TOKEN` compatibility alias).
- Set `CITATION_TRUSTED_DOMAINS` explicitly (non-empty CSV).
- Ensure `ENABLE_SCAFFOLD_PROVIDER=false`.
- Ensure `ALLOW_SCAFFOLD_SYNTHETIC_CITATIONS=false`.
- Ensure `EXPORT_POLICY_GATE_ENABLED=true`.
- Ensure at least one case-search backend is available:
  - `ENABLE_OFFICIAL_CASE_SOURCES=true`, or
  - valid `CANLII_API_KEY`.

## 2) Case-Law Search Behavior

- Confirm official feeds are primary (`SCC_DECISIONS`, `FC_DECISIONS`, `FCA_DECISIONS`).
- Confirm CanLII fallback is disabled for synthetic scaffold results in hardened environments.
- Decide whether to enable official-only display mode:
  - `CASE_SEARCH_OFFICIAL_ONLY_RESULTS=true` to hide non-exportable case results from UI.
- Keep CanLII full-text export disabled unless explicit legal approval + policy update is completed:
  - follow `docs/release/canlii-pdf-export-rollout-plan.md`.

## 3) Export Safety and Consent

- Confirm `/api/export/cases` requires `user_approved=true`.
- Confirm source-policy export gates are enforced.
- Confirm export URL host checks are enforced for initial and redirected URLs.
- Confirm non-PDF payloads are rejected when `format=pdf`.
- Confirm payload size cap is enforced (`EXPORT_MAX_DOWNLOAD_BYTES`).

## 4) Verification Commands

Run these from repo root before release:

```bash
make quality
npm run typecheck --prefix frontend-web
npm run test --prefix frontend-web
```

## 5) Release Evidence

- Preserve `make quality` output in CI artifacts.
- Preserve frontend test and typecheck output in CI artifacts.
- Preserve policy/ingestion evidence required by `release-gates`.
- Verify `/ops/metrics` export audit events are visible in staging after a controlled export test.
