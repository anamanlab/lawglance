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
    <section className="rounded-lg border border-[rgba(176,174,165,0.45)] bg-[#f3f1ea] p-3 text-xs text-muted shadow-[0_8px_20px_rgba(20,20,19,0.06)]">
      <p className="font-semibold text-ink">Support context</p>
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
