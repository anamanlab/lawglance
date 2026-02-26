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
    <main className="min-h-screen px-4 py-6 md:px-6 md:py-10">
      <div className="mx-auto w-full max-w-6xl">
        <section
          className="imm-fade-up mb-5 overflow-hidden rounded-[1.5rem] border border-[rgba(176,174,165,0.65)] bg-[rgba(250,249,245,0.78)] p-4 shadow-[0_12px_34px_rgba(20,20,19,0.06)] backdrop-blur-sm md:p-6"
          style={{ animationDelay: "40ms" }}
        >
          <div className="flex flex-col items-center justify-center text-center py-2">
            <p className="imm-kicker">IMMCAD</p>
            <h1 className="mt-3 max-w-3xl text-3xl font-semibold leading-tight text-ink md:text-4xl lg:text-[2.5rem]">
              Canadian Immigration Assistant
            </h1>
            <p className="mt-3 max-w-2xl text-sm leading-7 text-muted md:text-base mx-auto">
              Understand official immigration pathways, requirements, and next steps with grounded information.
            </p>
          </div>
        </section>

        <ChatShell
          apiBaseUrl={apiBaseUrl}
          legalDisclaimer={LEGAL_DISCLAIMER}
          showOperationalPanels={showOperationalPanels}
        />
      </div>
    </main>
  );
}
