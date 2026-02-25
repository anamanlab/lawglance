type ChatHeaderProps = {
  legalDisclaimer: string;
};

export function ChatHeader({ legalDisclaimer }: ChatHeaderProps): JSX.Element {
  return (
    <header className="rounded-2xl border border-[rgba(217,119,87,0.35)] bg-gradient-to-r from-[#f8eee8] via-[#f6f2ea] to-[#edf3ea] p-4 text-sm text-warning shadow-[0_10px_24px_rgba(20,20,19,0.08)]">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-lg font-semibold text-ink">Canada immigration scope notice</p>
        <span className="rounded-full border border-[rgba(217,119,87,0.35)] bg-[rgba(250,249,245,0.94)] px-3 py-1 text-xs font-semibold uppercase tracking-wide text-warning">
          Informational only
        </span>
      </div>
      <p className="mt-2 leading-6 text-ink">{legalDisclaimer}</p>
    </header>
  );
}
