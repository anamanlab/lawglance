import { useEffect, useState } from "react";

import {
  buildExportUnavailableReason,
  buildPdfUnavailableReason,
  confidenceToneClass,
  formatPrioritySourceStatus,
  formatSourceBadgeLabel,
  formatSourceEventTypeLabel,
  intakeToneClass,
  normalizeDocketNumbers,
  toCanliiSourceStatusLabel,
  toOfficialSourceStatusLabel,
} from "@/components/chat/related-case-panel-utils";
import type { RelatedCasePanelProps } from "@/components/chat/types";
import type { LawyerCaseSupport } from "@/lib/api-client";

type ResearchResultsPanelProps = Pick<
  RelatedCasePanelProps,
  | "relatedCases"
  | "lastCaseSearchQuery"
  | "relatedCasesRetrievalMode"
  | "sourceStatus"
  | "prioritySourceStatus"
  | "researchConfidence"
  | "confidenceReasons"
  | "intakeCompleteness"
  | "intakeHints"
  | "onExportCase"
  | "exportingCaseId"
  | "isExportSubmitting"
  | "submissionPhase"
> & {
  disableExportControls: boolean;
};

export function RelatedCasePanelResearchResults({
  relatedCases,
  lastCaseSearchQuery,
  relatedCasesRetrievalMode,
  sourceStatus,
  prioritySourceStatus,
  researchConfidence,
  confidenceReasons,
  intakeCompleteness,
  intakeHints,
  onExportCase,
  exportingCaseId,
  isExportSubmitting,
  submissionPhase,
  disableExportControls,
}: ResearchResultsPanelProps): JSX.Element {
  const [pendingExportCase, setPendingExportCase] = useState<LawyerCaseSupport | null>(null);
  const hasResults = relatedCases.length > 0;
  const shouldShowSourceCard = Boolean(sourceStatus);
  const officialStatus = sourceStatus?.official ?? "unknown";
  const canliiStatus = sourceStatus?.canlii ?? "unknown";
  const retrievalModeLabel =
    relatedCasesRetrievalMode === "auto"
      ? "Auto-retrieved for this answer"
      : relatedCasesRetrievalMode === "manual"
        ? "Manual case search"
        : null;

  useEffect(() => {
    if (!pendingExportCase) {
      return;
    }
    const handleKeyDown = (event: KeyboardEvent): void => {
      if (event.key === "Escape") {
        setPendingExportCase(null);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [pendingExportCase]);

  return (
    <>
      {hasResults && lastCaseSearchQuery ? (
        <div className="mt-2 rounded-lg border border-[var(--imm-border-soft)] bg-[var(--imm-surface-soft)] px-3 py-2 text-[11px] leading-6 text-muted">
          <p>
            Showing {relatedCases.length} related case{relatedCases.length === 1 ? "" : "s"} for: &quot;{lastCaseSearchQuery}&quot;
          </p>
          {retrievalModeLabel ? (
            <span className="mt-1 inline-flex rounded-full border border-[rgba(95,132,171,0.35)] bg-[var(--imm-accent-soft)] px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.08em] text-[var(--imm-accent-ink)]">
              {retrievalModeLabel}
            </span>
          ) : null}
        </div>
      ) : null}

      {shouldShowSourceCard ? (
        <div className="mt-2 rounded-lg border border-[var(--imm-border-soft)] bg-[var(--imm-surface-soft)] px-3 py-2 text-[11px] leading-5 text-muted">
          <span className="inline-flex rounded-full border border-[var(--imm-border-soft)] bg-[var(--imm-surface-strong)] px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.08em] text-muted">
            Source transparency
          </span>
          <p className="mt-2">
            {toOfficialSourceStatusLabel(officialStatus)} | {toCanliiSourceStatusLabel(canliiStatus)}
          </p>
          <p className="mt-1">{formatPrioritySourceStatus(prioritySourceStatus)}</p>
        </div>
      ) : null}

      {researchConfidence ? (
        <div className="mt-2 rounded-lg border border-[var(--imm-border-soft)] bg-[var(--imm-surface-soft)] px-3 py-2 text-[11px] leading-5 text-muted">
          <span
            className={`inline-flex rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.08em] ${confidenceToneClass(researchConfidence)}`}
          >
            Research confidence: {researchConfidence.toUpperCase()}
          </span>
          {confidenceReasons.length ? (
            <ul className="mt-2 space-y-1">
              {confidenceReasons.slice(0, 3).map((reason) => (
                <li key={reason}>{reason}</li>
              ))}
            </ul>
          ) : null}
        </div>
      ) : null}

      {intakeCompleteness ? (
        <div className="mt-2 rounded-lg border border-[var(--imm-border-soft)] bg-[var(--imm-surface-soft)] px-3 py-2 text-[11px] leading-5 text-muted">
          <span
            className={`inline-flex rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.08em] ${intakeToneClass(intakeCompleteness)}`}
          >
            Intake quality: {intakeCompleteness.toUpperCase()}
          </span>
          {intakeHints.length ? (
            <ul className="mt-2 space-y-1">
              {intakeHints.slice(0, 3).map((hint) => (
                <li key={hint}>{hint}</li>
              ))}
            </ul>
          ) : null}
        </div>
      ) : null}

      {hasResults ? (
        <ul className="mt-3 space-y-3 text-xs text-muted" id="related-case-results">
          {relatedCases.map((result) => {
            const exportUnavailable =
              result.export_allowed === false ||
              result.pdf_status === "unavailable" ||
              !result.source_id ||
              !result.document_url;
            const exportUnavailableReason = buildExportUnavailableReason(result.export_policy_reason);
            const sourceBadgeLabel = formatSourceBadgeLabel(result.source_id);
            const sourceEventTypeLabel = formatSourceEventTypeLabel(result.source_event_type);
            const docketNumbers = normalizeDocketNumbers(result.docket_numbers);

            return (
              <li
                className="overflow-hidden rounded-xl border border-[var(--imm-border-soft)] bg-[var(--imm-surface-soft)]"
                key={result.case_id}
              >
                <div className="border-b border-[rgba(159,154,142,0.42)] px-3 py-3">
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
                          ? "border-[rgba(111,132,89,0.35)] bg-[var(--imm-success-soft)] text-[var(--imm-success-ink)]"
                          : "border-[rgba(192,106,77,0.35)] bg-[var(--imm-primary-soft)] text-warning"
                      }`}
                    >
                      {result.pdf_status === "available" ? "PDF available" : "Online review only"}
                    </span>
                    {result.court ? (
                      <span className="rounded-full border border-[var(--imm-border-soft)] bg-[var(--imm-surface-strong)] px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-muted">
                        {result.court}
                      </span>
                    ) : null}
                    {sourceBadgeLabel ? (
                      <span className="rounded-full border border-[var(--imm-border-soft)] bg-[var(--imm-surface-strong)] px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-muted">
                        Source: {sourceBadgeLabel}
                      </span>
                    ) : null}
                    {sourceEventTypeLabel ? (
                      <span className="rounded-full border border-[rgba(95,132,171,0.35)] bg-[var(--imm-accent-soft)] px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-[var(--imm-accent-ink)]">
                        Event: {sourceEventTypeLabel}
                      </span>
                    ) : null}
                    <span className="w-full text-[10px] uppercase tracking-[0.1em] text-muted sm:w-auto">
                      Decision date: {result.decision_date}
                    </span>
                  </div>

                  <p className="mt-2 rounded-lg border border-[var(--imm-border-soft)] bg-[var(--imm-surface-strong)] px-2.5 py-2 text-[11px] leading-5 text-muted">
                    {result.relevance_reason}
                  </p>

                  {docketNumbers.length ? (
                    <div className="mt-2">
                      <p className="text-[10px] font-semibold uppercase tracking-[0.08em] text-muted">
                        Docket
                      </p>
                      <div className="mt-1 flex flex-wrap gap-1.5" aria-label="Docket numbers">
                        {docketNumbers.map((docketNumber) => (
                          <span
                            className="rounded-full border border-[var(--imm-border-soft)] bg-[var(--imm-surface-warm)] px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.06em] text-muted"
                            key={`${result.case_id}-${docketNumber}`}
                          >
                            {docketNumber}
                          </span>
                        ))}
                      </div>
                    </div>
                  ) : null}

                  {result.summary ? (
                    <div className="mt-2 text-[11px] leading-5 text-muted">
                      <p className="mb-0.5 text-[10px] font-semibold uppercase tracking-wider">Summary</p>
                      <p className="line-clamp-4 transition-all hover:line-clamp-none">{result.summary}</p>
                    </div>
                  ) : null}

                  <div className="mt-3 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                    <button
                      className="imm-btn-secondary px-2.5 py-1 text-[11px]"
                      disabled={disableExportControls || exportUnavailable}
                      onClick={() => setPendingExportCase(result)}
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

      {pendingExportCase ? (
        <div
          className="fixed inset-0 z-50 flex items-end justify-center bg-[rgba(20,20,19,0.45)] p-4 sm:items-center"
          onClick={() => setPendingExportCase(null)}
        >
          <div
            aria-labelledby="export-confirmation-title"
            aria-modal="true"
            className="w-full max-w-md rounded-xl border border-[var(--imm-border-soft)] bg-[var(--imm-surface-soft)] p-4 shadow-[0_18px_48px_rgba(20,20,19,0.2)]"
            onClick={(event) => event.stopPropagation()}
            role="dialog"
          >
            <p className="text-[10px] font-semibold uppercase tracking-[0.12em] text-muted">
              Export confirmation
            </p>
            <h3 className="mt-2 text-base font-semibold text-ink" id="export-confirmation-title">
              Export this case PDF now?
            </h3>
            <p className="mt-2 text-sm leading-6 text-muted">
              This will download the decision document from the official source for:
            </p>
            <p className="mt-2 rounded-lg border border-[var(--imm-border-soft)] bg-[var(--imm-surface-warm)] px-3 py-2 text-xs font-semibold text-ink">
              {pendingExportCase.title}
            </p>
            <div className="mt-4 flex flex-col gap-2 sm:flex-row sm:justify-end">
              <button
                className="imm-btn-secondary px-3 py-1.5 text-xs"
                disabled={disableExportControls}
                onClick={() => setPendingExportCase(null)}
                type="button"
              >
                Cancel
              </button>
              <button
                className="imm-btn-primary px-3 py-1.5 text-xs"
                disabled={disableExportControls}
                onClick={() => {
                  onExportCase(pendingExportCase);
                  setPendingExportCase(null);
                }}
                type="button"
              >
                Export PDF now
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </>
  );
}

