type ChatHeaderProps = {
  legalDisclaimer: string;
};

export function ChatHeader({ legalDisclaimer }: ChatHeaderProps): JSX.Element {
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
