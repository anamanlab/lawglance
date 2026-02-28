import { useState } from "react";

import type { RelatedCasePanelProps } from "@/components/chat/types";
import {
  buildBlockedReasons,
  formatIssueLabel,
  formatPageRange,
  formatPaginationSummary,
  formatRuleScope,
  sectionStatusLabel,
  sectionStatusTone,
  toSectionStatus,
  toViolationSeverity,
  uploadStatusLabel,
  uploadStatusTone,
  violationSeverityTone,
} from "@/components/chat/related-case-panel-utils";

type DocumentsWorkflowPanelProps = Pick<
  RelatedCasePanelProps,
  | "documentForum"
  | "documentMatterId"
  | "documentStatusMessage"
  | "documentUploads"
  | "documentReadiness"
  | "isDocumentIntakeSubmitting"
  | "isDocumentReadinessSubmitting"
  | "isDocumentPackageSubmitting"
  | "isDocumentDownloadSubmitting"
  | "onDocumentForumChange"
  | "onDocumentMatterIdChange"
  | "onDocumentUpload"
  | "onRefreshDocumentReadiness"
  | "onBuildDocumentPackage"
  | "onDownloadDocumentPackage"
  | "documentSupportMatrix"
>;

export function RelatedCasePanelDocuments({
  documentForum,
  documentMatterId,
  documentStatusMessage,
  documentUploads,
  documentReadiness,
  isDocumentIntakeSubmitting,
  isDocumentReadinessSubmitting,
  isDocumentPackageSubmitting,
  isDocumentDownloadSubmitting,
  onDocumentForumChange,
  onDocumentMatterIdChange,
  onDocumentUpload,
  onRefreshDocumentReadiness,
  onBuildDocumentPackage,
  onDownloadDocumentPackage,
  documentSupportMatrix,
}: DocumentsWorkflowPanelProps): JSX.Element {
  const documentUploadInputId = "document-intake-upload";
  const documentDropzoneHintId = "document-intake-dropzone-hint";
  const hasMatterId = documentMatterId.trim().length > 0;
  const [isDocumentDropActive, setIsDocumentDropActive] = useState(false);
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

  return (
    <div className="mt-4 rounded-xl border border-[var(--imm-border-soft)] bg-[var(--imm-surface-warm)] p-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-muted">
          Document intake
        </p>
        {documentReadiness ? (
          <span
            className={`inline-flex rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.08em] ${
              documentReadiness.isReady
                ? "border-[rgba(111,132,89,0.35)] bg-[var(--imm-success-soft)] text-[var(--imm-success-ink)]"
                : "border-[rgba(192,106,77,0.35)] bg-[var(--imm-primary-soft)] text-warning"
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
            className="mt-1 min-h-[38px] w-full rounded-md border border-[var(--imm-border-soft)] bg-[var(--imm-surface)] px-2 text-xs text-ink"
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
            className="mt-1 min-h-[38px] w-full rounded-md border border-[var(--imm-border-soft)] bg-[var(--imm-surface)] px-2 text-xs text-ink"
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
        Unsupported profile families:{" "}
        {unsupportedFamilies.length ? unsupportedFamilies.join(", ") : "none"}.
      </p>

      <div
        aria-describedby={documentDropzoneHintId}
        className={`mt-3 rounded-lg border border-dashed px-3 py-3 transition ${
          isDocumentDropActive
            ? "border-[rgba(95,132,171,0.7)] bg-[var(--imm-accent-soft)]"
            : "border-[var(--imm-border-soft)] bg-[var(--imm-surface-warm)]"
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

      <div className="mt-2 rounded-lg border border-[var(--imm-border-soft)] bg-[var(--imm-surface-soft)] px-3 py-2 text-[11px] leading-5 text-muted">
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
          <div className="mt-2 rounded-md border border-[rgba(159,154,142,0.42)] bg-[rgba(236,229,215,0.78)] px-2 py-1.5">
            <p className="text-[10px] uppercase tracking-[0.1em] text-muted">Rule guidance</p>
            <ul className="mt-1 space-y-1">
              {unresolvedRequirementStatuses.slice(0, 4).map((requirementStatus) => (
                <li key={`${requirementStatus.item}-${requirementStatus.status}`}>
                  <span className="font-semibold text-ink">
                    {formatIssueLabel(requirementStatus.item)} (
                    {formatRuleScope(requirementStatus.ruleScope)})
                  </span>
                  {requirementStatus.reason ? `: ${requirementStatus.reason}` : ""}
                </li>
              ))}
            </ul>
          </div>
        ) : null}
      </div>

      {ruleViolations.length ? (
        <div className="mt-2 rounded-lg border border-[var(--imm-border-soft)] bg-[var(--imm-surface-soft)] px-3 py-2 text-[11px] leading-5 text-muted">
          <p className="text-[10px] uppercase tracking-[0.1em] text-muted">Rule violations</p>
          <ul className="mt-2 space-y-2">
            {ruleViolations.map((violation) => {
              const normalizedSeverity = toViolationSeverity(violation.severity);
              return (
                <li
                  className="rounded-md border border-[rgba(159,154,142,0.42)] bg-[rgba(236,229,215,0.78)] px-2 py-1.5"
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
                  {violation.remediation ? <p className="mt-1">{violation.remediation}</p> : null}
                </li>
              );
            })}
          </ul>
        </div>
      ) : null}

      {recordSections.length ? (
        <div className="mt-2 rounded-lg border border-[var(--imm-border-soft)] bg-[var(--imm-surface-soft)] px-3 py-2 text-[11px] leading-5 text-muted">
          <p className="text-[10px] uppercase tracking-[0.1em] text-muted">
            Record section completeness
          </p>
          <ul className="mt-2 space-y-2">
            {recordSections.map((section) => {
              const normalizedSectionStatus = toSectionStatus(section.sectionStatus);
              return (
                <li
                  className="rounded-md border border-[rgba(159,154,142,0.42)] bg-[rgba(236,229,215,0.78)] px-2 py-1.5"
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
        <div className="mt-2 rounded-lg border border-[var(--imm-border-soft)] bg-[var(--imm-surface-soft)] px-3 py-2 text-[11px] leading-5 text-muted">
          <p className="text-[10px] uppercase tracking-[0.1em] text-muted">Compilation TOC</p>
          <ul className="mt-2 space-y-1">
            {tocEntries.map((entry) => (
              <li key={`${entry.position}-${entry.filename}`}>
                <span className="font-semibold text-ink">
                  {entry.position}. {entry.filename}
                </span>{" "}
                <span className="text-muted">
                  ({formatIssueLabel(entry.documentType)}) -{" "}
                  {formatPageRange(entry.startPage, entry.endPage)}
                </span>
              </li>
            ))}
          </ul>
          {paginationSummaryText ? <p className="mt-2">{paginationSummaryText}</p> : null}
          {latestCompilation?.compilationProfile ? (
            <p className="mt-1">
              Compilation profile: {latestCompilation.compilationProfile.id} v
              {latestCompilation.compilationProfile.version}
            </p>
          ) : null}
        </div>
      ) : null}

      {blockedReasons.length ? (
        <div className="mt-2 rounded-lg border border-[rgba(192,106,77,0.35)] bg-[var(--imm-primary-soft)] px-3 py-2 text-[11px] leading-5 text-warning">
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
                className="rounded-lg border border-[var(--imm-border-soft)] bg-[var(--imm-surface-soft)] px-3 py-2"
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
  );
}

