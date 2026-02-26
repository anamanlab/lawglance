import type { RelatedCasePanelProps } from "@/components/chat/types";

function buildExportUnavailableReason(policyReason?: string | null): string {
  switch (policyReason) {
    case "source_export_blocked_by_policy":
      return "Online case review is still available. Direct PDF export is unavailable for this source under policy.";
    case "export_url_not_allowed_for_source":
    case "export_redirect_url_not_allowed_for_source":
      return "Online case review is still available. Direct PDF export is unavailable because the document URL is not trusted for this source.";
    case "source_not_in_registry_for_export":
      return "Online case review is still available. Direct PDF export is unavailable because this source is not registered for export.";
    case "source_export_metadata_missing":
      return "Online case review is still available. Direct PDF export is unavailable because source metadata is missing for this case.";
    case "document_url_host_untrusted":
      return "Online case review is still available. Direct PDF export is unavailable because the case document host is not trusted for this source.";
    default:
      return "Online case review is still available. Direct PDF export is unavailable for this case result.";
  }
}

function buildPdfUnavailableReason(pdfReason?: string | null): string {
  switch (pdfReason) {
    case "document_url_missing":
      return "This result is still usable online, but no decision document URL was returned for direct PDF export.";
    case "document_url_host_untrusted":
      return "This result is still usable online, but the document host is not trusted for direct PDF export.";
    case "document_url_unverified_source":
      return "This result is still usable online, but source metadata could not be verified for direct PDF export.";
    case "source_export_metadata_missing":
      return "This result is still usable online, but source metadata is missing for direct PDF export.";
    case "source_not_in_registry_for_export":
      return "This result is still usable online, but this source is not registered for direct PDF export.";
    case "source_not_in_policy_for_export":
      return "This result is still usable online, but this source is not approved for direct PDF export.";
    default:
      return "This result is still usable online, but direct PDF export is unavailable.";
  }
}

export function RelatedCasePanel({
  statusToneClass,
  supportStatus,
  showDiagnostics = false,
  isChatSubmitting,
  isCaseSearchSubmitting,
  isExportSubmitting,
  submissionPhase,
  caseSearchQuery,
  lastCaseSearchQuery,
  onCaseSearchQueryChange,
  relatedCasesStatus,
  relatedCases,
  matterProfile,
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

  const issueTags = matterProfile?.issue_tags;
  const targetCourt = matterProfile?.target_court;
  const displayTags = Array.isArray(issueTags) ? issueTags : issueTags ? [issueTags] : [];
  const disableCaseSearchControls = isChatSubmitting || isCaseSearchSubmitting;
  const disableExportControls = isChatSubmitting || isCaseSearchSubmitting || isExportSubmitting;

  return (
    <section className="imm-paper-card imm-fade-up rounded-2xl p-4 md:p-5" style={{ animationDelay: "200ms" }}>
      <div className="relative z-10">
        <div className="flex flex-wrap items-start justify-between gap-3 border-b border-[rgba(176,174,165,0.42)] pb-3">
          <div>
            <h2 className="text-lg font-semibold text-ink">Related case law</h2>
            <p className="mt-1 max-w-md text-xs leading-6 text-muted">
              Discover official case law matching your query.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <span className="imm-pill imm-pill-neutral text-[10px]">
              Sidebar tools
            </span>
            {showDiagnostics && supportStatus ? (
              <span
                className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.1em] ${statusToneClass ?? ""}`}
              >
                {supportStatus}
              </span>
            ) : null}
          </div>
        </div>

        <div className="mt-4 rounded-xl border border-[var(--imm-border-soft)] bg-[var(--imm-surface-warm)] p-3">
          <label
            className="mb-1 block min-h-[24px] py-1 text-[11px] font-semibold uppercase tracking-[0.14em] text-muted"
            htmlFor={caseSearchInputId}
          >
            Case search query
          </label>
          <input
            className="min-h-[44px] w-full rounded-lg border border-[rgba(176,174,165,0.78)] bg-[rgba(250,249,245,0.96)] px-3 py-2 text-xs leading-6 text-ink shadow-sm outline-none transition duration-150 focus:border-accent-blue focus:ring-2 focus:ring-[rgba(106,155,204,0.2)] disabled:cursor-not-allowed disabled:opacity-70"
            disabled={disableCaseSearchControls}
            id={caseSearchInputId}
            aria-describedby={caseSearchHintId}
            maxLength={300}
            onChange={(event) => {
              onCaseSearchQueryChange(event.target.value);
            }}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !disableCaseSearchControls && hasCaseSearchQuery) {
                event.preventDefault();
                onSearch();
              }
            }}
            placeholder="Example: Express Entry refusal Federal Court"
            type="text"
            value={caseSearchQuery}
          />
          <p
            className={`mt-2 text-[11px] leading-5 ${queryChangedSinceLastSearch ? "text-warning" : "text-muted"}`}
            id={caseSearchHintId}
          >
            {queryHint}
          </p>

          <div className="mt-3 flex flex-col items-stretch gap-2 sm:flex-row sm:flex-wrap sm:items-center">
            <button
              aria-controls={resultsListId}
              aria-expanded={hasResults}
              className="imm-btn-secondary px-3 py-1.5 text-xs"
              disabled={disableCaseSearchControls || !hasCaseSearchQuery}
              onClick={onSearch}
              type="button"
            >
              {isCaseSearchSubmitting && submissionPhase === "cases" ? "Searching..." : "Find related cases"}
            </button>
            <span className="self-start text-[10px] uppercase tracking-[0.12em] text-muted sm:self-auto">
              Grounded lawyer research
            </span>
          </div>
        </div>

        <div aria-live="polite" className="mt-3 min-h-[20px]" role="status">
          {isCaseSearchSubmitting && submissionPhase === "cases" ? (
            <div className="flex animate-pulse flex-col gap-2.5 py-1">
              <div className="h-2.5 w-3/4 rounded-full bg-[rgba(176,174,165,0.25)]" />
              <div className="h-2.5 w-1/2 rounded-full bg-[rgba(176,174,165,0.25)]" />
              <span className="sr-only">Running grounded lawyer case research...</span>
            </div>
          ) : (
            <p className="text-xs leading-6 text-muted">{relatedCasesStatus}</p>
          )}
        </div>

        {hasResults && lastCaseSearchQuery ? (
          <p className="mt-2 rounded-lg border border-[var(--imm-border-soft)] bg-[var(--imm-surface-soft)] px-3 py-2 text-[11px] leading-6 text-muted">
            Showing {relatedCases.length} related case{relatedCases.length === 1 ? "" : "s"} for: &quot;{lastCaseSearchQuery}&quot;
          </p>
        ) : null}

        {hasResults ? (
          <ul className="mt-3 space-y-3 text-xs text-muted" id={resultsListId}>
            {relatedCases.map((result) => {
              const exportUnavailable =
                result.export_allowed === false ||
                result.pdf_status === "unavailable" ||
                !result.source_id ||
                !result.document_url;
              const exportUnavailableReason = buildExportUnavailableReason(result.export_policy_reason);

              return (
                <li
                  className="overflow-hidden rounded-xl border border-[rgba(176,174,165,0.45)] bg-[rgba(250,249,245,0.96)]"
                  key={result.case_id}
                >
                  <div className="border-b border-[rgba(176,174,165,0.35)] px-3 py-3">
                    <a
                      className="block font-semibold leading-6 text-ink underline-offset-2 hover:underline"
                      href={result.url}
                      rel="noreferrer"
                      target="_blank"
                    >
                      {result.title}
                    </a>
                    <p className="mt-1 text-[11px] leading-5 text-muted">{result.citation}</p>
                  </div>

                  <div className="px-3 py-2">
                    <div className="flex flex-wrap items-center gap-2">
                      <span
                        className={`rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${
                          result.pdf_status === "available"
                            ? "border-[#b8c6a6] bg-[#eef2e7] text-[#5f7248]"
                            : "border-[rgba(217,119,87,0.35)] bg-[#f8eee8] text-warning"
                        }`}
                      >
                        {result.pdf_status === "available" ? "PDF available" : "Online review only"}
                      </span>
                      {result.court ? (
                        <span className="rounded-full border border-[rgba(176,174,165,0.45)] bg-[#ebe8df] px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-muted">
                          {result.court}
                        </span>
                      ) : null}
                      <span className="w-full text-[10px] uppercase tracking-[0.1em] text-muted sm:w-auto">
                        Decision date: {result.decision_date}
                      </span>
                    </div>

                    <p className="mt-2 rounded-lg border border-[rgba(176,174,165,0.4)] bg-[#f3f1ea] px-2.5 py-2 text-[11px] leading-5 text-muted">
                      {result.relevance_reason}
                    </p>

                    {result.summary ? (
                      <div className="mt-2 text-[11px] leading-5 text-muted">
                        <p className="font-semibold uppercase tracking-wider text-[10px] mb-0.5">Summary</p>
                        <p className="line-clamp-4 hover:line-clamp-none transition-all">{result.summary}</p>
                      </div>
                    ) : null}

                    <div className="mt-3 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                      <button
                        className="imm-btn-secondary px-2.5 py-1 text-[11px]"
                        disabled={disableExportControls || exportUnavailable}
                        onClick={() => onExportCase(result)}
                        type="button"
                      >
                        {isExportSubmitting &&
                        submissionPhase === "export" &&
                        exportingCaseId === result.case_id
                          ? "Exporting..."
                          : "Export PDF"}
                      </button>
                      <span className="text-[10px] uppercase tracking-[0.1em] text-muted">
                        Optional PDF export
                      </span>
                    </div>

                    {exportUnavailable ? (
                      <p className="mt-2 text-[11px] leading-5 text-muted">
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
      </div>
    </section>
  );
}
