import { useEffect, useMemo, useRef, useState } from "react";

import { RelatedCasePanelDocuments } from "@/components/chat/related-case-panel-documents";
import { RelatedCasePanelResearch } from "@/components/chat/related-case-panel-research";
import type { RelatedCasePanelProps } from "@/components/chat/types";
import { buildWorkflowStatusContract } from "@/components/chat/workflow-status-contract";
import { emitWorkflowMetric } from "@/lib/workflow-confusion-metrics";

type WorkflowMode = "research" | "documents";

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
  relatedCasesStatus,
  relatedCasesRetrievalMode,
  sourceStatus,
  prioritySourceStatus,
  onCaseSearchQueryChange,
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
  const [activeWorkflowMode, setActiveWorkflowMode] = useState<WorkflowMode>("research");
  const lastModeSwitchEpochRef = useRef<number | null>(null);
  const lastResearchWarningRef = useRef<string>("");
  const lastDocumentWarningRef = useRef<string>("");

  const workflowStatus = useMemo(
    () =>
      buildWorkflowStatusContract({
        relatedCasesStatus,
        documentStatusMessage,
        isCaseSearchSubmitting,
        isDocumentIntakeSubmitting,
        isDocumentReadinessSubmitting,
        isDocumentPackageSubmitting,
        isDocumentDownloadSubmitting,
      }),
    [
      documentStatusMessage,
      isCaseSearchSubmitting,
      isDocumentDownloadSubmitting,
      isDocumentIntakeSubmitting,
      isDocumentPackageSubmitting,
      isDocumentReadinessSubmitting,
      relatedCasesStatus,
    ]
  );
  const isDocumentSubmitting =
    isDocumentIntakeSubmitting ||
    isDocumentReadinessSubmitting ||
    isDocumentPackageSubmitting ||
    isDocumentDownloadSubmitting;

  const handleWorkflowModeChange = (nextMode: WorkflowMode): void => {
    if (nextMode === activeWorkflowMode) {
      return;
    }

    const now = Date.now();
    const elapsedSinceLastSwitchMs =
      lastModeSwitchEpochRef.current === null ? null : now - lastModeSwitchEpochRef.current;
    lastModeSwitchEpochRef.current = now;

    emitWorkflowMetric("workflow_mode_switch", {
      from_mode: activeWorkflowMode,
      to_mode: nextMode,
      elapsed_since_last_switch_ms: elapsedSinceLastSwitchMs,
      case_search_submitting: isCaseSearchSubmitting,
      document_submitting: isDocumentSubmitting,
    });

    if (typeof elapsedSinceLastSwitchMs === "number" && elapsedSinceLastSwitchMs <= 8000) {
      emitWorkflowMetric("workflow_switch_churn", {
        from_mode: activeWorkflowMode,
        to_mode: nextMode,
        elapsed_since_last_switch_ms: elapsedSinceLastSwitchMs,
      });
    }

    if (activeWorkflowMode === "research" && isCaseSearchSubmitting) {
      emitWorkflowMetric("workflow_abandonment", {
        mode: "research",
        reason: "switched_away_while_search_running",
      });
    }
    if (activeWorkflowMode === "documents" && isDocumentSubmitting) {
      emitWorkflowMetric("workflow_abandonment", {
        mode: "documents",
        reason: "switched_away_while_document_work_running",
      });
    }

    setActiveWorkflowMode(nextMode);
  };

  useEffect(() => {
    if (workflowStatus.research.tone !== "warning" || !workflowStatus.research.detail) {
      return;
    }
    if (workflowStatus.research.detail === lastResearchWarningRef.current) {
      return;
    }
    lastResearchWarningRef.current = workflowStatus.research.detail;
    emitWorkflowMetric("workflow_warning", {
      detail: workflowStatus.research.detail,
      mode: "research",
    });
  }, [workflowStatus.research.detail, workflowStatus.research.tone]);

  useEffect(() => {
    if (workflowStatus.documents.tone !== "warning" || !workflowStatus.documents.detail) {
      return;
    }
    if (workflowStatus.documents.detail === lastDocumentWarningRef.current) {
      return;
    }
    lastDocumentWarningRef.current = workflowStatus.documents.detail;
    emitWorkflowMetric("workflow_warning", {
      detail: workflowStatus.documents.detail,
      mode: "documents",
    });
  }, [workflowStatus.documents.detail, workflowStatus.documents.tone]);

  const handleResearchSearch = (): void => {
    const normalizedCurrentQuery = caseSearchQuery.trim().toLowerCase();
    const normalizedLastSearchQuery = (lastCaseSearchQuery ?? "").trim().toLowerCase();
    const normalizedResearchStatus = relatedCasesStatus.toLowerCase();

    if (
      normalizedCurrentQuery &&
      normalizedCurrentQuery === normalizedLastSearchQuery &&
      (normalizedResearchStatus.includes("failed") ||
        normalizedResearchStatus.includes("unavailable") ||
        normalizedResearchStatus.includes("error"))
    ) {
      emitWorkflowMetric("research_retry_after_failure", {
        query: caseSearchQuery.trim(),
        related_cases_status: relatedCasesStatus,
      });
    }
    onSearch();
  };

  return (
    <section
      className="imm-paper-card imm-fade-up rounded-2xl p-4 md:p-5"
      style={{ animationDelay: "200ms" }}
    >
      <div className="relative z-10">
        <div className="flex flex-wrap items-start justify-between gap-3 border-b border-[var(--imm-border-soft)] pb-3">
          <div>
            <h2 className="text-lg font-semibold text-ink">Research & document workflows</h2>
            <p className="mt-1 max-w-md text-xs leading-6 text-muted">
              Conversation answers appear in the main thread. Use this panel for case-law research and document tasks.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <span className="imm-pill imm-pill-neutral text-[10px]">Workflow tools</span>
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
          aria-label="Workflow mode"
          className="mt-4 flex rounded-xl border border-[var(--imm-border-soft)] bg-[var(--imm-surface-warm)] p-1"
          role="tablist"
        >
          <button
            id="workflow-research-tab"
            aria-controls="workflow-research-panel"
            aria-label="Research"
            aria-selected={activeWorkflowMode === "research"}
            className={`flex-1 rounded-lg px-3 py-2 text-[11px] font-semibold uppercase tracking-[0.1em] transition ${
              activeWorkflowMode === "research"
                ? "border border-[rgba(95,132,171,0.35)] bg-[var(--imm-accent-soft)] text-[var(--imm-accent-ink)]"
                : "text-muted hover:bg-[rgba(228,221,208,0.88)]"
            }`}
            onClick={() => handleWorkflowModeChange("research")}
            role="tab"
            type="button"
          >
            <span>Research</span>
            <span
              className={`ml-1 hidden rounded-full border px-1.5 py-0.5 text-[9px] font-semibold tracking-[0.08em] sm:inline-flex ${
                workflowStatus.research.tone === "warning"
                  ? "border-[rgba(172,63,47,0.22)] bg-[var(--imm-danger-soft)] text-[var(--imm-danger-ink)]"
                  : workflowStatus.research.tone === "success"
                    ? "border-[rgba(111,132,89,0.35)] bg-[var(--imm-success-soft)] text-[var(--imm-success-ink)]"
                    : "border-[rgba(95,132,171,0.35)] bg-[var(--imm-accent-soft)] text-[var(--imm-accent-ink)]"
              }`}
            >
              {workflowStatus.research.label}
            </span>
          </button>
          <button
            id="workflow-documents-tab"
            aria-controls="workflow-documents-panel"
            aria-label="Documents"
            aria-selected={activeWorkflowMode === "documents"}
            className={`flex-1 rounded-lg px-3 py-2 text-[11px] font-semibold uppercase tracking-[0.1em] transition ${
              activeWorkflowMode === "documents"
                ? "border border-[rgba(95,132,171,0.35)] bg-[var(--imm-accent-soft)] text-[var(--imm-accent-ink)]"
                : "text-muted hover:bg-[rgba(228,221,208,0.88)]"
            }`}
            onClick={() => handleWorkflowModeChange("documents")}
            role="tab"
            type="button"
          >
            <span>Documents</span>
            <span
              className={`ml-1 hidden rounded-full border px-1.5 py-0.5 text-[9px] font-semibold tracking-[0.08em] sm:inline-flex ${
                workflowStatus.documents.tone === "warning"
                  ? "border-[rgba(172,63,47,0.22)] bg-[var(--imm-danger-soft)] text-[var(--imm-danger-ink)]"
                  : workflowStatus.documents.tone === "success"
                    ? "border-[rgba(111,132,89,0.35)] bg-[var(--imm-success-soft)] text-[var(--imm-success-ink)]"
                    : "border-[rgba(95,132,171,0.35)] bg-[var(--imm-accent-soft)] text-[var(--imm-accent-ink)]"
              }`}
            >
              {workflowStatus.documents.label}
            </span>
          </button>
        </div>

        <div
          id="workflow-documents-panel"
          aria-labelledby="workflow-documents-tab"
          hidden={activeWorkflowMode !== "documents"}
          role="tabpanel"
        >
          <RelatedCasePanelDocuments
            documentForum={documentForum}
            documentMatterId={documentMatterId}
            documentStatusMessage={documentStatusMessage}
            documentUploads={documentUploads}
            documentReadiness={documentReadiness}
            isDocumentIntakeSubmitting={isDocumentIntakeSubmitting}
            isDocumentReadinessSubmitting={isDocumentReadinessSubmitting}
            isDocumentPackageSubmitting={isDocumentPackageSubmitting}
            isDocumentDownloadSubmitting={isDocumentDownloadSubmitting}
            onDocumentForumChange={onDocumentForumChange}
            onDocumentMatterIdChange={onDocumentMatterIdChange}
            onDocumentUpload={onDocumentUpload}
            onRefreshDocumentReadiness={onRefreshDocumentReadiness}
            onBuildDocumentPackage={onBuildDocumentPackage}
            onDownloadDocumentPackage={onDownloadDocumentPackage}
            documentSupportMatrix={documentSupportMatrix}
          />
        </div>

        <div
          id="workflow-research-panel"
          aria-labelledby="workflow-research-tab"
          hidden={activeWorkflowMode !== "research"}
          role="tabpanel"
        >
          <RelatedCasePanelResearch
            isChatSubmitting={isChatSubmitting}
            isCaseSearchSubmitting={isCaseSearchSubmitting}
            isExportSubmitting={isExportSubmitting}
            submissionPhase={submissionPhase}
            caseSearchQuery={caseSearchQuery}
            lastCaseSearchQuery={lastCaseSearchQuery}
            relatedCasesRetrievalMode={relatedCasesRetrievalMode}
            sourceStatus={sourceStatus}
            prioritySourceStatus={prioritySourceStatus}
            onCaseSearchQueryChange={onCaseSearchQueryChange}
            researchConfidence={researchConfidence}
            confidenceReasons={confidenceReasons}
            intakeCompleteness={intakeCompleteness}
            intakeHints={intakeHints}
            relatedCases={relatedCases}
            matterProfile={matterProfile}
            intakeObjective={intakeObjective}
            intakeTargetCourt={intakeTargetCourt}
            intakeProceduralPosture={intakeProceduralPosture}
            intakeIssueTags={intakeIssueTags}
            intakeAnchorReference={intakeAnchorReference}
            intakeDateFrom={intakeDateFrom}
            intakeDateTo={intakeDateTo}
            onIntakeObjectiveChange={onIntakeObjectiveChange}
            onIntakeTargetCourtChange={onIntakeTargetCourtChange}
            onIntakeProceduralPostureChange={onIntakeProceduralPostureChange}
            onIntakeIssueTagsChange={onIntakeIssueTagsChange}
            onIntakeAnchorReferenceChange={onIntakeAnchorReferenceChange}
            onIntakeDateFromChange={onIntakeDateFromChange}
            onIntakeDateToChange={onIntakeDateToChange}
            onSearch={handleResearchSearch}
            onExportCase={onExportCase}
            exportingCaseId={exportingCaseId}
          />
        </div>
      </div>
    </section>
  );
}
