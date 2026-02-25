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
    case "document_url_unverified_source":
      return "PDF unavailable because the source metadata could not be verified for this document.";
    case "source_export_metadata_missing":
      return "PDF unavailable because source metadata is missing for this case.";
    case "source_not_in_registry_for_export":
      return "PDF unavailable because this source is not registered for export.";
    case "source_not_in_policy_for_export":
      return "PDF unavailable because this source is not approved for export policy.";
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
    <section className="rounded-lg border border-[rgba(176,174,165,0.45)] bg-[#f3f1ea] p-3 text-sm shadow-[0_8px_20px_rgba(20,20,19,0.06)]">
      <div className="mb-2 flex items-center justify-between gap-2">
        <p className="font-semibold text-ink">Related case law</p>
        {showDiagnostics && statusToneClass && supportStatus ? (
          <span
            className={`rounded-full border px-2.5 py-1 text-[11px] font-semibold uppercase tracking-wide ${statusToneClass}`}
          >
            {supportStatus}
          </span>
        ) : null}
      </div>
      <p className="mb-3 text-xs text-muted">
        Case-law search is a separate service. We prefill it from your last chat question, and you can edit it.
      </p>

      <div className="mb-3 grid grid-cols-1 gap-2 sm:grid-cols-3">
        <p className="rounded-md border border-[rgba(176,174,165,0.45)] bg-[rgba(250,249,245,0.94)] px-2 py-1 text-[11px] font-medium text-muted">
          1. Ask a question
        </p>
        <p className="rounded-md border border-[rgba(176,174,165,0.45)] bg-[rgba(250,249,245,0.94)] px-2 py-1 text-[11px] font-medium text-muted">
          2. Refine case query
        </p>
        <p className="rounded-md border border-[rgba(176,174,165,0.45)] bg-[rgba(250,249,245,0.94)] px-2 py-1 text-[11px] font-medium text-muted">
          3. Review and export
        </p>
      </div>

      <label
        className="mb-1 block text-[11px] font-semibold uppercase tracking-wide text-muted"
        htmlFor={caseSearchInputId}
      >
        Case search query
      </label>
      <input
        className="w-full rounded-md border border-[rgba(176,174,165,0.85)] bg-[rgba(250,249,245,0.96)] px-3 py-2 text-xs text-ink shadow-sm outline-none transition duration-150 focus:border-accent-blue focus:ring-2 focus:ring-[rgba(106,155,204,0.2)] disabled:cursor-not-allowed disabled:opacity-70"
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
          queryChangedSinceLastSearch ? "text-warning" : "text-muted"
        }`}
        id={caseSearchHintId}
      >
        {queryHint}
      </p>

      <button
        aria-controls={resultsListId}
        aria-expanded={hasResults}
        className="min-h-[44px] min-w-[44px] rounded-md border border-[rgba(176,174,165,0.8)] bg-[rgba(250,249,245,0.94)] px-3 py-1.5 text-xs font-semibold text-ink transition duration-200 ease-out hover:bg-[#ebe8df] disabled:cursor-not-allowed disabled:opacity-60"
        disabled={isSubmitting || !hasCaseSearchQuery}
        onClick={onSearch}
        type="button"
      >
        {isSubmitting && submissionPhase === "cases" ? "Searching..." : "Find related cases"}
      </button>

      <p
        aria-live="polite"
        className="mt-2 min-h-[20px] text-muted"
        role="status"
      >
        {relatedCasesStatus}
      </p>

      {hasResults && lastCaseSearchQuery ? (
        <p className="mt-1 rounded-md border border-[rgba(176,174,165,0.45)] bg-[rgba(250,249,245,0.94)] px-2 py-1 text-[11px] text-muted">
          Showing {relatedCases.length} related case
          {relatedCases.length === 1 ? "" : "s"} for: &quot;{lastCaseSearchQuery}&quot;
        </p>
      ) : null}

      {hasResults ? (
        <ul className="mt-2 space-y-2 text-xs text-muted" id={resultsListId}>
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
              <li className="rounded-md border border-[rgba(176,174,165,0.45)] bg-[rgba(250,249,245,0.96)] p-2" key={result.case_id}>
                <a
                  className="font-medium text-ink underline underline-offset-2"
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
                        ? "border-[#b8c6a6] bg-[#eef2e7] text-[#5f7248]"
                        : "border-[rgba(217,119,87,0.35)] bg-[#f8eee8] text-warning"
                    }`}
                  >
                    {result.pdf_status === "available"
                      ? "PDF available"
                      : "PDF unavailable"}
                  </span>
                  {result.court ? (
                    <span className="rounded-full border border-[rgba(176,174,165,0.45)] bg-[#ebe8df] px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-muted">
                      {result.court}
                    </span>
                  ) : null}
                </div>
                <p className="mt-1 text-[11px] text-muted">
                  Decision date: {result.decision_date}
                </p>
                <p className="mt-1 rounded-md border border-[rgba(176,174,165,0.45)] bg-[#f3f1ea] px-2 py-1 text-[11px] text-muted">
                  {result.relevance_reason}
                </p>
                <div className="mt-2">
                  <button
                    className="min-h-[36px] min-w-[44px] rounded-md border border-[rgba(176,174,165,0.8)] bg-[rgba(250,249,245,0.94)] px-2.5 py-1 text-[11px] font-semibold text-ink transition duration-200 ease-out hover:bg-[#ebe8df] disabled:cursor-not-allowed disabled:opacity-60"
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
                    <p className="mt-1 text-[11px] text-muted">
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
