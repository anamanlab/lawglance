import { ChatShell } from "@/components/chat-shell";
import { getRuntimeConfig } from "@/lib/runtime-config";

const LEGAL_DISCLAIMER =
  "IMMCAD provides Canadian immigration information only and does not provide legal advice or representation.";

export const dynamic = "force-dynamic";

export default function HomePage(): JSX.Element {
  const { apiBaseUrl } = getRuntimeConfig();

  return (
    <main className="min-h-screen px-4 py-6 md:py-10">
      <ChatShell apiBaseUrl={apiBaseUrl} legalDisclaimer={LEGAL_DISCLAIMER} />
    </main>
  );
}
