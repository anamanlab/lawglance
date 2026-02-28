# Chat Thinking Transparency Design

**Date:** 2026-02-27  
**Status:** Approved

## Context

The current chat UI provides strong answer/citation rendering and global workflow banners, but users cannot consistently see what the agent is doing while a response is in progress. We need a simpler, modern transparency pattern that builds trust without overwhelming the conversation flow.

## Goals

- Make agent progress visible in the chat workspace by default.
- Keep the default experience simple while allowing deeper inspection on demand.
- Improve trust through explicit stage/status/evidence signals.
- Preserve existing chat behavior and API contracts as much as possible.

## Non-Goals

- No backend streaming transport changes (SSE/WebSocket) in v1.
- No redesign of unrelated workflows outside chat transparency.
- No replacement of current global incident/status banner behavior.

## Experience Architecture

### Hybrid Thinking Layer

1. Inline Activity Strip (inside assistant turn)
- Always visible, compact status chips for the current/just-completed assistant turn.
- Example stages: Understanding question, Searching case law, Evaluating sources, Drafting answer, Completed.

2. Expandable Thinking Drawer (per assistant turn)
- User can expand to inspect detailed timeline entries.
- Each entry includes timestamp, state, concise details, and optional evidence/diagnostic metadata.

3. Trust-first defaults
- Inline strip remains visible by default.
- Drawer remains collapsed by default for simplicity.
- Users can inspect details only when needed.

## Component and Data Design

### New Frontend Activity Model

Add a typed event model in frontend chat state:

`AgentActivityEvent`
- `id`: stable unique event identifier
- `turnId`: groups events by assistant response turn
- `stage`: `intake | retrieval | grounding | synthesis | delivery`
- `status`: `running | success | warning | error | blocked`
- `label`: short user-facing status text
- `startedAt`: ISO timestamp
- `endedAt`: ISO timestamp (optional)
- `details`: optional explanatory text
- `meta`: optional map for diagnostics (`sourceCount`, `traceId`, `fallbackUsed`, `policyReason`)

### State Ownership

`use-chat-logic` is the single source of truth for activity events.

- Emit events as chat/search/export operations start/complete/fail.
- Assign one `turnId` per assistant response cycle.
- Derive events from existing signals first:
  - `submissionPhase`
  - `supportContext`
  - `chat response fallback_used`
  - `research_preview` and related source status

### UI Composition

- `MessageList` renders an inline `ActivityStrip` for assistant turns.
- New `ThinkingDrawer` renders detailed timeline events.
- `StatusBanner` remains global incident/workflow status and does not duplicate per-turn details.

## Interaction and Motion

## Interaction Rules

- Inline strip transitions active step to completed step with subtle motion.
- Drawer toggle labels:
  - `Show agent thinking`
  - `Hide details`
- If a step errors, auto-expand that step once, then preserve user-controlled collapse state.

## Motion Guidelines

- Keep transitions lightweight (160-240ms).
- Use short stagger (~40ms) when revealing timeline entries.
- Continuous animation only for currently-running step indicator.
- Respect `prefers-reduced-motion` and disable non-essential animation.

## Accessibility and Responsive Behavior

- Timeline updates announced via `aria-live="polite"`.
- Step status changes use plain language in accessible labels.
- Drawer toggle keyboard-accessible with proper `aria-expanded`.
- Diagnostic metadata is text-visible, not color-only.
- Mobile:
  - Inline strip remains in message bubble.
  - Drawer opens as bottom sheet.
- Desktop:
  - Drawer appears as inline expansion or adjacent panel depending on available space.
- Tap targets and controls remain at accessible sizes.

## Error Handling

- Timeline feature degrades gracefully if event mapping fails.
- Fallback/provider degradations appear as warning step with concise reason.
- Policy refusals mark delivery stage as blocked and include actionable user guidance.
- Retry actions create a new immutable turn timeline; prior timelines remain unchanged.

## Testing Strategy

1. Unit tests
- Event mapping/reducer behavior in `use-chat-logic`.
- Stage/status transitions for success, warning, blocked, and error paths.

2. Component tests
- Inline strip rendering per stage/state.
- Drawer expand/collapse behavior and keyboard interaction.
- Reduced-motion behavior.

3. Contract tests
- Mapping from existing API payload fields (`fallback_used`, `research_preview`, errors) into timeline events.
- No-regression coverage for standard chat send/render flow.

## Rollout Plan

- Add feature flag: `NEXT_PUBLIC_IMMCAD_ENABLE_AGENT_THINKING_TIMELINE`.
- Defaults:
  - Development: enabled.
  - Production: disabled initially.
- Dark launch to internal users first.
- Promote to production default after:
  - test pass
  - UX validation that transparency improves confidence without clutter.

## Future Extension

This model is intentionally compatible with later backend progress streaming (SSE/WebSocket). A future version can swap event source from inferred client lifecycle to server-emitted timeline events without redesigning the UI layer.
