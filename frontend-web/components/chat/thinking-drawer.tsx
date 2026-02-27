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
        className="rounded-full border border-[rgba(176,174,165,0.55)] bg-[#f6f3eb] px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.08em] text-muted hover:bg-[#eee9de]"
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
          className="mt-2 space-y-1 rounded-xl border border-[rgba(176,174,165,0.45)] bg-[#f7f4ec] p-2 text-xs text-ink"
        >
          {events.map((event) => (
            <li key={event.id}>
              <span className="font-semibold">{event.label}</span>
              <span className="text-muted">{` (${event.status})`}</span>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
