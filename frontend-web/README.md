# frontend-web

Minimal Next.js App Router + Tailwind chat shell for IMMCAD (`US-006`).

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
