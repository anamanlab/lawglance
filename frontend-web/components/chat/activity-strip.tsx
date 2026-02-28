import type { AgentActivityEvent } from "@/components/chat/types";

type ActivityStripProps = {
  events: AgentActivityEvent[];
};

function statusClasses(status: AgentActivityEvent["status"]): string {
  if (status === "success") {
    return "border-[rgba(111,132,89,0.35)] bg-[var(--imm-success-soft)] text-[var(--imm-success-ink)]";
  }
  if (status === "warning") {
    return "border-[rgba(192,106,77,0.35)] bg-[var(--imm-primary-soft)] text-[var(--imm-warning-ink)]";
  }
  if (status === "error" || status === "blocked") {
    return "border-[rgba(172,63,47,0.22)] bg-[var(--imm-danger-soft)] text-[var(--imm-danger-ink)]";
  }
  return "border-[rgba(95,132,171,0.35)] bg-[var(--imm-accent-soft)] text-[var(--imm-accent-ink)]";
}

export function ActivityStrip({ events }: ActivityStripProps): JSX.Element | null {
  if (events.length === 0) {
    return null;
  }

  return (
    <div aria-label="Agent activity" aria-live="polite" className="mt-2 flex flex-wrap gap-1.5">
      {events.map((event) => (
        <span
          aria-label={`${event.label} (${event.status})`}
          className={`imm-activity-animate inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.08em] ${statusClasses(event.status)}`}
          data-activity-status={event.status}
          key={event.id}
        >
          {event.label}
        </span>
      ))}
    </div>
  );
}
