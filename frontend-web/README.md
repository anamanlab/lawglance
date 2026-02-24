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
```

`NEXT_PUBLIC_IMMCAD_API_BASE_URL` should point to the local proxy route (`/api`) for browser calls.
Set `IMMCAD_API_BEARER_TOKEN` on the server when backend bearer auth is enabled.
Do not expose bearer tokens through `NEXT_PUBLIC_*` variables.
For production, `IMMCAD_API_BASE_URL` must use `https://`.
Use `NEXT_PUBLIC_IMMCAD_FRONTEND_REDESIGN_ENABLED=true|false` to stage rollout of the redesigned shell.

## Architecture

- `app/page.tsx`: frontend entry page and shell composition.
- `components/chat-shell.tsx`: compatibility export for the current chat shell API.
- `components/chat/chat-shell-container.tsx`: stateful orchestration layer.
- `components/chat/*.tsx`: presentational modules (header, thread, composer, case panel, support panel).
- `lib/api-client.ts`: browser API contract client with trace/error envelope handling.
- `lib/backend-proxy.ts`: server proxy and scaffold fallback behavior.

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
