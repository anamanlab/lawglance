# Pre-Deploy Command Sheet (2026-02-25)

## Purpose
Deterministic command sequence for the next deploy window after quota reset.

## 1) Preflight (repo + quality)

```bash
git checkout main
git pull --ff-only origin main

git status --short

gh pr list --state open --limit 30
```

```bash
make quality
make source-registry-validate
make backend-vercel-sync-validate
```

```bash
npm run build --prefix frontend-web
npm run typecheck --prefix frontend-web
npm run test --prefix frontend-web
```

```bash
uv run python scripts/scan_domain_leaks.py
bash scripts/check_repository_hygiene.sh
```

## 2) Backend Deploy (source-based)

```bash
vercel --cwd backend-vercel deploy --prod --yes
```

Verify deployment and alias:

```bash
vercel inspect <backend-deployment-url>
vercel inspect https://backend-vercel-eight-sigma.vercel.app
```

## 3) Frontend Deploy

```bash
vercel --cwd frontend-web deploy --prod --yes
```

Verify deployment and alias:

```bash
vercel inspect <frontend-deployment-url>
vercel inspect https://frontend-web-plum-five.vercel.app
```

## 4) Smoke Checks (production aliases)

Unauthenticated health:

```bash
vercel curl /healthz --deployment https://backend-vercel-eight-sigma.vercel.app
```

Authenticated endpoints (requires valid production token):

```bash
export IMMCAD_API_BEARER_TOKEN='<prod-token>'

vercel curl /ops/metrics \
  --deployment https://backend-vercel-eight-sigma.vercel.app \
  -- --header "Authorization: Bearer ${IMMCAD_API_BEARER_TOKEN}"

vercel curl /api/search/cases \
  --deployment https://backend-vercel-eight-sigma.vercel.app \
  -- --request POST \
     --header "content-type: application/json" \
     --header "Authorization: Bearer ${IMMCAD_API_BEARER_TOKEN}" \
     --data '{"query":"H&C reasonableness standard","limit":3}'

vercel curl /api/chat \
  --deployment https://backend-vercel-eight-sigma.vercel.app \
  -- --request POST \
     --header "content-type: application/json" \
     --header "Authorization: Bearer ${IMMCAD_API_BEARER_TOKEN}" \
     --data '{"message":"Give one leading SCC immigration reasonableness case with citation only.","session_id":"prod-smoke-20260225","locale":"en-CA","mode":"standard"}'
```

## 5) Go/No-Go Checklist

- Backend alias points to new READY deployment.
- Frontend alias points to new READY deployment.
- Health check returns 200.
- Authenticated `/ops/metrics`, `/api/chat`, `/api/search/cases` return 200.
- Export policy behavior validated via UI path (approval prompt + allowed-source export).
- `docs/release/known-issues.md` updated with any residual accepted risks.

## 6) Rollback (if needed)

Re-point aliases to last known READY deployment IDs and re-run smoke checks.

```bash
vercel --cwd backend-vercel ls --prod
vercel --cwd frontend-web ls --prod
```

Then verify aliases again with `vercel inspect` and repeat Section 4 smoke checks.
