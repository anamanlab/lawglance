import { ChatShell } from "@/components/chat-shell";
import { getRuntimeConfig } from "@/lib/runtime-config";

const LEGAL_DISCLAIMER =
  "IMMCAD provides Canadian immigration information only and does not provide legal advice or representation.";

export const dynamic = "force-dynamic";

export default function HomePage(): JSX.Element {
  const { apiBaseUrl, enableRedesignedShell } = getRuntimeConfig();

  if (!enableRedesignedShell) {
    return (
      <main className="min-h-screen px-4 py-6 md:py-10">
        <ChatShell apiBaseUrl={apiBaseUrl} legalDisclaimer={LEGAL_DISCLAIMER} />
      </main>
    );
  }

  return (
    <main className="min-h-screen px-4 py-6 md:py-10">
      <div className="mx-auto mb-4 w-full max-w-6xl px-1">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-blue-800/90">
          IMMCAD workspace
        </p>
        <h1 className="mt-1 text-3xl font-semibold text-slate-900 md:text-4xl">
          Canada immigration research assistant
        </h1>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-700 md:text-base">
          Ask focused questions, inspect citations, and capture support context with traceability.
        </p>
      </div>

      <ChatShell apiBaseUrl={apiBaseUrl} legalDisclaimer={LEGAL_DISCLAIMER} />
    </main>
  );
}
