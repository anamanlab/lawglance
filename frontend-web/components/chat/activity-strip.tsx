import type { AgentActivityEvent } from "@/components/chat/types";

type ActivityStripProps = {
  events: AgentActivityEvent[];
};

function statusClasses(status: AgentActivityEvent["status"]): string {
  if (status === "success") {
    return "border-[#b8c6a6] bg-[#eef2e7] text-[#5f7248]";
  }
  if (status === "warning") {
    return "border-[rgba(217,119,87,0.35)] bg-[#f8eee8] text-[#8a543f]";
  }
  if (status === "error" || status === "blocked") {
    return "border-[rgba(172,63,47,0.22)] bg-[#fcece9] text-[#8f4635]";
  }
  return "border-[rgba(106,155,204,0.35)] bg-[#edf3fa] text-[#4d6f95]";
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
