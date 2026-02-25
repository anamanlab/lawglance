import type { RelatedCasePanelProps } from "@/components/chat/types";

function buildExportUnavailableReason(policyReason?: string | null): string {
  switch (policyReason) {
    case "source_export_blocked_by_policy":
      return "Export unavailable for this source under policy.";
    case "export_url_not_allowed_for_source":
    case "export_redirect_url_not_allowed_for_source":
      return "Export unavailable because the document URL is not trusted for this source.";
    case "source_not_in_registry_for_export":
      return "Export unavailable because this source is not registered for export.";
    case "source_export_metadata_missing":
      return "Export unavailable because source metadata is missing for this case.";
    case "document_url_host_untrusted":
      return "Export unavailable because the case document host is not trusted for this source.";
    default:
      return "Export unavailable for this case result.";
  }
}

function buildPdfUnavailableReason(pdfReason?: string | null): string {
  switch (pdfReason) {
    case "document_url_missing":
      return "PDF unavailable because no decision document URL was returned for this case.";
    case "document_url_host_untrusted":
      return "PDF unavailable because the document host is not trusted for this source.";
    case "source_not_in_registry_for_export":
      return "PDF unavailable because this source is not registered for export.";
    default:
      return "PDF unavailable for this case result.";
  }
}

export function RelatedCasePanel({
  statusToneClass,
  supportStatus,
  showDiagnostics = false,
  isSubmitting,
  submissionPhase,
  caseSearchQuery,
  lastCaseSearchQuery,
  onCaseSearchQueryChange,
  relatedCasesStatus,
  relatedCases,
  onSearch,
  onExportCase,
  exportingCaseId,
}: RelatedCasePanelProps): JSX.Element {
  const resultsListId = "related-case-results";
  const caseSearchInputId = "related-case-query";
  const caseSearchHintId = "related-case-query-hint";
  const normalizedCurrentQuery = caseSearchQuery.trim().toLowerCase();
  const normalizedLastSearchQuery = (lastCaseSearchQuery ?? "").trim().toLowerCase();
  const hasResults = relatedCases.length > 0;
  const hasCaseSearchQuery = caseSearchQuery.trim().length >= 2;
  const queryChangedSinceLastSearch =
    hasResults &&
    Boolean(normalizedCurrentQuery) &&
    Boolean(normalizedLastSearchQuery) &&
    normalizedCurrentQuery !== normalizedLastSearchQuery;

  const queryHint = queryChangedSinceLastSearch
    ? "Current query differs from the query used for the listed results."
    : "Tip: use program names, legal issues, court names, or citations for stronger case matches.";

  return (
    <section className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm shadow-[0_8px_20px_rgba(15,23,42,0.08)]">
      <div className="mb-2 flex items-center justify-between gap-2">
        <p className="font-semibold text-slate-800">Related case law</p>
        {showDiagnostics && statusToneClass && supportStatus ? (
          <span
            className={`rounded-full border px-2.5 py-1 text-[11px] font-semibold uppercase tracking-wide ${statusToneClass}`}
          >
            {supportStatus}
          </span>
        ) : null}
      </div>
      <p className="mb-3 text-xs text-slate-600">
        Case-law search is a separate service. We prefill it from your last chat question, and you can edit it.
      </p>

      <div className="mb-3 grid grid-cols-1 gap-2 sm:grid-cols-3">
        <p className="rounded-md border border-slate-200 bg-white px-2 py-1 text-[11px] font-medium text-slate-700">
          1. Ask a question
        </p>
        <p className="rounded-md border border-slate-200 bg-white px-2 py-1 text-[11px] font-medium text-slate-700">
          2. Refine case query
        </p>
        <p className="rounded-md border border-slate-200 bg-white px-2 py-1 text-[11px] font-medium text-slate-700">
          3. Review and export
        </p>
      </div>

      <label
        className="mb-1 block text-[11px] font-semibold uppercase tracking-wide text-slate-600"
        htmlFor={caseSearchInputId}
      >
        Case search query
      </label>
      <input
        className="w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-xs text-slate-900 shadow-sm outline-none transition duration-150 focus:border-slate-500 focus:ring-2 focus:ring-slate-300 disabled:cursor-not-allowed disabled:opacity-70"
        disabled={isSubmitting}
        id={caseSearchInputId}
        aria-describedby={caseSearchHintId}
        maxLength={300}
        onChange={(event) => {
          onCaseSearchQueryChange(event.target.value);
        }}
        onKeyDown={(event) => {
          if (event.key === "Enter" && !isSubmitting && hasCaseSearchQuery) {
            event.preventDefault();
            onSearch();
          }
        }}
        placeholder="Example: Express Entry refusal Federal Court"
        type="text"
        value={caseSearchQuery}
      />
      <p
        className={`mt-1 text-[11px] ${
          queryChangedSinceLastSearch ? "text-amber-700" : "text-slate-500"
        }`}
        id={caseSearchHintId}
      >
        {queryHint}
      </p>

      <button
        aria-controls={resultsListId}
        aria-expanded={hasResults}
        className="min-h-[44px] min-w-[44px] rounded-md border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-800 transition duration-200 ease-out hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-60"
        disabled={isSubmitting || !hasCaseSearchQuery}
        onClick={onSearch}
        type="button"
      >
        {isSubmitting && submissionPhase === "cases" ? "Searching..." : "Find related cases"}
      </button>

      <p
        aria-live="polite"
        className="mt-2 min-h-[20px] text-slate-600"
        role="status"
      >
        {relatedCasesStatus}
      </p>

      {hasResults && lastCaseSearchQuery ? (
        <p className="mt-1 rounded-md border border-slate-200 bg-white px-2 py-1 text-[11px] text-slate-600">
          Showing {relatedCases.length} related case
          {relatedCases.length === 1 ? "" : "s"} for: &quot;{lastCaseSearchQuery}&quot;
        </p>
      ) : null}

      {hasResults ? (
        <ul className="mt-2 space-y-2 text-xs text-slate-700" id={resultsListId}>
          {relatedCases.map((result) => {
            const exportUnavailable =
              result.export_allowed === false ||
              result.pdf_status === "unavailable" ||
              !result.source_id ||
              !result.document_url;
            const exportUnavailableReason = buildExportUnavailableReason(
              result.export_policy_reason
            );

            return (
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
                <div className="mt-1 flex flex-wrap items-center gap-2">
                  <span
                    className={`rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${
                      result.pdf_status === "available"
                        ? "border-emerald-200 bg-emerald-50 text-emerald-700"
                        : "border-amber-200 bg-amber-50 text-amber-700"
                    }`}
                  >
                    {result.pdf_status === "available"
                      ? "PDF available"
                      : "PDF unavailable"}
                  </span>
                  {result.court ? (
                    <span className="rounded-full border border-slate-200 bg-slate-100 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-slate-600">
                      {result.court}
                    </span>
                  ) : null}
                </div>
                <p className="mt-1 text-[11px] text-slate-500">
                  Decision date: {result.decision_date}
                </p>
                <p className="mt-1 rounded-md border border-slate-200 bg-slate-50 px-2 py-1 text-[11px] text-slate-700">
                  {result.relevance_reason}
                </p>
                <div className="mt-2">
                  <button
                    className="min-h-[36px] min-w-[44px] rounded-md border border-slate-300 bg-white px-2.5 py-1 text-[11px] font-semibold text-slate-800 transition duration-200 ease-out hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-60"
                    disabled={isSubmitting || exportUnavailable}
                    onClick={() => onExportCase(result)}
                    type="button"
                  >
                    {isSubmitting &&
                    submissionPhase === "export" &&
                    exportingCaseId === result.case_id
                      ? "Exporting..."
                      : "Export PDF"}
                  </button>
                  {exportUnavailable ? (
                    <p className="mt-1 text-[11px] text-slate-500">
                      {result.pdf_status === "unavailable"
                        ? buildPdfUnavailableReason(result.pdf_reason)
                        : exportUnavailableReason}
                    </p>
                  ) : null}
                </div>
              </li>
            );
          })}
        </ul>
      ) : null}
    </section>
  );
}
