import { ChatShell } from "@/components/chat-shell";
import { getRuntimeConfig } from "@/lib/runtime-config";

const LEGAL_DISCLAIMER =
  "IMMCAD provides Canadian immigration information only and does not provide legal advice or representation.";

export const dynamic = "force-dynamic";

export default function HomePage(): JSX.Element {
  const { apiBaseUrl } = getRuntimeConfig();

  return (
    <main className="min-h-screen bg-gradient-to-b from-slate-100 via-slate-200 to-slate-100 px-4 py-8 md:py-12">
      <ChatShell apiBaseUrl={apiBaseUrl} legalDisclaimer={LEGAL_DISCLAIMER} />
    </main>
  );
}
