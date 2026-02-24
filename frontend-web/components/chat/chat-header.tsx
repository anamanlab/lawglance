type ChatHeaderProps = {
  legalDisclaimer: string;
};

export function ChatHeader({ legalDisclaimer }: ChatHeaderProps): JSX.Element {
  return (
    <header className="rounded-2xl border border-amber-300 bg-gradient-to-r from-amber-50 via-orange-50 to-amber-100 p-4 text-sm text-warning shadow-[0_10px_24px_rgba(180,83,9,0.12)]">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-lg font-semibold text-slate-900">Canada legal scope notice</p>
        <span className="rounded-full border border-amber-300 bg-white px-3 py-1 text-xs font-semibold uppercase tracking-wide text-amber-700">
          Informational only
        </span>
      </div>
      <p className="mt-2 leading-6 text-slate-800">{legalDisclaimer}</p>
    </header>
  );
}
