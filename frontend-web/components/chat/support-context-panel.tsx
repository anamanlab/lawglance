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
    <section className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-xs text-slate-700 shadow-[0_8px_20px_rgba(15,23,42,0.08)]">
      <p className="font-semibold text-slate-800">Support context</p>
      <p className="mt-1">API target: {endpointLabel}</p>
      <p>Last endpoint: {supportContext?.endpoint ?? "Not called yet"}</p>
      <p>Last outcome: {supportContext ? supportContext.status : "Not available"}</p>
      <p>Last error code: {supportContext?.code ?? "None"}</p>
      <p>Last policy reason: {supportContext?.policyReason ?? "None"}</p>
      <p>Trace ID: {supportContext?.traceId ?? "Unavailable"}</p>
      {supportContext?.traceIdMismatch ? (
        <p className="mt-1 font-medium text-red-700">
          Trace mismatch detected between header and error body.
        </p>
      ) : null}
    </section>
  );
}
