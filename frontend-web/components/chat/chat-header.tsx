import type { FrontendLocale } from "@/components/chat/types";

type ChatHeaderProps = {
  legalDisclaimer: string;
  activeLocale: FrontendLocale;
  onLocaleChange: (value: FrontendLocale) => void;
};

export function ChatHeader({
  legalDisclaimer,
  activeLocale,
  onLocaleChange,
}: ChatHeaderProps): JSX.Element {
  return (
    <header className="mb-4 flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-[rgba(176,174,165,0.42)] pb-4">
      <div>
        <h2 className="text-xl font-semibold leading-tight text-ink">
          IMMCAD Assistant
        </h2>
        <p className="mt-1 text-[11px] leading-snug text-muted max-w-2xl">
          {legalDisclaimer}
        </p>
      </div>

      <div className="flex flex-wrap items-center gap-2 shrink-0">
        <label className="flex items-center gap-2 rounded-full border border-[rgba(176,174,165,0.65)] bg-[#f6f3eb] px-2 py-1 text-[10px] font-semibold uppercase tracking-[0.08em] text-muted">
          Language
          <select
            aria-label="Interface language"
            className="rounded-md border border-[rgba(176,174,165,0.72)] bg-white px-1.5 py-1 text-[10px] font-semibold uppercase tracking-[0.04em] text-ink"
            onChange={(event) => onLocaleChange(event.target.value as FrontendLocale)}
            value={activeLocale}
          >
            <option value="en-CA">English</option>
            <option value="fr-CA">Francais</option>
          </select>
        </label>
        <span className="imm-pill imm-pill-orange">
          Informational only
        </span>
        <span className="imm-pill imm-pill-blue">
          Cite sources
        </span>
      </div>
    </header>
  );
}
