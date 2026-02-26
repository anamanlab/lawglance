import type { SupportContext } from "@/components/chat/types";

type SupportContextPanelProps = {
  endpointLabel: string;
  supportContext: SupportContext | null;
};

export function SupportContextPanel({
  endpointLabel,
  supportContext,
}: SupportContextPanelProps): JSX.Element {
  return (
    <section className="imm-paper-card imm-fade-up rounded-2xl p-4" style={{ animationDelay: "240ms" }}>
      <div className="relative z-10">
        <div className="flex items-center justify-between gap-2 border-b border-[rgba(176,174,165,0.4)] pb-2">
          <p className="imm-kicker">Diagnostics</p>
          <span className="imm-pill imm-pill-neutral font-mono text-[10px]">
            OPS
          </span>
        </div>

        <p className="mt-2 text-sm font-semibold text-ink">Support context</p>

        <div className="imm-scrollbar mt-3 space-y-1 overflow-x-auto rounded-xl border border-[rgba(176,174,165,0.4)] bg-[rgba(247,243,234,0.62)] p-3 font-mono text-[11px] leading-6 text-muted">
          <p className="whitespace-nowrap">API target: {endpointLabel}</p>
          <p className="whitespace-nowrap">Last endpoint: {supportContext?.endpoint ?? "Not called yet"}</p>
          <p>Last outcome: {supportContext ? supportContext.status : "Not available"}</p>
          <p>Last error code: {supportContext?.code ?? "None"}</p>
          <p>Last policy reason: {supportContext?.policyReason ?? "None"}</p>
          <p>Trace ID: {supportContext?.traceId ?? "Unavailable"}</p>
        </div>

        {supportContext?.traceIdMismatch ? (
          <p className="mt-3 rounded-lg border border-[rgba(172,63,47,0.22)] bg-[var(--imm-danger-soft)] px-3 py-2 text-[11px] font-medium leading-5 text-[var(--imm-danger-ink)]">
            Trace mismatch detected between header and error body.
          </p>
        ) : null}
      </div>
    </section>
  );
}
