import { useState } from "react";

import type { AgentActivityEvent } from "@/components/chat/types";

type ThinkingDrawerProps = {
  events: AgentActivityEvent[];
};

export function ThinkingDrawer({ events }: ThinkingDrawerProps): JSX.Element | null {
  const [isOpen, setIsOpen] = useState(false);

  if (events.length === 0) {
    return null;
  }

  return (
    <div className="mt-2">
      <button
        aria-expanded={isOpen}
        className="imm-activity-animate rounded-full border border-[var(--imm-border-soft)] bg-[var(--imm-surface-strong)] px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.08em] text-muted hover:bg-[var(--imm-surface-muted)]"
        onClick={() => {
          setIsOpen((current) => !current);
        }}
        type="button"
      >
        {isOpen ? "Hide details" : "Show agent thinking"}
      </button>
      {isOpen ? (
        <ul
          aria-label="Timeline details"
          aria-live="polite"
          className="mt-2 space-y-1 rounded-xl border border-[var(--imm-border-soft)] bg-[var(--imm-surface)] p-2 text-xs text-ink"
        >
          {events.map((event) => (
            <li
              aria-label={`${event.label} (${event.status})`}
              className="imm-activity-animate"
              data-activity-status={event.status}
              key={event.id}
            >
              <span className="font-semibold">{event.label}</span>
              <span className="text-muted">{` (${event.status})`}</span>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
