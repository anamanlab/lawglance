# Chat Thinking Transparency Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a hybrid chat transparency experience that shows agent thinking stages inline and in an expandable per-turn timeline, gated by a frontend feature flag.

**Architecture:** Extend frontend chat state with a per-turn `AgentActivityEvent` timeline generated from existing request lifecycle and response metadata. Render this timeline in two synchronized views: compact inline strip and expandable details drawer. Keep rollout safe via `NEXT_PUBLIC_IMMCAD_ENABLE_AGENT_THINKING_TIMELINE`, default-on in development and default-off in production.

**Tech Stack:** Next.js 14, React 18, TypeScript, TailwindCSS, Vitest, Testing Library.

---

### Task 1: Add Feature Flag Contract and Plumbing

**Files:**
- Modify: `frontend-web/lib/runtime-config.ts`
- Modify: `frontend-web/app/page.tsx`
- Modify: `frontend-web/components/chat/types.ts`
- Test: `frontend-web/tests/runtime-config.test.ts`
- Test: `frontend-web/tests/home-page.rollout.test.tsx`

**Step 1: Write the failing test**

```ts
it("exposes thinking timeline flag defaults", () => {
  delete process.env.NEXT_PUBLIC_IMMCAD_ENABLE_AGENT_THINKING_TIMELINE;
  const config = getRuntimeConfig();
  expect(config.enableAgentThinkingTimeline).toBe(true);
});
```

**Step 2: Run test to verify it fails**

Run: `cd frontend-web && npm run test -- tests/runtime-config.test.ts`  
Expected: FAIL because `enableAgentThinkingTimeline` is missing from runtime config.

**Step 3: Write minimal implementation**

```ts
export type RuntimeConfig = {
  // existing fields...
  enableAgentThinkingTimeline: boolean;
};

const enableAgentThinkingTimeline = parseBooleanFlag(
  process.env.NEXT_PUBLIC_IMMCAD_ENABLE_AGENT_THINKING_TIMELINE,
  nodeEnv !== "production"
);
```

**Step 4: Run tests to verify pass**

Run: `cd frontend-web && npm run test -- tests/runtime-config.test.ts tests/home-page.rollout.test.tsx`  
Expected: PASS.

**Step 5: Commit**

```bash
git add frontend-web/lib/runtime-config.ts frontend-web/app/page.tsx frontend-web/components/chat/types.ts frontend-web/tests/runtime-config.test.ts frontend-web/tests/home-page.rollout.test.tsx
git commit -m "feat(chat): add thinking timeline feature flag plumbing"
```

### Task 2: Add Activity Timeline Domain Types and Helpers

**Files:**
- Modify: `frontend-web/components/chat/types.ts`
- Create: `frontend-web/components/chat/agent-activity.ts`
- Test: `frontend-web/tests/agent-activity.contract.test.ts`

**Step 1: Write the failing test**

```ts
it("builds initial running timeline for a new assistant turn", () => {
  const events = buildInitialTurnEvents("turn-1");
  expect(events[0]?.stage).toBe("intake");
  expect(events[0]?.status).toBe("running");
});
```

**Step 2: Run test to verify it fails**

Run: `cd frontend-web && npm run test -- tests/agent-activity.contract.test.ts`  
Expected: FAIL because helper module does not exist.

**Step 3: Write minimal implementation**

```ts
export type AgentActivityStage = "intake" | "retrieval" | "grounding" | "synthesis" | "delivery";
export type AgentActivityStatus = "running" | "success" | "warning" | "error" | "blocked";

export function buildInitialTurnEvents(turnId: string): AgentActivityEvent[] {
  return [{ id: `${turnId}-intake`, turnId, stage: "intake", status: "running", label: "Understanding question", startedAt: new Date().toISOString() }];
}
```

**Step 4: Run test to verify it passes**

Run: `cd frontend-web && npm run test -- tests/agent-activity.contract.test.ts`  
Expected: PASS.

**Step 5: Commit**

```bash
git add frontend-web/components/chat/types.ts frontend-web/components/chat/agent-activity.ts frontend-web/tests/agent-activity.contract.test.ts
git commit -m "feat(chat): add activity timeline domain model"
```

### Task 3: Integrate Timeline State Into Chat Logic

**Files:**
- Modify: `frontend-web/components/chat/use-chat-logic.ts`
- Modify: `frontend-web/components/chat/types.ts`
- Test: `frontend-web/tests/chat-shell.ui.test.tsx`
- Test: `frontend-web/tests/chat-shell.contract.test.tsx`

**Step 1: Write the failing test**

```tsx
it("shows running timeline step while chat request is pending", async () => {
  // render + deferred fetch
  expect(await screen.findByText("Understanding question")).toBeTruthy();
});
```

**Step 2: Run test to verify it fails**

Run: `cd frontend-web && npm run test -- tests/chat-shell.ui.test.tsx -t "running timeline"`  
Expected: FAIL because timeline data is not exposed.

**Step 3: Write minimal implementation**

```ts
const [activityByTurn, setActivityByTurn] = useState<Record<string, AgentActivityEvent[]>>({});

// on submit start: seed intake/retrieval running events
// on response success: close running stages, add synthesis/delivery success
// on fallback/error/policy: set warning/error/blocked statuses with meta
```

**Step 4: Run tests to verify pass**

Run: `cd frontend-web && npm run test -- tests/chat-shell.ui.test.tsx tests/chat-shell.contract.test.tsx`  
Expected: PASS with updated assertions.

**Step 5: Commit**

```bash
git add frontend-web/components/chat/use-chat-logic.ts frontend-web/components/chat/types.ts frontend-web/tests/chat-shell.ui.test.tsx frontend-web/tests/chat-shell.contract.test.tsx
git commit -m "feat(chat): emit per-turn activity timeline events"
```

### Task 4: Build Inline Activity Strip UI

**Files:**
- Create: `frontend-web/components/chat/activity-strip.tsx`
- Modify: `frontend-web/components/chat/message-list.tsx`
- Test: `frontend-web/tests/chat-shell.ui.test.tsx`

**Step 1: Write the failing test**

```tsx
it("renders inline activity strip for assistant turn", async () => {
  expect(await screen.findByText("Agent activity")).toBeTruthy();
});
```

**Step 2: Run test to verify it fails**

Run: `cd frontend-web && npm run test -- tests/chat-shell.ui.test.tsx -t "inline activity strip"`  
Expected: FAIL because component is missing.

**Step 3: Write minimal implementation**

```tsx
export function ActivityStrip({ events }: { events: AgentActivityEvent[] }) {
  return (
    <div aria-label="Agent activity" className="flex flex-wrap gap-1.5">
      {events.map((event) => <span key={event.id}>{event.label}</span>)}
    </div>
  );
}
```

**Step 4: Run test to verify pass**

Run: `cd frontend-web && npm run test -- tests/chat-shell.ui.test.tsx`  
Expected: PASS.

**Step 5: Commit**

```bash
git add frontend-web/components/chat/activity-strip.tsx frontend-web/components/chat/message-list.tsx frontend-web/tests/chat-shell.ui.test.tsx
git commit -m "feat(chat): add inline agent activity strip"
```

### Task 5: Build Expandable Thinking Drawer UI

**Files:**
- Create: `frontend-web/components/chat/thinking-drawer.tsx`
- Modify: `frontend-web/components/chat/message-list.tsx`
- Test: `frontend-web/tests/chat-shell.ui.test.tsx`

**Step 1: Write the failing test**

```tsx
it("toggles thinking drawer details for assistant turn", async () => {
  await user.click(screen.getByRole("button", { name: "Show agent thinking" }));
  expect(screen.getByText("Timeline details")).toBeTruthy();
});
```

**Step 2: Run test to verify it fails**

Run: `cd frontend-web && npm run test -- tests/chat-shell.ui.test.tsx -t "thinking drawer"`  
Expected: FAIL because toggle/details panel does not exist.

**Step 3: Write minimal implementation**

```tsx
export function ThinkingDrawer({ events }: { events: AgentActivityEvent[] }) {
  const [open, setOpen] = useState(false);
  return (
    <div>
      <button aria-expanded={open} onClick={() => setOpen((v) => !v)}>
        {open ? "Hide details" : "Show agent thinking"}
      </button>
      {open ? <ul aria-label="Timeline details">...</ul> : null}
    </div>
  );
}
```

**Step 4: Run test to verify pass**

Run: `cd frontend-web && npm run test -- tests/chat-shell.ui.test.tsx`  
Expected: PASS.

**Step 5: Commit**

```bash
git add frontend-web/components/chat/thinking-drawer.tsx frontend-web/components/chat/message-list.tsx frontend-web/tests/chat-shell.ui.test.tsx
git commit -m "feat(chat): add expandable thinking drawer"
```

### Task 6: Wire Feature Flag Through Chat Shell Rendering

**Files:**
- Modify: `frontend-web/components/chat/chat-shell-container.tsx`
- Modify: `frontend-web/components/chat/types.ts`
- Modify: `frontend-web/components/chat/message-list.tsx`
- Test: `frontend-web/tests/chat-shell.contract.test.tsx`

**Step 1: Write the failing test**

```tsx
it("hides timeline UI when feature flag is disabled", () => {
  render(<ChatShell ... enableAgentThinkingTimeline={false} />);
  expect(screen.queryByText("Show agent thinking")).toBeNull();
});
```

**Step 2: Run test to verify it fails**

Run: `cd frontend-web && npm run test -- tests/chat-shell.contract.test.tsx -t "feature flag is disabled"`  
Expected: FAIL because prop is not wired.

**Step 3: Write minimal implementation**

```tsx
<MessageList
  enableAgentThinkingTimeline={enableAgentThinkingTimeline}
  activityByTurn={activityByTurn}
  ...
/>
```

**Step 4: Run tests to verify pass**

Run: `cd frontend-web && npm run test -- tests/chat-shell.contract.test.tsx tests/chat-shell.ui.test.tsx`  
Expected: PASS.

**Step 5: Commit**

```bash
git add frontend-web/components/chat/chat-shell-container.tsx frontend-web/components/chat/types.ts frontend-web/components/chat/message-list.tsx frontend-web/tests/chat-shell.contract.test.tsx
git commit -m "feat(chat): gate timeline UI behind runtime flag"
```

### Task 7: Add Motion, Reduced-Motion, and Timeline Styling

**Files:**
- Modify: `frontend-web/app/globals.css`
- Modify: `frontend-web/components/chat/activity-strip.tsx`
- Modify: `frontend-web/components/chat/thinking-drawer.tsx`
- Test: `frontend-web/tests/chat-shell.ui.test.tsx`

**Step 1: Write the failing test**

```tsx
it("uses accessible labels and status semantics for timeline entries", async () => {
  expect(await screen.findByRole("list", { name: "Timeline details" })).toBeTruthy();
});
```

**Step 2: Run test to verify it fails**

Run: `cd frontend-web && npm run test -- tests/chat-shell.ui.test.tsx -t "status semantics"`  
Expected: FAIL due missing aria labels/structure.

**Step 3: Write minimal implementation**

```css
@media (prefers-reduced-motion: reduce) {
  .imm-activity-animate { animation: none !important; transition: none !important; }
}
```

```tsx
<li aria-live="polite" aria-label={`${event.label} (${event.status})`}>...</li>
```

**Step 4: Run tests to verify pass**

Run: `cd frontend-web && npm run test -- tests/chat-shell.ui.test.tsx`  
Expected: PASS.

**Step 5: Commit**

```bash
git add frontend-web/app/globals.css frontend-web/components/chat/activity-strip.tsx frontend-web/components/chat/thinking-drawer.tsx frontend-web/tests/chat-shell.ui.test.tsx
git commit -m "feat(chat): add accessible timeline motion and styling"
```

### Task 8: Final Verification and Documentation

**Files:**
- Modify: `frontend-web/.env.example`
- Modify: `frontend-web/README.md`
- Modify: `docs/plans/2026-02-27-chat-thinking-transparency-design.md` (optional rollout notes)

**Step 1: Write/Update tests for docs-referenced flag behavior (if missing)**

```ts
it("documents timeline feature flag in env examples", () => {
  expect(readEnvExample()).toContain("NEXT_PUBLIC_IMMCAD_ENABLE_AGENT_THINKING_TIMELINE");
});
```

**Step 2: Run verification suite**

Run: `cd frontend-web && npm run test -- tests/runtime-config.test.ts tests/chat-shell.ui.test.tsx tests/chat-shell.contract.test.tsx tests/home-page.rollout.test.tsx tests/agent-activity.contract.test.ts`  
Expected: PASS.

Run: `cd frontend-web && npm run lint`  
Expected: PASS.

Run: `cd frontend-web && npm run typecheck`  
Expected: PASS.

**Step 3: Update docs with rollout and flag guidance**

```md
NEXT_PUBLIC_IMMCAD_ENABLE_AGENT_THINKING_TIMELINE=true
```

**Step 4: Re-run quick regression after docs/env edits**

Run: `cd frontend-web && npm run test -- tests/runtime-config.test.ts tests/home-page.rollout.test.tsx`  
Expected: PASS.

**Step 5: Commit**

```bash
git add frontend-web/.env.example frontend-web/README.md docs/plans/2026-02-27-chat-thinking-transparency-design.md
git commit -m "docs(chat): add thinking timeline rollout guidance"
```

## End-to-End Verification Checklist

- Run: `cd frontend-web && npm run test`
- Run: `cd frontend-web && npm run lint`
- Run: `cd frontend-web && npm run typecheck`
- Manually verify desktop and mobile behavior in local dev:
  - `cd frontend-web && npm run dev`
  - Confirm inline strip always visible for assistant turn.
  - Confirm drawer toggle behavior and accessibility labels.
  - Confirm warning/error timeline entries on fallback/policy/error paths.

## Rollback Plan

- Set `NEXT_PUBLIC_IMMCAD_ENABLE_AGENT_THINKING_TIMELINE=false` to disable all timeline UI without reverting code.
- If a regression is detected post-deploy, disable flag and ship fix in follow-up patch.
