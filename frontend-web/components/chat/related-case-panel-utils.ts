import type {
  DocumentCompilationPaginationSummary,
  PrioritySourceStatusMap,
} from "@/components/chat/types";

export const LOW_SPECIFICITY_HINT =
  "Query may be too broad. Add at least two anchors: program/issue and court or citation.";

export const DEFAULT_QUERY_HINT =
  "Tip: use program names, legal issues, court names, or citations for stronger case matches.";

const PRIORITY_SOURCE_DISPLAY_ORDER = [
  { sourceId: "SCC_DECISIONS", label: "SCC" },
  { sourceId: "FC_DECISIONS", label: "FC" },
];

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

export function formatSourceBadgeLabel(sourceId?: string | null): string | null {
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

export function formatSourceEventTypeLabel(value?: string | null): string | null {
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

export function normalizeDocketNumbers(docketNumbers?: string[] | null): string[] {
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

export function buildRefinementSuggestions(params: {
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

export function formatPrioritySourceStatus(statuses?: PrioritySourceStatusMap | null): string {
  if (!statuses) {
    return "Priority courts: n/a";
  }
  const parts = PRIORITY_SOURCE_DISPLAY_ORDER.map(({ sourceId, label }) => {
    const status = statuses[sourceId] ?? "missing";
    return `${label}: ${status}`;
  });
  return `Priority courts: ${parts.join(" | ")}`;
}

export function buildExportUnavailableReason(policyReason?: string | null): string {
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

export function buildPdfUnavailableReason(pdfReason?: string | null): string {
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

export function confidenceToneClass(confidence: "low" | "medium" | "high"): string {
  if (confidence === "high") {
    return "border-[rgba(111,132,89,0.35)] bg-[var(--imm-success-soft)] text-[var(--imm-success-ink)]";
  }
  if (confidence === "medium") {
    return "border-[rgba(95,132,171,0.35)] bg-[var(--imm-accent-soft)] text-[var(--imm-accent-ink)]";
  }
  return "border-[rgba(192,106,77,0.35)] bg-[var(--imm-primary-soft)] text-warning";
}

export function intakeToneClass(completeness: "low" | "medium" | "high"): string {
  if (completeness === "high") {
    return "border-[rgba(111,132,89,0.35)] bg-[var(--imm-success-soft)] text-[var(--imm-success-ink)]";
  }
  if (completeness === "medium") {
    return "border-[rgba(95,132,171,0.35)] bg-[var(--imm-accent-soft)] text-[var(--imm-accent-ink)]";
  }
  return "border-[rgba(192,106,77,0.35)] bg-[var(--imm-primary-soft)] text-warning";
}

export function toOfficialSourceStatusLabel(status: string): string {
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

export function toCanliiSourceStatusLabel(status: string): string {
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

export function formatIssueLabel(value: string): string {
  return value.replace(/_/g, " ");
}

export function formatRuleScope(value: "base" | "conditional"): string {
  return value === "conditional" ? "Conditional rule" : "Base rule";
}

export function uploadStatusLabel(status: "pending" | "uploaded" | "needs_review" | "failed"): string {
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

export function uploadStatusTone(status: "pending" | "uploaded" | "needs_review" | "failed"): string {
  if (status === "pending") {
    return "border-[rgba(95,132,171,0.35)] bg-[var(--imm-accent-soft)] text-[var(--imm-accent-ink)]";
  }
  if (status === "needs_review") {
    return "border-[rgba(192,106,77,0.35)] bg-[var(--imm-primary-soft)] text-warning";
  }
  if (status === "failed") {
    return "border-[rgba(172,63,47,0.22)] bg-[var(--imm-danger-soft)] text-[var(--imm-danger-ink)]";
  }
  return "border-[rgba(111,132,89,0.35)] bg-[var(--imm-success-soft)] text-[var(--imm-success-ink)]";
}

export function toViolationSeverity(value: string): "blocking" | "warning" {
  return value.trim().toLowerCase() === "blocking" ? "blocking" : "warning";
}

export function toSectionStatus(value: string): "present" | "missing" | "warning" {
  const normalizedValue = value.trim().toLowerCase();
  if (normalizedValue === "missing") {
    return "missing";
  }
  if (normalizedValue === "warning") {
    return "warning";
  }
  return "present";
}

export function sectionStatusTone(value: "present" | "missing" | "warning"): string {
  if (value === "missing") {
    return "border-[rgba(172,63,47,0.22)] bg-[var(--imm-danger-soft)] text-[var(--imm-danger-ink)]";
  }
  if (value === "warning") {
    return "border-[rgba(192,106,77,0.35)] bg-[var(--imm-primary-soft)] text-warning";
  }
  return "border-[rgba(111,132,89,0.35)] bg-[var(--imm-success-soft)] text-[var(--imm-success-ink)]";
}

export function sectionStatusLabel(value: "present" | "missing" | "warning"): string {
  if (value === "missing") {
    return "Missing";
  }
  if (value === "warning") {
    return "Warning";
  }
  return "Complete";
}

export function violationSeverityTone(value: "blocking" | "warning"): string {
  if (value === "blocking") {
    return "border-[rgba(172,63,47,0.22)] bg-[var(--imm-danger-soft)] text-[var(--imm-danger-ink)]";
  }
  return "border-[rgba(192,106,77,0.35)] bg-[var(--imm-primary-soft)] text-warning";
}

export function formatPageRange(startPage: number | null, endPage: number | null): string {
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

export function formatPaginationSummary(
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

export function buildBlockedReasons(params: {
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

