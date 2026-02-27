import { useEffect, useState } from "react";
import type {
  DocumentCompilationPaginationSummary,
  RelatedCasePanelProps,
} from "@/components/chat/types";
import { isLowSpecificityCaseQuery } from "@/components/chat/case-query-specificity";
import type { LawyerCaseSupport } from "@/lib/api-client";

const LOW_SPECIFICITY_HINT =
  "Query may be too broad. Add at least two anchors: program/issue and court or citation.";

const DEFAULT_QUERY_HINT =
  "Tip: use program names, legal issues, court names, or citations for stronger case matches.";

type WorkflowMode = "research" | "documents";

function normalizeIssueTag(value: string): string {
  return value.replace(/_/g, " ");
}

function toTitleCase(value: string): string {
  return value.toLowerCase().replace(/\b\w/g, (character) => character.toUpperCase());
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

function formatSourceBadgeLabel(sourceId?: string | null): string | null {
  if (!sourceId) {
    return null;
  }

  const normalizedSourceId = sourceId.trim().toUpperCase();
  if (!normalizedSourceId) {
    return null;
  }

  switch (normalizedSourceId) {
    case "FC_DECISIONS":
      return "Federal Court Decisions";
    case "FCA_DECISIONS":
      return "Federal Court of Appeal Decisions";
    case "SCC_DECISIONS":
      return "Supreme Court Decisions";
    case "CANLII_CASE_BROWSE":
      return "CanLII Case Browse";
    default:
      return toTitleCase(normalizedSourceId.replace(/_/g, " "));
  }
}

function formatSourceEventTypeLabel(value?: string | null): string | null {
  if (!value) {
    return null;
  }

  const normalizedValue = value.trim().toLowerCase();
  if (!normalizedValue) {
    return null;
  }

  switch (normalizedValue) {
    case "new":
      return "New";
    case "updated":
      return "Updated";
    case "translated":
      return "Translated";
    case "corrected":
      return "Corrected";
    default:
      return toTitleCase(normalizedValue.replace(/_/g, " "));
  }
}

function normalizeDocketNumbers(docketNumbers?: string[] | null): string[] {
  if (!Array.isArray(docketNumbers) || docketNumbers.length === 0) {
    return [];
  }

  const uniqueDocketNumbers: string[] = [];
  const seen = new Set<string>();
  for (const docketNumber of docketNumbers) {
    if (typeof docketNumber !== "string") {
      continue;
    }
    const normalizedDocket = docketNumber.trim();
    if (!normalizedDocket) {
      continue;
    }
    const dedupeKey = normalizedDocket.toLowerCase();
    if (seen.has(dedupeKey)) {
      continue;
    }
    seen.add(dedupeKey);
    uniqueDocketNumbers.push(normalizedDocket);
  }
  return uniqueDocketNumbers.slice(0, 6);
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

function formatIssueLabel(value: string): string {
  return value.replace(/_/g, " ");
}

function formatRuleScope(value: "base" | "conditional"): string {
  return value === "conditional" ? "Conditional rule" : "Base rule";
}

function uploadStatusLabel(status: "pending" | "uploaded" | "needs_review" | "failed"): string {
  if (status === "pending") {
    return "Uploading";
  }
  if (status === "needs_review") {
    return "Needs review";
  }
  if (status === "failed") {
    return "Failed";
  }
  return "Uploaded";
}

function uploadStatusTone(status: "pending" | "uploaded" | "needs_review" | "failed"): string {
  if (status === "pending") {
    return "border-[rgba(106,155,204,0.35)] bg-[#eef3f8] text-[#436280]";
  }
  if (status === "needs_review") {
    return "border-[rgba(217,119,87,0.35)] bg-[#f8eee8] text-warning";
  }
  if (status === "failed") {
    return "border-[rgba(172,63,47,0.22)] bg-[var(--imm-danger-soft)] text-[var(--imm-danger-ink)]";
  }
  return "border-[#b8c6a6] bg-[#eef2e7] text-[#5f7248]";
}

function toViolationSeverity(value: string): "blocking" | "warning" {
  return value.trim().toLowerCase() === "blocking" ? "blocking" : "warning";
}

function toSectionStatus(value: string): "present" | "missing" | "warning" {
  const normalizedValue = value.trim().toLowerCase();
  if (normalizedValue === "missing") {
    return "missing";
  }
  if (normalizedValue === "warning") {
    return "warning";
  }
  return "present";
}

function sectionStatusTone(value: "present" | "missing" | "warning"): string {
  if (value === "missing") {
    return "border-[rgba(172,63,47,0.22)] bg-[var(--imm-danger-soft)] text-[var(--imm-danger-ink)]";
  }
  if (value === "warning") {
    return "border-[rgba(217,119,87,0.35)] bg-[#f8eee8] text-warning";
  }
  return "border-[#b8c6a6] bg-[#eef2e7] text-[#5f7248]";
}

function sectionStatusLabel(value: "present" | "missing" | "warning"): string {
  if (value === "missing") {
    return "Missing";
  }
  if (value === "warning") {
    return "Warning";
  }
  return "Complete";
}

function violationSeverityTone(value: "blocking" | "warning"): string {
  if (value === "blocking") {
    return "border-[rgba(172,63,47,0.22)] bg-[var(--imm-danger-soft)] text-[var(--imm-danger-ink)]";
  }
  return "border-[rgba(217,119,87,0.35)] bg-[#f8eee8] text-warning";
}

function formatPageRange(startPage: number | null, endPage: number | null): string {
  if (typeof startPage === "number" && typeof endPage === "number") {
    return `Pages ${startPage}-${endPage}`;
  }
  if (typeof startPage === "number") {
    return `Starts at page ${startPage}`;
  }
  if (typeof endPage === "number") {
    return `Ends at page ${endPage}`;
  }
  return "Page range unavailable";
}

function toNonNegativeInteger(value: unknown): number | null {
  if (typeof value !== "number" || !Number.isFinite(value) || value < 0) {
    return null;
  }
  return Math.trunc(value);
}

function formatPaginationSummary(
  summary: DocumentCompilationPaginationSummary | null | undefined
): string | null {
  if (typeof summary === "string") {
    const normalizedSummary = summary.trim();
    return normalizedSummary || null;
  }
  if (!summary || typeof summary !== "object") {
    return null;
  }

  const summaryRecord = summary as Record<string, unknown>;
  const totalDocuments = toNonNegativeInteger(
    summaryRecord.total_documents ?? summaryRecord.totalDocuments
  );
  const totalPages = toNonNegativeInteger(summaryRecord.total_pages ?? summaryRecord.totalPages);
  const lastAssignedPage = toNonNegativeInteger(
    summaryRecord.last_assigned_page ?? summaryRecord.lastAssignedPage
  );

  const segments: string[] = [];
  if (typeof totalDocuments === "number") {
    segments.push(
      `${totalDocuments} compiled ${totalDocuments === 1 ? "document" : "documents"}`
    );
  }
  if (typeof totalPages === "number") {
    segments.push(`${totalPages} ${totalPages === 1 ? "page" : "pages"}`);
  }
  if (typeof lastAssignedPage === "number") {
    segments.push(`last assigned page ${lastAssignedPage}`);
  }

  if (!segments.length) {
    return null;
  }
  return `Pagination summary: ${segments.join(", ")}.`;
}

function buildBlockedReasons(params: {
  missingRequiredItems: string[];
  blockingIssues: string[];
  unresolvedRequirementStatuses: {
    item: string;
    reason: string | null;
    ruleScope: "base" | "conditional";
  }[];
  blockingRuleViolations: {
    code: string;
    remediation: string | null;
  }[];
}): string[] {
  const reasons: string[] = [];
  for (const item of params.missingRequiredItems) {
    reasons.push(`Add required document: ${formatIssueLabel(item)}.`);
  }
  for (const issue of params.blockingIssues) {
    reasons.push(`Resolve blocking issue: ${formatIssueLabel(issue)}.`);
  }
  for (const status of params.unresolvedRequirementStatuses) {
    if (status.reason) {
      reasons.push(
        `${formatIssueLabel(status.item)} (${formatRuleScope(status.ruleScope)}): ${status.reason}`
      );
    }
  }
  for (const violation of params.blockingRuleViolations) {
    reasons.push(
      `Resolve blocking rule ${violation.code}: ${violation.remediation ?? "See source guidance."}`
    );
  }
  return Array.from(new Set(reasons)).slice(0, 6);
}

export function RelatedCasePanel({
  statusToneClass,
  supportStatus,
  showDiagnostics = false,
  documentForum,
  documentMatterId,
  documentStatusMessage,
  documentUploads,
  documentReadiness,
  isDocumentIntakeSubmitting,
  isDocumentReadinessSubmitting,
  isDocumentPackageSubmitting,
  isDocumentDownloadSubmitting,
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
  onDocumentForumChange,
  onDocumentMatterIdChange,
  onDocumentUpload,
  onRefreshDocumentReadiness,
  onBuildDocumentPackage,
  onDownloadDocumentPackage,
  documentSupportMatrix,
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
  const documentUploadInputId = "document-intake-upload";
  const documentDropzoneHintId = "document-intake-dropzone-hint";
  const hasMatterId = documentMatterId.trim().length > 0;
  const [isDocumentDropActive, setIsDocumentDropActive] = useState(false);
  const [activeWorkflowMode, setActiveWorkflowMode] = useState<WorkflowMode>("research");
  const [showAdvancedIntake, setShowAdvancedIntake] = useState(false);
  const [pendingExportCase, setPendingExportCase] = useState<LawyerCaseSupport | null>(null);
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
  const shouldShowSourceCard = Boolean(sourceStatus);
  const officialStatus = sourceStatus?.official ?? "unknown";
  const canliiStatus = sourceStatus?.canlii ?? "unknown";

  const queryHint = queryChangedSinceLastSearch
    ? "Current query differs from the query used for the listed results."
    : lowSpecificityQuery
      ? LOW_SPECIFICITY_HINT
      : DEFAULT_QUERY_HINT;
  const refinementSuggestions = buildRefinementSuggestions({
    query: caseSearchQuery,
    matterProfile,
  });
  const latestCompilation = documentReadiness?.latestCompilation ?? null;

  const disableDocumentControls =
    isDocumentIntakeSubmitting ||
    isDocumentReadinessSubmitting ||
    isDocumentPackageSubmitting ||
    isDocumentDownloadSubmitting;
  const disableGeneratePackage = disableDocumentControls || !hasMatterId;
  const hasCompiledBinder =
    latestCompilation?.compilationOutputMode === "compiled_pdf" &&
    latestCompilation.compiledArtifact !== null;
  const disableDownloadPackage = disableDocumentControls || !hasMatterId || !hasCompiledBinder;
  const metadataOnlyDownloadHint =
    latestCompilation?.compilationOutputMode === "metadata_plan_only"
      ? "Download unavailable: compilation mode is metadata only. Generate a compiled PDF binder to enable download."
      : null;
  const disableCaseSearchControls = isChatSubmitting || isCaseSearchSubmitting;
  const disableExportControls = isChatSubmitting || isCaseSearchSubmitting || isExportSubmitting;
  const unresolvedRequirementStatuses = (documentReadiness?.requirementStatuses ?? []).filter(
    (requirementStatus) => requirementStatus.status !== "present"
  );
  const supportMatrix = {
    supported_profiles_by_forum: documentSupportMatrix?.supported_profiles_by_forum ?? {},
    unsupported_profile_families: documentSupportMatrix?.unsupported_profile_families ?? [],
  };
  const supportedProfiles = (
    supportMatrix.supported_profiles_by_forum[documentForum] ?? []
  ).map(formatIssueLabel);
  const unsupportedFamilies = supportMatrix.unsupported_profile_families.map(formatIssueLabel);
  const tocEntries = latestCompilation?.tocEntries ?? [];
  const ruleViolations = latestCompilation?.ruleViolations ?? [];
  const recordSections = latestCompilation?.recordSections ?? [];
  const paginationSummaryText = formatPaginationSummary(latestCompilation?.paginationSummary);
  const blockingRuleViolations = ruleViolations.filter(
    (violation) => toViolationSeverity(violation.severity) === "blocking"
  );
  const blockedReasons = buildBlockedReasons({
    missingRequiredItems: documentReadiness?.missingRequiredItems ?? [],
    blockingIssues: documentReadiness?.blockingIssues ?? [],
    unresolvedRequirementStatuses,
    blockingRuleViolations: blockingRuleViolations.map((violation) => ({
      code: violation.code,
      remediation: violation.remediation,
    })),
  });

  useEffect(() => {
    if (
      isDocumentIntakeSubmitting ||
      isDocumentReadinessSubmitting ||
      isDocumentPackageSubmitting ||
      isDocumentDownloadSubmitting
    ) {
      setActiveWorkflowMode("documents");
      return;
    }
    if (documentUploads.length > 0 || documentReadiness) {
      setActiveWorkflowMode("documents");
    }
  }, [
    documentReadiness,
    documentUploads.length,
    isDocumentDownloadSubmitting,
    isDocumentIntakeSubmitting,
    isDocumentPackageSubmitting,
    isDocumentReadinessSubmitting,
  ]);

  useEffect(() => {
    if (
      intakeProceduralPosture ||
      intakeIssueTags.trim() ||
      intakeAnchorReference.trim() ||
      intakeDateFrom ||
      intakeDateTo
    ) {
      setShowAdvancedIntake(true);
    }
  }, [
    intakeAnchorReference,
    intakeDateFrom,
    intakeDateTo,
    intakeIssueTags,
    intakeProceduralPosture,
  ]);

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

        <div
          className="mt-4 flex rounded-xl border border-[rgba(176,174,165,0.5)] bg-[rgba(247,243,234,0.7)] p-1"
          aria-label="Workflow mode"
          role="tablist"
        >
          <button
            id="workflow-research-tab"
            aria-controls="workflow-research-panel"
            aria-selected={activeWorkflowMode === "research"}
            className={`flex-1 rounded-lg px-3 py-2 text-[11px] font-semibold uppercase tracking-[0.1em] transition ${
              activeWorkflowMode === "research"
                ? "border border-[rgba(106,155,204,0.35)] bg-[#eef3f8] text-[#436280]"
                : "text-muted hover:bg-[rgba(235,232,223,0.8)]"
            }`}
            onClick={() => setActiveWorkflowMode("research")}
            role="tab"
            type="button"
          >
            Research
          </button>
          <button
            id="workflow-documents-tab"
            aria-controls="workflow-documents-panel"
            aria-selected={activeWorkflowMode === "documents"}
            className={`flex-1 rounded-lg px-3 py-2 text-[11px] font-semibold uppercase tracking-[0.1em] transition ${
              activeWorkflowMode === "documents"
                ? "border border-[rgba(106,155,204,0.35)] bg-[#eef3f8] text-[#436280]"
                : "text-muted hover:bg-[rgba(235,232,223,0.8)]"
            }`}
            onClick={() => setActiveWorkflowMode("documents")}
            role="tab"
            type="button"
          >
            Documents
          </button>
        </div>

        <div
          id="workflow-documents-panel"
          aria-labelledby="workflow-documents-tab"
          hidden={activeWorkflowMode !== "documents"}
          role="tabpanel"
        >
          <div className="mt-4 rounded-xl border border-[var(--imm-border-soft)] bg-[var(--imm-surface-warm)] p-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-muted">
              Document intake
            </p>
            {documentReadiness ? (
              <span
                className={`inline-flex rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.08em] ${
                  documentReadiness.isReady
                    ? "border-[#b8c6a6] bg-[#eef2e7] text-[#5f7248]"
                    : "border-[rgba(217,119,87,0.35)] bg-[#f8eee8] text-warning"
                }`}
              >
                {documentReadiness.isReady ? "Ready" : "Not ready"}
              </span>
            ) : null}
          </div>
          <p className="mt-1 text-[11px] leading-5 text-muted">
            Upload filings, review quality flags, and confirm readiness before generating a package.
          </p>

          <div className="mt-2 grid gap-2 sm:grid-cols-2">
            <label className="text-[11px] text-muted">
              Document forum
              <select
                aria-label="Document forum"
                className="mt-1 min-h-[38px] w-full rounded-md border border-[rgba(176,174,165,0.72)] bg-white px-2 text-xs text-ink"
                disabled={disableDocumentControls}
                onChange={(event) => onDocumentForumChange(event.target.value as typeof documentForum)}
                value={documentForum}
              >
                <option value="federal_court_jr">Federal Court JR</option>
                <option value="rpd">IRB RPD</option>
                <option value="rad">IRB RAD</option>
                <option value="iad">IRB IAD</option>
                <option value="id">IRB ID</option>
                <option value="ircc_application">IRCC Application (PR card renewal)</option>
              </select>
            </label>
            <label className="text-[11px] text-muted">
              Matter ID (optional)
              <input
                aria-label="Matter ID (optional)"
                className="mt-1 min-h-[38px] w-full rounded-md border border-[rgba(176,174,165,0.72)] bg-white px-2 text-xs text-ink"
                disabled={disableDocumentControls}
                onChange={(event) => onDocumentMatterIdChange(event.target.value)}
                placeholder="matter-abc123"
                type="text"
                value={documentMatterId}
              />
            </label>
          </div>
          <p className="mt-2 text-[10px] leading-4 text-muted">
            Supported profiles for {formatIssueLabel(documentForum)}:{" "}
            {supportedProfiles.length ? supportedProfiles.join(", ") : "none"}.
            Unsupported profile families: {unsupportedFamilies.length ? unsupportedFamilies.join(", ") : "none"}.
          </p>

          <div
            aria-describedby={documentDropzoneHintId}
            className={`mt-3 rounded-lg border border-dashed px-3 py-3 transition ${
              isDocumentDropActive
                ? "border-[rgba(106,155,204,0.8)] bg-[#eef3f8]"
                : "border-[rgba(176,174,165,0.6)] bg-[rgba(247,243,234,0.72)]"
            }`}
            onDragEnter={(event) => {
              event.preventDefault();
              if (disableDocumentControls) {
                return;
              }
              setIsDocumentDropActive(true);
            }}
            onDragLeave={(event) => {
              event.preventDefault();
              setIsDocumentDropActive(false);
            }}
            onDragOver={(event) => {
              event.preventDefault();
              if (!disableDocumentControls) {
                setIsDocumentDropActive(true);
              }
            }}
            onDrop={(event) => {
              event.preventDefault();
              setIsDocumentDropActive(false);
              if (disableDocumentControls) {
                return;
              }
              const droppedFiles = Array.from(event.dataTransfer.files ?? []);
              if (droppedFiles.length > 0) {
                onDocumentUpload(droppedFiles);
              }
            }}
          >
            <div className="flex flex-wrap items-center gap-2">
              <label
                className={`imm-btn-secondary cursor-pointer px-2.5 py-1 text-[11px] ${
                  disableDocumentControls ? "pointer-events-none opacity-60" : ""
                }`}
                htmlFor={documentUploadInputId}
              >
                {isDocumentIntakeSubmitting ? "Uploading..." : "Choose files"}
              </label>
              <input
                aria-label="Upload documents"
                className="sr-only"
                disabled={disableDocumentControls}
                id={documentUploadInputId}
                multiple
                onChange={(event) => {
                  const selectedFiles = Array.from(event.currentTarget.files ?? []);
                  if (selectedFiles.length > 0) {
                    onDocumentUpload(selectedFiles);
                  }
                  event.currentTarget.value = "";
                }}
                type="file"
              />
              <p className="text-[11px] leading-5 text-muted">Or drag and drop files here.</p>
            </div>
            <p className="mt-2 text-[10px] uppercase tracking-[0.12em] text-muted" id={documentDropzoneHintId}>
              PDF and image files supported
            </p>
          </div>

          <div className="mt-3 flex flex-wrap items-center gap-2">
            <button
              className="imm-btn-secondary px-2.5 py-1 text-[11px]"
              disabled={!hasMatterId || disableDocumentControls}
              onClick={onRefreshDocumentReadiness}
              type="button"
            >
              {isDocumentReadinessSubmitting ? "Refreshing..." : "Refresh readiness"}
            </button>
            <button
              className="imm-btn-secondary px-2.5 py-1 text-[11px]"
              disabled={disableGeneratePackage}
              onClick={onBuildDocumentPackage}
              type="button"
            >
              {isDocumentPackageSubmitting ? "Generating..." : "Generate package"}
            </button>
            <button
              className="imm-btn-secondary px-2.5 py-1 text-[11px]"
              title={metadataOnlyDownloadHint ?? undefined}
              disabled={disableDownloadPackage}
              onClick={onDownloadDocumentPackage}
              type="button"
            >
              {isDocumentDownloadSubmitting ? "Downloading..." : "Download binder PDF"}
            </button>
          </div>
          {metadataOnlyDownloadHint ? (
            <p className="mt-1 text-[10px] text-muted">{metadataOnlyDownloadHint}</p>
          ) : null}

          <div aria-live="polite" className="mt-2 min-h-[20px]" role="status">
            <p className="text-xs leading-5 text-muted">{documentStatusMessage}</p>
          </div>

          <div className="mt-2 rounded-lg border border-[rgba(176,174,165,0.45)] bg-[rgba(250,249,245,0.96)] px-3 py-2 text-[11px] leading-5 text-muted">
            <p className="font-semibold text-ink">Matter ID: {documentMatterId.trim() || "Not assigned"}</p>
            <p className="mt-1">
              Ready for filing package:{" "}
              <span className="font-semibold text-ink">
                {documentReadiness ? (documentReadiness.isReady ? "Ready" : "Not ready") : "Unknown"}
              </span>
            </p>
            {documentReadiness?.missingRequiredItems.length ? (
              <p className="mt-1">
                Missing: {documentReadiness.missingRequiredItems.map(formatIssueLabel).join(", ")}
              </p>
            ) : null}
            {documentReadiness?.blockingIssues.length ? (
              <p className="mt-1">
                Blocking: {documentReadiness.blockingIssues.map(formatIssueLabel).join(", ")}
              </p>
            ) : null}
            {documentReadiness?.warnings.length ? (
              <p className="mt-1">
                Warnings: {documentReadiness.warnings.map(formatIssueLabel).join(", ")}
              </p>
            ) : null}
            {latestCompilation?.compilationOutputMode === "compiled_pdf" &&
            latestCompilation.compiledArtifact ? (
              <p className="mt-1">
                Compiled binder: {latestCompilation.compiledArtifact.filename} (
                {latestCompilation.compiledArtifact.pageCount} pages)
              </p>
            ) : null}
            {latestCompilation?.compilationOutputMode === "metadata_plan_only" ? (
              <p className="mt-1">Compiled binder download is unavailable in metadata-only mode.</p>
            ) : null}
            {unresolvedRequirementStatuses.length ? (
              <div className="mt-2 rounded-md border border-[rgba(176,174,165,0.35)] bg-[rgba(247,243,234,0.64)] px-2 py-1.5">
                <p className="text-[10px] uppercase tracking-[0.1em] text-muted">Rule guidance</p>
                <ul className="mt-1 space-y-1">
                  {unresolvedRequirementStatuses.slice(0, 4).map((requirementStatus) => (
                    <li key={`${requirementStatus.item}-${requirementStatus.status}`}>
                      <span className="font-semibold text-ink">
                        {formatIssueLabel(requirementStatus.item)} ({formatRuleScope(requirementStatus.ruleScope)})
                      </span>
                      {requirementStatus.reason ? `: ${requirementStatus.reason}` : ""}
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}
          </div>

          {ruleViolations.length ? (
            <div className="mt-2 rounded-lg border border-[rgba(176,174,165,0.45)] bg-[rgba(250,249,245,0.96)] px-3 py-2 text-[11px] leading-5 text-muted">
              <p className="text-[10px] uppercase tracking-[0.1em] text-muted">Rule violations</p>
              <ul className="mt-2 space-y-2">
                {ruleViolations.map((violation) => {
                  const normalizedSeverity = toViolationSeverity(violation.severity);
                  return (
                    <li
                      className="rounded-md border border-[rgba(176,174,165,0.35)] bg-[rgba(247,243,234,0.64)] px-2 py-1.5"
                      key={`${violation.severity}-${violation.code}`}
                    >
                      <div className="flex flex-wrap items-center gap-2">
                        <span
                          className={`inline-flex rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.08em] ${violationSeverityTone(normalizedSeverity)}`}
                        >
                          {normalizedSeverity}
                        </span>
                        <span className="font-semibold text-ink">{violation.code}</span>
                      </div>
                      {violation.sourceUrl ? (
                        <a
                          className="mt-1 inline-block underline-offset-2 hover:underline"
                          href={violation.sourceUrl}
                          rel="noreferrer"
                          target="_blank"
                        >
                          Source reference: {violation.code}
                        </a>
                      ) : null}
                      {violation.remediation ? (
                        <p className="mt-1">{violation.remediation}</p>
                      ) : null}
                    </li>
                  );
                })}
              </ul>
            </div>
          ) : null}

          {recordSections.length ? (
            <div className="mt-2 rounded-lg border border-[rgba(176,174,165,0.45)] bg-[rgba(250,249,245,0.96)] px-3 py-2 text-[11px] leading-5 text-muted">
              <p className="text-[10px] uppercase tracking-[0.1em] text-muted">
                Record section completeness
              </p>
              <ul className="mt-2 space-y-2">
                {recordSections.map((section) => {
                  const normalizedSectionStatus = toSectionStatus(section.sectionStatus);
                  return (
                    <li
                      className="rounded-md border border-[rgba(176,174,165,0.35)] bg-[rgba(247,243,234,0.64)] px-2 py-1.5"
                      key={section.sectionId}
                    >
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="font-semibold text-ink">{section.title}</span>
                        <span
                          className={`inline-flex rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.08em] ${sectionStatusTone(normalizedSectionStatus)}`}
                        >
                          {sectionStatusLabel(normalizedSectionStatus)}
                        </span>
                      </div>
                      {section.missingDocumentTypes.length ? (
                        <p className="mt-1">
                          Missing: {section.missingDocumentTypes.map(formatIssueLabel).join(", ")}
                        </p>
                      ) : null}
                      {section.missingReasons.length ? (
                        <ul className="mt-1 space-y-1">
                          {section.missingReasons.map((reason) => (
                            <li key={`${section.sectionId}-${reason}`}>{reason}</li>
                          ))}
                        </ul>
                      ) : null}
                    </li>
                  );
                })}
              </ul>
            </div>
          ) : null}

          {tocEntries.length ? (
            <div className="mt-2 rounded-lg border border-[rgba(176,174,165,0.45)] bg-[rgba(250,249,245,0.96)] px-3 py-2 text-[11px] leading-5 text-muted">
              <p className="text-[10px] uppercase tracking-[0.1em] text-muted">Compilation TOC</p>
              <ul className="mt-2 space-y-1">
                {tocEntries.map((entry) => (
                  <li key={`${entry.position}-${entry.filename}`}>
                    <span className="font-semibold text-ink">
                      {entry.position}. {entry.filename}
                    </span>{" "}
                    <span className="text-muted">
                      ({formatIssueLabel(entry.documentType)}) - {formatPageRange(entry.startPage, entry.endPage)}
                    </span>
                  </li>
                ))}
              </ul>
              {paginationSummaryText ? (
                <p className="mt-2">{paginationSummaryText}</p>
              ) : null}
              {latestCompilation?.compilationProfile ? (
                <p className="mt-1">
                  Compilation profile: {latestCompilation.compilationProfile.id} v
                  {latestCompilation.compilationProfile.version}
                </p>
              ) : null}
            </div>
          ) : null}

          {blockedReasons.length ? (
            <div className="mt-2 rounded-lg border border-[rgba(217,119,87,0.35)] bg-[#f8eee8] px-3 py-2 text-[11px] leading-5 text-warning">
              <p className="text-[10px] uppercase tracking-[0.1em] text-warning">Why blocked</p>
              <ul className="mt-2 space-y-1 text-muted">
                {blockedReasons.map((reason) => (
                  <li key={reason}>{reason}</li>
                ))}
              </ul>
            </div>
          ) : null}

          {documentUploads.length ? (
            <ul className="mt-2 space-y-2 text-[11px] leading-5 text-muted">
              {documentUploads.map((uploadItem) => {
                const uploadRemediationGuidance = Array.from(
                  new Set(
                    uploadItem.issueDetails
                      .map((issueDetail) => issueDetail.remediation?.trim() ?? "")
                      .filter(Boolean)
                  )
                );
                return (
                  <li
                    className="rounded-lg border border-[rgba(176,174,165,0.45)] bg-[rgba(250,249,245,0.96)] px-3 py-2"
                    key={`${uploadItem.fileId}-${uploadItem.filename}`}
                  >
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <p className="font-medium text-ink">{uploadItem.filename}</p>
                      <span
                        className={`inline-flex rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.08em] ${uploadStatusTone(uploadItem.status)}`}
                      >
                        {uploadStatusLabel(uploadItem.status)}
                      </span>
                    </div>
                    {uploadItem.classification ? (
                      <p className="mt-1 text-[10px] uppercase tracking-[0.1em] text-muted">
                        Type: {formatIssueLabel(uploadItem.classification)}
                      </p>
                    ) : null}
                    {uploadItem.issues.length ? (
                      <p className="mt-1">Issues: {uploadItem.issues.map(formatIssueLabel).join(", ")}</p>
                    ) : null}
                    {uploadRemediationGuidance.length ? (
                      <p className="mt-1">Next step: {uploadRemediationGuidance.join(" ")}</p>
                    ) : null}
                  </li>
                );
              })}
            </ul>
          ) : null}
          </div>
        </div>

        <div
          id="workflow-research-panel"
          aria-labelledby="workflow-research-tab"
          hidden={activeWorkflowMode !== "research"}
          role="tabpanel"
        >
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
            </div>
            <button
              aria-expanded={showAdvancedIntake}
              className="imm-btn-secondary mt-2 px-2.5 py-1 text-[11px]"
              disabled={disableCaseSearchControls}
              onClick={() => setShowAdvancedIntake((currentValue) => !currentValue)}
              type="button"
            >
              {showAdvancedIntake ? "Hide advanced filters" : "Show advanced filters"}
            </button>
            {showAdvancedIntake ? (
              <div className="mt-2 grid gap-2 sm:grid-cols-2">
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
            ) : null}
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

        {isCaseSearchSubmitting && submissionPhase === "cases" ? (
          <div aria-live="polite" className="mt-3 min-h-[20px]" role="status">
            <div className="flex animate-pulse flex-col gap-2.5 py-1">
              <div className="h-2.5 w-3/4 rounded-full bg-[rgba(176,174,165,0.25)]" />
              <div className="h-2.5 w-1/2 rounded-full bg-[rgba(176,174,165,0.25)]" />
              <span className="sr-only">Running grounded lawyer case research...</span>
            </div>
          </div>
        ) : null}

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
              const sourceBadgeLabel = formatSourceBadgeLabel(result.source_id);
              const sourceEventTypeLabel = formatSourceEventTypeLabel(result.source_event_type);
              const docketNumbers = normalizeDocketNumbers(result.docket_numbers);

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
                      {sourceBadgeLabel ? (
                        <span className="rounded-full border border-[rgba(176,174,165,0.45)] bg-[#ebe8df] px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-muted">
                          Source: {sourceBadgeLabel}
                        </span>
                      ) : null}
                      {sourceEventTypeLabel ? (
                        <span className="rounded-full border border-[rgba(106,155,204,0.35)] bg-[#eef3f8] px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-[#436280]">
                          Event: {sourceEventTypeLabel}
                        </span>
                      ) : null}
                      <span className="w-full text-[10px] uppercase tracking-[0.1em] text-muted sm:w-auto">
                        Decision date: {result.decision_date}
                      </span>
                    </div>

                    <p className="mt-2 rounded-lg border border-[rgba(176,174,165,0.4)] bg-[#f3f1ea] px-2.5 py-2 text-[11px] leading-5 text-muted">
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
                              className="rounded-full border border-[rgba(176,174,165,0.45)] bg-[rgba(247,243,234,0.72)] px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.06em] text-muted"
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
                        <p className="font-semibold uppercase tracking-wider text-[10px] mb-0.5">Summary</p>
                        <p className="line-clamp-4 hover:line-clamp-none transition-all">{result.summary}</p>
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
              className="w-full max-w-md rounded-xl border border-[rgba(176,174,165,0.75)] bg-[rgba(253,252,248,0.99)] p-4 shadow-[0_18px_48px_rgba(20,20,19,0.2)]"
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
              <p className="mt-2 rounded-lg border border-[rgba(176,174,165,0.45)] bg-[rgba(247,243,234,0.72)] px-3 py-2 text-xs font-semibold text-ink">
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
        </div>
      </div>
    </section>
  );
}
