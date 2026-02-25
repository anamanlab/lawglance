# Frontend E2E Suite

This directory hosts Playwright end-to-end tests for the `frontend-web` Next.js app.

## Structure

- `fixtures/` - reusable test prompts and deterministic response payloads.
- `pages/` - page-object wrappers for shared selectors and interactions.
- `support/` - API stub setup and request capture utilities.
- `specs/` - end-to-end user journeys.

## Data Strategy

Tests use route-level stubs for `/api/chat` and `/api/search/cases` so each scenario is
stable and independent from backend availability. Stub helpers capture outgoing request
payloads to verify frontend API contracts.

## Running

From `frontend-web`:

```bash
npm run test:e2e:install
npm run test:e2e
npm run test:e2e:cross-browser
npm run test:e2e:mobile
npm run test:e2e:webkit
npm run test:e2e:mobile-safari
```

By default on local/headless Linux hosts, Playwright runs Chromium/Firefox/Mobile Chrome.
WebKit/Safari runs are opt-in.

Note: WebKit/Safari runs may require additional host libraries on Linux. CI installs
these dependencies with `playwright install --with-deps`.

## Environment Controls

- `PLAYWRIGHT_BASE_URL` - target URL.
- `PLAYWRIGHT_SKIP_WEBSERVER=true` - skip automatic Next.js startup.
- `PLAYWRIGHT_PROJECTS=chromium,firefox` - select project subset.
- `PLAYWRIGHT_INCLUDE_SAFARI=true` - include Mobile Safari in CI defaults.
