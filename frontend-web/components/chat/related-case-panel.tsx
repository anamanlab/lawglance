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
    default:
      return "Export unavailable for this case result.";
  }
}

export function RelatedCasePanel({
  statusToneClass,
  supportStatus,
  showDiagnostics = false,
  isSubmitting,
  submissionPhase,
  pendingCaseQuery,
  relatedCasesStatus,
  relatedCases,
  onSearch,
  onExportCase,
  exportingCaseId,
}: RelatedCasePanelProps): JSX.Element {
  const resultsListId = "related-case-results";
  const hasResults = relatedCases.length > 0;

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
        Find official Canadian court decisions related to your question.
      </p>

      <button
        aria-controls={resultsListId}
        aria-expanded={hasResults}
        className="min-h-[44px] min-w-[44px] rounded-md border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-800 transition duration-200 ease-out hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-60"
        disabled={isSubmitting || !pendingCaseQuery}
        onClick={onSearch}
        type="button"
      >
        {isSubmitting && submissionPhase === "cases" ? "Searching..." : "Find related cases"}
      </button>

      <p
        aria-live="polite"
        className="mt-2 min-h-[20px] text-slate-600"
      >
        {relatedCasesStatus}
      </p>

      {hasResults ? (
        <ul className="mt-2 space-y-2 text-xs text-slate-700" id={resultsListId}>
          {relatedCases.map((result) => {
            const exportUnavailable =
              result.export_allowed === false ||
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
                <p className="mt-1 text-[11px] text-slate-500">
                  Decision date: {result.decision_date}
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
                      {exportUnavailableReason}
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
