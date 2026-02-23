# Feature: Next.js Minimal Chat UI and Integration Contract

## Goal

Provide an implementation-ready migration plan from the current Streamlit interface to a minimal Next.js + Tailwind chat UI without changing backend API behavior.

## Scope

- Frontend migration planning only.
- Contract-first integration with existing `POST /api/chat` and error envelope behavior.
- Canada-only legal information experience with mandatory disclaimer handling.

## API Contract Expectations

Frontend must follow `docs/architecture/api-contracts.md` exactly:

- Chat success/refusal path: `POST /api/chat` returns `ChatResponse` with `answer`, `citations`, `confidence`, `disclaimer`, and optional `fallback_used`.
- Policy refusal is a `200` response with `fallback_used.reason = "policy_block"`; treat as handled response, not transport failure.
- Error path returns `ErrorEnvelope` with `error.code`, `error.message`, and `error.trace_id`.
- `x-trace-id` response header is canonical and must be captured for every response.
- For error responses, `error.trace_id` must match `x-trace-id`.

## Minimal UI Acceptance Criteria

1. Chat layout renders user and assistant messages in chronological order.
2. Assistant messages always display the legal disclaimer text returned by API.
3. Citation rendering:
   - Each citation renders `title` and links to `url`.
   - Optional `pin` and `snippet` render when present.
   - No synthetic placeholder citations are shown.
4. Refusal rendering:
   - Policy refusal content displays as assistant output in the standard chat stream.
   - Refusal path keeps disclaimer visible.
5. Error rendering:
   - User-safe error state by `error.code` (auth, rate-limit, validation, provider).
   - UI shows request trace ID from `x-trace-id` for support correlation.
6. Mobile support:
   - Input, message list, and citation block remain usable at 360px width.

## Implementation-Ready Migration Path (Next.js + Tailwind)

### Phase 1: App Skeleton

- Create `frontend-web` Next.js App Router project.
- Configure Tailwind and shared design tokens for spacing, typography, and state colors.
- Add environment wiring for API base URL and bearer token passthrough.

### Phase 2: Contract Client

- Implement typed API client methods:
  - `sendChatMessage(payload)` for `POST /api/chat`
  - shared parser for `ErrorEnvelope`
- Capture `x-trace-id` from every response and return it with parsed payload.
- Add client-side contract tests with mocked API envelopes (success, refusal, error).

### Phase 3: Minimal Chat UI

- Build components:
  - `ChatShell`
  - `MessageList`
  - `MessageComposer`
  - `CitationList`
  - `TraceBanner`
- Implement loading and retry behavior with non-blocking fallback indicators.
- Keep disclaimer persistent on every assistant message render.

### Phase 4: Integration and Verification

- Run frontend against local API scaffold (`uv run uvicorn immcad_api.main:app --app-dir src --reload --port 8000`).
- Validate refusal, citation-required, and provider-error behavior against live endpoints.
- Verify responsive behavior in browser before merge.

## Definition of Done

- Frontend contract behavior matches `docs/architecture/api-contracts.md` for success, refusal, and error envelopes.
- Minimal UI acceptance criteria pass in desktop and mobile viewport checks.
- No behavior widens scope beyond Canada legal informational use.
