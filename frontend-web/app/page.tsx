import { ChatShell } from "@/components/chat-shell";
import { getRuntimeConfig } from "@/lib/runtime-config";

const LEGAL_DISCLAIMER =
  "IMMCAD provides Canadian immigration information only and does not provide legal advice or representation.";

export const dynamic = "force-dynamic";

export default function HomePage(): JSX.Element {
  const { apiBaseUrl, enableRedesignedShell, showOperationalPanels } = getRuntimeConfig();

  if (!enableRedesignedShell) {
    return (
      <main className="min-h-screen px-4 py-6 md:py-10">
        <ChatShell
          apiBaseUrl={apiBaseUrl}
          legalDisclaimer={LEGAL_DISCLAIMER}
          showOperationalPanels={showOperationalPanels}
        />
      </main>
    );
  }

  return (
    <main className="min-h-screen px-4 py-6 md:py-10">
      <div className="mx-auto mb-4 w-full max-w-6xl px-1">
        <h1 className="mt-1 text-3xl font-semibold text-ink md:text-4xl">
          Canadian Immigration Information Assistant
        </h1>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-muted md:text-base">
          Understand official immigration pathways, requirements, and next steps with grounded information.
        </p>
      </div>

      <ChatShell
        apiBaseUrl={apiBaseUrl}
        legalDisclaimer={LEGAL_DISCLAIMER}
        showOperationalPanels={showOperationalPanels}
      />
    </main>
  );
}
