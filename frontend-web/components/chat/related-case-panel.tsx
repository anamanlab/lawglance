import type { RelatedCasePanelProps } from "@/components/chat/types";
import { isLowSpecificityCaseQuery } from "@/components/chat/case-query-specificity";

const LOW_SPECIFICITY_HINT =
  "Query may be too broad. Add at least two anchors: program/issue and court or citation.";

const DEFAULT_QUERY_HINT =
  "Tip: use program names, legal issues, court names, or citations for stronger case matches.";

function normalizeIssueTag(value: string): string {
  return value.replace(/_/g, " ");
}

function toCourtLabel(value?: string | null): string | null {
  if (!value) {
    return null;
  }

  switch (value.trim().toLowerCase()) {
    case "fc":
      return "Federal Court";
    case "fca":
      return "Federal Court of Appeal";
    case "scc":
      return "Supreme Court";
    default:
      return value.trim().toUpperCase();
  }
}

function buildRefinementSuggestions(params: {
  query: string;
  matterProfile?: Record<string, string | string[] | null>;
}): string[] {
  const { query, matterProfile } = params;
  const baseQuery = query.trim().replace(/\s+/g, " ");
  const suggestions: string[] = [];

  if (baseQuery) {
    suggestions.push(`${baseQuery} Federal Court`);
    suggestions.push(`${baseQuery} procedural fairness`);
    suggestions.push(`${baseQuery} 2024 FC 101`);
  }

  const issueTags = matterProfile?.issue_tags;
  const normalizedIssueTags = Array.isArray(issueTags)
    ? issueTags
    : issueTags
      ? [issueTags]
      : [];
  for (const issueTag of normalizedIssueTags) {
    const displayTag = normalizeIssueTag(issueTag);
    suggestions.push(baseQuery ? `${baseQuery} ${displayTag}` : `${displayTag} Federal Court`);
  }

  const courtLabel = toCourtLabel(matterProfile?.target_court as string | null | undefined);
  if (courtLabel) {
    suggestions.push(baseQuery ? `${baseQuery} ${courtLabel}` : `${courtLabel} precedent`);
  }

  const seen = new Set<string>();
  const uniqueSuggestions: string[] = [];
  for (const suggestion of suggestions) {
    const compactSuggestion = suggestion.trim().replace(/\s+/g, " ");
    if (!compactSuggestion || compactSuggestion.length > 120) {
      continue;
    }
    if (baseQuery && compactSuggestion.toLowerCase() === baseQuery.toLowerCase()) {
      continue;
    }
    const normalizedSuggestion = compactSuggestion.toLowerCase();
    if (seen.has(normalizedSuggestion)) {
      continue;
    }
    seen.add(normalizedSuggestion);
    uniqueSuggestions.push(compactSuggestion);
  }

  return uniqueSuggestions.slice(0, 4);
}

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

function confidenceToneClass(confidence: "low" | "medium" | "high"): string {
  if (confidence === "high") {
    return "border-[#b8c6a6] bg-[#eef2e7] text-[#5f7248]";
  }
  if (confidence === "medium") {
    return "border-[rgba(106,155,204,0.35)] bg-[#eef3f8] text-[#436280]";
  }
  return "border-[rgba(217,119,87,0.35)] bg-[#f8eee8] text-warning";
}

function intakeToneClass(completeness: "low" | "medium" | "high"): string {
  if (completeness === "high") {
    return "border-[#b8c6a6] bg-[#eef2e7] text-[#5f7248]";
  }
  if (completeness === "medium") {
    return "border-[rgba(106,155,204,0.35)] bg-[#eef3f8] text-[#436280]";
  }
  return "border-[rgba(217,119,87,0.35)] bg-[#f8eee8] text-warning";
}

function toSourceBucket(sourceId?: string | null): "official" | "canlii" | "unknown" {
  const normalizedSourceId = (sourceId ?? "").trim().toUpperCase();
  if (!normalizedSourceId) {
    return "unknown";
  }
  if (normalizedSourceId.startsWith("CANLII")) {
    return "canlii";
  }
  if (
    normalizedSourceId === "FC_DECISIONS" ||
    normalizedSourceId === "FCA_DECISIONS" ||
    normalizedSourceId === "SCC_DECISIONS"
  ) {
    return "official";
  }
  return "unknown";
}

function toOfficialSourceStatusLabel(status: string): string {
  if (status === "ok") {
    return "Official courts: available";
  }
  if (status === "unavailable") {
    return "Official courts: unavailable";
  }
  if (status === "no_match") {
    return "Official courts: no direct match";
  }
  return "Official courts: status unknown";
}

function toCanliiSourceStatusLabel(status: string): string {
  if (status === "used") {
    return "CanLII: used as supplement";
  }
  if (status === "unavailable") {
    return "CanLII: unavailable";
  }
  if (status === "not_used") {
    return "CanLII: not used";
  }
  return "CanLII: status unknown";
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
  relatedCasesRetrievalMode,
  sourceStatus,
  onCaseSearchQueryChange,
  relatedCasesStatus,
  researchConfidence,
  confidenceReasons,
  intakeCompleteness,
  intakeHints,
  relatedCases,
  matterProfile,
  intakeObjective,
  intakeTargetCourt,
  intakeProceduralPosture,
  intakeIssueTags,
  intakeAnchorReference,
  intakeDateFrom,
  intakeDateTo,
  onIntakeObjectiveChange,
  onIntakeTargetCourtChange,
  onIntakeProceduralPostureChange,
  onIntakeIssueTagsChange,
  onIntakeAnchorReferenceChange,
  onIntakeDateFromChange,
  onIntakeDateToChange,
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
  const lowSpecificityQuery = isLowSpecificityCaseQuery(caseSearchQuery);
  const queryChangedSinceLastSearch =
    hasResults &&
    Boolean(normalizedCurrentQuery) &&
    Boolean(normalizedLastSearchQuery) &&
    normalizedCurrentQuery !== normalizedLastSearchQuery;
  const retrievalModeLabel =
    relatedCasesRetrievalMode === "auto"
      ? "Auto-retrieved for this answer"
      : relatedCasesRetrievalMode === "manual"
        ? "Manual case search"
        : null;
  const sourceCounts = relatedCases.reduce(
    (counts, result) => {
      const sourceBucket = toSourceBucket(result.source_id);
      if (sourceBucket === "official") {
        counts.official += 1;
      } else if (sourceBucket === "canlii") {
        counts.canlii += 1;
      } else {
        counts.unknown += 1;
      }
      return counts;
    },
    { official: 0, canlii: 0, unknown: 0 }
  );
  const shouldShowSourceCard = Boolean(sourceStatus) || hasResults;
  const officialStatus = sourceStatus?.official ?? (sourceCounts.official ? "ok" : "unknown");
  const canliiStatus = sourceStatus?.canlii ?? (sourceCounts.canlii ? "used" : "unknown");

  const queryHint = queryChangedSinceLastSearch
    ? "Current query differs from the query used for the listed results."
    : lowSpecificityQuery
      ? LOW_SPECIFICITY_HINT
      : DEFAULT_QUERY_HINT;
  const refinementSuggestions = buildRefinementSuggestions({
    query: caseSearchQuery,
    matterProfile,
  });

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
            <h2 className="text-lg font-semibold text-ink">Case-law precedents</h2>
            <p className="mt-1 max-w-md text-xs leading-6 text-muted">
              Conversation answers appear in the main thread; precedent results appear here.
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
            className={`mt-2 text-[11px] leading-5 ${queryChangedSinceLastSearch || lowSpecificityQuery ? "text-warning" : "text-muted"}`}
            id={caseSearchHintId}
          >
            {queryHint}
          </p>

          <div className="mt-3 rounded-lg border border-[rgba(176,174,165,0.45)] bg-[rgba(247,243,234,0.72)] p-3">
            <p className="text-[10px] uppercase tracking-[0.12em] text-muted">
              Research intake (recommended)
            </p>
            <p className="mt-1 text-[11px] leading-5 text-muted">
              Add context so ranking and confidence are grounded in your litigation objective.
            </p>
            <div className="mt-2 grid gap-2 sm:grid-cols-2">
              <label className="text-[11px] text-muted">
                Research objective
                <select
                  aria-label="Research objective"
                  className="mt-1 min-h-[38px] w-full rounded-md border border-[rgba(176,174,165,0.72)] bg-white px-2 text-xs text-ink"
                  disabled={disableCaseSearchControls}
                  onChange={(event) => onIntakeObjectiveChange(event.target.value as typeof intakeObjective)}
                  value={intakeObjective}
                >
                  <option value="">Not specified</option>
                  <option value="support_precedent">Support precedent</option>
                  <option value="distinguish_precedent">Distinguish precedent</option>
                  <option value="background_research">Background research</option>
                </select>
              </label>
              <label className="text-[11px] text-muted">
                Target court
                <select
                  aria-label="Target court"
                  className="mt-1 min-h-[38px] w-full rounded-md border border-[rgba(176,174,165,0.72)] bg-white px-2 text-xs text-ink"
                  disabled={disableCaseSearchControls}
                  onChange={(event) => onIntakeTargetCourtChange(event.target.value)}
                  value={intakeTargetCourt}
                >
                  <option value="">Not specified</option>
                  <option value="fc">Federal Court (FC)</option>
                  <option value="fca">Federal Court of Appeal (FCA)</option>
                  <option value="scc">Supreme Court (SCC)</option>
                </select>
              </label>
              <label className="text-[11px] text-muted">
                Procedural posture
                <select
                  aria-label="Procedural posture"
                  className="mt-1 min-h-[38px] w-full rounded-md border border-[rgba(176,174,165,0.72)] bg-white px-2 text-xs text-ink"
                  disabled={disableCaseSearchControls}
                  onChange={(event) =>
                    onIntakeProceduralPostureChange(event.target.value as typeof intakeProceduralPosture)
                  }
                  value={intakeProceduralPosture}
                >
                  <option value="">Not specified</option>
                  <option value="judicial_review">Judicial review</option>
                  <option value="appeal">Appeal</option>
                  <option value="motion">Motion</option>
                  <option value="application">Application</option>
                </select>
              </label>
              <label className="text-[11px] text-muted">
                Issue tags
                <input
                  aria-label="Issue tags"
                  className="mt-1 min-h-[38px] w-full rounded-md border border-[rgba(176,174,165,0.72)] bg-white px-2 text-xs text-ink"
                  disabled={disableCaseSearchControls}
                  onChange={(event) => onIntakeIssueTagsChange(event.target.value)}
                  placeholder="procedural_fairness, inadmissibility"
                  type="text"
                  value={intakeIssueTags}
                />
              </label>
              <label className="text-[11px] text-muted sm:col-span-2">
                Citation or docket anchor
                <input
                  aria-label="Citation or docket anchor"
                  className="mt-1 min-h-[38px] w-full rounded-md border border-[rgba(176,174,165,0.72)] bg-white px-2 text-xs text-ink"
                  disabled={disableCaseSearchControls}
                  onChange={(event) => onIntakeAnchorReferenceChange(event.target.value)}
                  placeholder="2024 FCA 77 or A-77-23"
                  type="text"
                  value={intakeAnchorReference}
                />
              </label>
              <label className="text-[11px] text-muted">
                Decision date from
                <input
                  aria-label="Decision date from"
                  className="mt-1 min-h-[38px] w-full rounded-md border border-[rgba(176,174,165,0.72)] bg-white px-2 text-xs text-ink"
                  disabled={disableCaseSearchControls}
                  onChange={(event) => onIntakeDateFromChange(event.target.value)}
                  type="date"
                  value={intakeDateFrom}
                />
              </label>
              <label className="text-[11px] text-muted">
                Decision date to
                <input
                  aria-label="Decision date to"
                  className="mt-1 min-h-[38px] w-full rounded-md border border-[rgba(176,174,165,0.72)] bg-white px-2 text-xs text-ink"
                  disabled={disableCaseSearchControls}
                  onChange={(event) => onIntakeDateToChange(event.target.value)}
                  type="date"
                  value={intakeDateTo}
                />
              </label>
            </div>
          </div>

          {refinementSuggestions.length ? (
            <div className="mt-3">
              <p className="text-[10px] uppercase tracking-[0.12em] text-muted">
                Query refinements
              </p>
              <div className="mt-2 flex flex-wrap gap-2">
                {refinementSuggestions.map((suggestion) => (
                  <button
                    className="imm-btn-secondary px-2.5 py-1 text-[11px]"
                    disabled={disableCaseSearchControls}
                    key={suggestion}
                    onClick={() => {
                      onCaseSearchQueryChange(suggestion);
                    }}
                    type="button"
                  >
                    {suggestion}
                  </button>
                ))}
              </div>
            </div>
          ) : null}

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
          <div className="mt-2 rounded-lg border border-[var(--imm-border-soft)] bg-[var(--imm-surface-soft)] px-3 py-2 text-[11px] leading-6 text-muted">
            <p>
              Showing {relatedCases.length} related case{relatedCases.length === 1 ? "" : "s"} for: &quot;{lastCaseSearchQuery}&quot;
            </p>
            {retrievalModeLabel ? (
              <span className="mt-1 inline-flex rounded-full border border-[rgba(106,155,204,0.35)] bg-[#eef3f8] px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.08em] text-[#436280]">
                {retrievalModeLabel}
              </span>
            ) : null}
          </div>
        ) : null}

        {shouldShowSourceCard ? (
          <div className="mt-2 rounded-lg border border-[var(--imm-border-soft)] bg-[rgba(250,249,245,0.96)] px-3 py-2 text-[11px] leading-5 text-muted">
            <span className="inline-flex rounded-full border border-[rgba(176,174,165,0.45)] bg-[#ebe8df] px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.08em] text-muted">
              Source transparency
            </span>
            <p className="mt-2">
              {toOfficialSourceStatusLabel(officialStatus)} | {toCanliiSourceStatusLabel(canliiStatus)}
            </p>
            <p className="mt-1">
              Results by source: Official {sourceCounts.official}, CanLII {sourceCounts.canlii}, Other {sourceCounts.unknown}
            </p>
          </div>
        ) : null}

        {researchConfidence ? (
          <div className="mt-2 rounded-lg border border-[var(--imm-border-soft)] bg-[rgba(250,249,245,0.96)] px-3 py-2 text-[11px] leading-5 text-muted">
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
          <div className="mt-2 rounded-lg border border-[var(--imm-border-soft)] bg-[rgba(250,249,245,0.96)] px-3 py-2 text-[11px] leading-5 text-muted">
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
