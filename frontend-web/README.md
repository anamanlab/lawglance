# frontend-web

Next.js App Router + Tailwind frontend shell for IMMCAD (`US-006`).

## Prerequisites

- Node.js 20+
- npm 10+

## Environment

Create `frontend-web/.env.local`:

```bash
NEXT_PUBLIC_IMMCAD_API_BASE_URL=/api
IMMCAD_API_BASE_URL=http://127.0.0.1:8000
IMMCAD_API_BEARER_TOKEN=your-api-bearer-token
IMMCAD_ALLOW_PROXY_SCAFFOLD_FALLBACK=false
```

`NEXT_PUBLIC_IMMCAD_API_BASE_URL` should point to the local proxy route (`/api`) for browser calls.
Server-side proxy configuration reads only `IMMCAD_API_BASE_URL` (the `NEXT_PUBLIC_*` variable is not used as a server fallback).
Set `IMMCAD_API_BEARER_TOKEN` on the server when backend bearer auth is enabled (`API_BEARER_TOKEN` is accepted as a compatibility alias).
If both token variables are set, they must contain the same value.
Do not expose bearer tokens through `NEXT_PUBLIC_*` variables.
For production, `IMMCAD_API_BASE_URL` must use `https://`.
`IMMCAD_ALLOW_PROXY_SCAFFOLD_FALLBACK` defaults to `false`; set it to `true` only for non-hardened debug/demo environments where chat scaffold fallback is explicitly desired.
Use `NEXT_PUBLIC_IMMCAD_FRONTEND_REDESIGN_ENABLED=true|false` to stage rollout of the redesigned shell.

For Cloudflare local preview, copy `.dev.vars.example` to `.dev.vars` and set real values.

## Architecture

- `app/page.tsx`: frontend entry page and shell composition.
- `app/api/documents/*`: proxy handlers for document intake/readiness/package endpoints.
- `components/chat-shell.tsx`: compatibility export for the current chat shell API.
- `components/chat/chat-shell-container.tsx`: stateful orchestration layer.
- `components/chat/*.tsx`: presentational modules (header, thread, composer, case panel, support panel).
- `lib/api-client.ts`: browser API contract client with trace/error envelope handling.
- `lib/backend-proxy.ts`: server proxy and scaffold fallback behavior.

Document proxy notes:

- `lib/backend-proxy.ts` forwards `x-real-ip`, `x-forwarded-for`, `cf-connecting-ip`, and `true-client-ip` upstream to preserve backend client-scoped document matter lookups across proxy hops.
- Readiness/package requests for a `matter_id` depend on consistent upstream client identity.

## Run

```bash
npm install
npm run dev
```

Open `http://127.0.0.1:3000`.

## Scripts

- `npm run dev` - local development server
- `npm run build` - production build
- `npm run start` - run production build
- `npm run lint` - Next.js lint checks
- `npm run typecheck` - TypeScript checks
- `npm run test` - Vitest contract and component tests
- `npm run cf:build` - build a Cloudflare Worker artifact using OpenNext
- `npm run cf:preview` - build and preview the Cloudflare Worker locally
- `npm run cf:deploy` - build and deploy to Cloudflare Workers
- `npm run cf:upload` - build and upload assets/version to Cloudflare
- `npm run test:e2e:install` - install default headless-server browsers (Chromium + Firefox)
- `npm run test:e2e:install:webkit` - install WebKit browser runtime
- `npm run test:e2e:install:mobile-safari` - install WebKit runtime for Mobile Safari emulation
- `npm run test:e2e` - run default Playwright E2E suite (Chromium + Firefox + Mobile Chrome)
- `npm run test:e2e:cross-browser` - run Playwright E2E suite on Chromium and Firefox
- `npm run test:e2e:webkit` - run Playwright E2E suite on WebKit
- `npm run test:e2e:mobile` - run Playwright E2E suite on Mobile Chrome profile
- `npm run test:e2e:mobile-safari` - run Playwright E2E suite on Mobile Safari profile
- `npm run test:e2e:headed` - run Chromium E2E tests with visible browser UI

## E2E Testing

The Playwright suite lives under `frontend-web/e2e/`:

- `e2e/pages/` contains page-object helpers.
- `e2e/fixtures/` contains deterministic test prompts/response payloads.
- `e2e/support/` contains API route stubs and request capture helpers.
- `e2e/specs/` contains end-to-end scenarios.

By default, Playwright starts `next dev` on `http://127.0.0.1:3100` and forces
`ENVIRONMENT=development` so tests stay isolated from hardened runtime requirements.
On local/headless Linux hosts, default project selection excludes Safari-based projects.
Use explicit scripts (`test:e2e:webkit`, `test:e2e:mobile-safari`) to opt into them.

Useful overrides:

- `PLAYWRIGHT_BASE_URL` - run against an existing host (for example staging).
- `PLAYWRIGHT_SKIP_WEBSERVER=true` - skip local Next.js startup.
- `PLAYWRIGHT_PROJECTS=chromium,firefox` - run a subset of configured projects.
- `PLAYWRIGHT_INCLUDE_SAFARI=true` - include Mobile Safari in CI default project selection.

## Cloudflare (OpenNext)

This app is prepared for Cloudflare Workers using OpenNext:

- `open-next.config.ts`
- `wrangler.jsonc`

Local Cloudflare preview:

```bash
cp .dev.vars.example .dev.vars
npm run cf:preview
```

Production deploy (after `wrangler login` and environment setup):

```bash
npm run cf:deploy
```
