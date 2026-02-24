import type { RelatedCasePanelProps } from "@/components/chat/types";

export function RelatedCasePanel({
  statusToneClass,
  supportStatus,
  isSubmitting,
  submissionPhase,
  pendingCaseQuery,
  relatedCasesStatus,
  relatedCases,
  onSearch,
}: RelatedCasePanelProps): JSX.Element {
  const resultsListId = "related-case-results";
  const hasResults = relatedCases.length > 0;

  return (
    <section className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm shadow-[0_8px_20px_rgba(15,23,42,0.08)]">
      <div className="mb-2 flex items-center justify-between gap-2">
        <p className="font-semibold text-slate-800">Related case search</p>
        <span
          className={`rounded-full border px-2.5 py-1 text-[11px] font-semibold uppercase tracking-wide ${statusToneClass}`}
        >
          {supportStatus ?? "idle"}
        </span>
      </div>

      <button
        aria-controls={resultsListId}
        aria-expanded={hasResults}
        className="min-h-[44px] min-w-[44px] rounded-md border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-800 transition duration-200 ease-out hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-60"
        disabled={isSubmitting || !pendingCaseQuery}
        onClick={onSearch}
        type="button"
      >
        {isSubmitting && submissionPhase === "cases" ? "Searching..." : "Search related cases"}
      </button>

      {relatedCasesStatus ? <p className="mt-1 text-slate-600">{relatedCasesStatus}</p> : null}

      {hasResults ? (
        <ul className="mt-2 space-y-2 text-xs text-slate-700" id={resultsListId}>
          {relatedCases.map((result) => (
            <li className="rounded-md border border-slate-200 bg-white p-2" key={result.case_id}>
              <a
                className="font-medium text-slate-900 underline underline-offset-2"
                href={result.url}
                rel="noreferrer"
                target="_blank"
              >
                {result.title}
              </a>
              <p className="mt-1">{result.citation}</p>
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}
