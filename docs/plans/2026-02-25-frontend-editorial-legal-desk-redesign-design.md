# IMMCAD Frontend Editorial Legal Desk Redesign (Approved)

## Context
- Active UI target: `frontend-web` (Next.js), not legacy Streamlit.
- Existing functionality (chat, case-law search, export, diagnostics) must remain unchanged.
- User approved visual direction: **Editorial / Legal Desk**.

## Aesthetic Direction
- Warm paper/folio visual language with premium legal-research desk cues.
- Strong typography hierarchy using Anthropic brand-aligned fonts (`Poppins` headings, `Lora` body).
- Structured panels, ruled separators, dossier-like cards, and muted operational labels.
- Distinct but restrained color accents using Anthropic palette (orange/blue/green) on neutral paper backgrounds.

## UX Goals
- Improve scanability of transcript, citations, and related-case workflows.
- Make the app feel like a high-trust research workspace, not a generic chatbot.
- Preserve accessibility (focus visibility, readable contrast, keyboard flow, ARIA labels).

## Scope (This Pass)
- `frontend-web/app/page.tsx` hero/masthead redesign
- `frontend-web/components/chat/chat-shell-container.tsx` shell structure + layout framing
- `frontend-web/components/chat/chat-header.tsx` scope notice redesign
- `frontend-web/components/chat/status-banner.tsx` incident/error banner redesign
- `frontend-web/components/chat/message-list.tsx` transcript + message bubble redesign
- `frontend-web/components/chat/message-composer.tsx` composer card redesign
- `frontend-web/components/chat/quick-prompts.tsx` quick-prompt control redesign
- `frontend-web/components/chat/related-case-panel.tsx` sidebar case-law panel redesign
- `frontend-web/components/chat/support-context-panel.tsx` diagnostics panel redesign
- `frontend-web/app/globals.css` supporting editorial utility classes/effects (if needed)

## Constraints
- Do not change API calls, state management, or business logic.
- Do not change key action labels used by tests (`Send`, `Find related cases`, `Export PDF`, etc.).
- Maintain mobile responsiveness and sticky sidebar behavior on large screens.

## Implementation Plan
1. Reshape page shell + hero into an editorial masthead.
2. Rebuild chat shell card structure with layered paper effects and section labels.
3. Redesign transcript + composer together for visual cohesion.
4. Redesign sidebar panels and status/diagnostic treatments.
5. Run frontend lint + typecheck.
