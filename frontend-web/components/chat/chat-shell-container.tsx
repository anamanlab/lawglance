"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { ChatHeader } from "@/components/chat/chat-header";
import {
  DOCUMENT_UPLOAD_DEFAULT_STATUS,
  MAX_MESSAGE_LENGTH,
} from "@/components/chat/constants";
import { MessageComposer } from "@/components/chat/message-composer";
import { MessageList } from "@/components/chat/message-list";
import { RelatedCasePanel } from "@/components/chat/related-case-panel";
import { StatusBanner } from "@/components/chat/status-banner";
import { SupportContextPanel } from "@/components/chat/support-context-panel";
import type { ChatShellProps } from "@/components/chat/types";
import { buildStatusTone } from "@/components/chat/utils";
import { useChatLogic } from "@/components/chat/use-chat-logic";

export function ChatShell({
  apiBaseUrl,
  legalDisclaimer,
  showOperationalPanels = false,
  enableAgentThinkingTimeline,
}: ChatShellProps): JSX.Element {
  const {
    textareaRef,
    endOfThreadRef,
    draft,
    setDraft,
    activeLocale,
    isChatSubmitting,
    isCaseSearchSubmitting,
    isExportSubmitting,
    chatError,
    retryPrompt,
    supportContext,
    relatedCases,
    matterProfile,
    relatedCasesStatus,
    caseSearchQuery,
    lastCaseSearchQuery,
    relatedCasesRetrievalMode,
    sourceStatus,
    researchConfidence,
    confidenceReasons,
    intakeCompleteness,
    intakeHints,
    intakeObjective,
    intakeTargetCourt,
    intakeProceduralPosture,
    intakeIssueTags,
    intakeAnchorReference,
    intakeDateFrom,
    intakeDateTo,
    documentForum,
    documentMatterId,
    documentStatusMessage,
    documentUploads,
    documentReadiness,
    isDocumentIntakeSubmitting,
    isDocumentReadinessSubmitting,
    isDocumentPackageSubmitting,
    isDocumentDownloadSubmitting,
    exportingCaseId,
    submissionPhase,
    chatPendingElapsedSeconds,
    isSlowChatResponse,
    activityByTurn,
    activeActivityTurnId,
    messages,
    runRelatedCaseSearch,
    runCaseExport,
    onSubmit,
    onRetryLastRequest,
    onQuickPromptClick,
    onCaseSearchQueryChange,
    onIntakeObjectiveChange,
    onIntakeTargetCourtChange,
    onIntakeProceduralPostureChange,
    onIntakeIssueTagsChange,
    onIntakeAnchorReferenceChange,
    onIntakeDateFromChange,
    onIntakeDateToChange,
    onDocumentForumChange,
    onDocumentMatterIdChange,
    onLocaleChange,
    onDocumentUpload,
    onRefreshDocumentReadiness,
    onBuildDocumentPackage,
    onDownloadDocumentPackage,
    documentSupportMatrix,
  } = useChatLogic({ apiBaseUrl, legalDisclaimer, showOperationalPanels });

  const [isMobileDrawerOpen, setIsMobileDrawerOpen] = useState(false);
  const mobileDrawerRef = useRef<HTMLElement | null>(null);
  const previousFocusedElementRef = useRef<HTMLElement | null>(null);

  const closeMobileDrawer = useCallback(() => {
    setIsMobileDrawerOpen(false);
  }, []);

  const openMobileDrawer = useCallback(() => {
    previousFocusedElementRef.current =
      document.activeElement instanceof HTMLElement ? document.activeElement : null;
    setIsMobileDrawerOpen(true);
  }, []);

  useEffect(() => {
    if (!isMobileDrawerOpen || !mobileDrawerRef.current) {
      return;
    }

    const focusableSelector =
      'a[href], button:not([disabled]), textarea:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])';
    const getFocusableElements = (): HTMLElement[] =>
      Array.from(
        mobileDrawerRef.current?.querySelectorAll<HTMLElement>(focusableSelector) ?? []
      );
    const focusableElements = getFocusableElements();
    const firstFocusableElement = focusableElements[0] ?? mobileDrawerRef.current;
    const lastFocusableElement =
      focusableElements[focusableElements.length - 1] ?? mobileDrawerRef.current;

    const focusTimer = window.setTimeout(() => {
      firstFocusableElement.focus();
    }, 0);

    const handleKeyDown = (event: KeyboardEvent): void => {
      if (event.key === "Escape") {
        event.preventDefault();
        closeMobileDrawer();
        return;
      }

      if (event.key !== "Tab" || !mobileDrawerRef.current) {
        return;
      }

      const activeElement =
        document.activeElement instanceof HTMLElement ? document.activeElement : null;
      const containsActiveElement =
        activeElement !== null && mobileDrawerRef.current.contains(activeElement);

      if (event.shiftKey) {
        if (!containsActiveElement || activeElement === firstFocusableElement) {
          event.preventDefault();
          lastFocusableElement.focus();
        }
        return;
      }

      if (!containsActiveElement || activeElement === lastFocusableElement) {
        event.preventDefault();
        firstFocusableElement.focus();
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => {
      window.clearTimeout(focusTimer);
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [closeMobileDrawer, isMobileDrawerOpen]);

  useEffect(() => {
    if (isMobileDrawerOpen) {
      return;
    }
    if (previousFocusedElementRef.current) {
      previousFocusedElementRef.current.focus();
      previousFocusedElementRef.current = null;
    }
  }, [isMobileDrawerOpen]);

  useEffect(() => {
    if (isMobileDrawerOpen) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "";
    }
    return () => {
      document.body.style.overflow = "";
    };
  }, [isMobileDrawerOpen]);

  const trimmedDraft = draft.trim();
  const sendDisabled = isChatSubmitting || !trimmedDraft;
  const remainingCharacters = MAX_MESSAGE_LENGTH - draft.length;

  const statusToneClass = useMemo(
    () => buildStatusTone(supportContext?.status ?? null),
    [supportContext]
  );
  const workflowStatus = useMemo(() => {
    const caseStatusMessage = relatedCasesStatus.trim();
    const documentStatus = documentStatusMessage.trim();
    const isDefaultDocumentStatus =
      documentStatus === DOCUMENT_UPLOAD_DEFAULT_STATUS;

    if (caseStatusMessage) {
      const normalizedMessage = caseStatusMessage.toLowerCase();
      const caseTone =
        normalizedMessage.includes("unavailable") ||
        normalizedMessage.includes("failed") ||
        normalizedMessage.includes("blocked") ||
        normalizedMessage.includes("invalid") ||
        normalizedMessage.includes("too broad")
          ? "warning"
          : normalizedMessage.includes("download started") ||
            normalizedMessage.includes("ready")
            ? "success"
            : "info";
      return {
        title: "Case-law workflow",
        message: caseStatusMessage,
        tone: caseTone as "info" | "success" | "warning",
      };
    }

    if (!isDefaultDocumentStatus && documentStatus) {
      const normalizedMessage = documentStatus.toLowerCase();
      const documentTone =
        normalizedMessage.includes("failed") ||
        normalizedMessage.includes("not ready") ||
        normalizedMessage.includes("blocked")
          ? "warning"
          : normalizedMessage.includes("complete") ||
            normalizedMessage.includes("ready") ||
            normalizedMessage.includes("generated")
            ? "success"
            : "info";
      return {
        title: "Document workflow",
        message: documentStatus,
        tone: documentTone as "info" | "success" | "warning",
      };
    }

    return null;
  }, [documentStatusMessage, relatedCasesStatus]);
  const endpointLabel = apiBaseUrl.trim().replace(/\/+$/, "") || "same-origin /api";

  return (
    <>
      <section className="mx-auto w-full max-w-6xl">
        <div className="imm-paper-shell imm-fade-up rounded-[1.75rem] p-4 md:p-6" style={{ animationDelay: "60ms" }}>
          <div className="relative z-10">
            <ChatHeader
              legalDisclaimer={legalDisclaimer}
              activeLocale={activeLocale}
              onLocaleChange={onLocaleChange}
            />

            <div className="relative mt-4 grid gap-4 lg:grid-cols-[minmax(0,1.68fr)_minmax(19rem,1fr)] lg:items-start">
              <div
                aria-hidden="true"
                className="pointer-events-none absolute bottom-0 left-[calc(62%+0.25rem)] top-0 hidden w-px bg-gradient-to-b from-transparent via-[rgba(176,174,165,0.35)] to-transparent lg:block"
              />
              <div className="space-y-4">
                <StatusBanner
                  chatError={chatError}
                  supportContext={supportContext}
                  workflowStatus={workflowStatus}
                  relatedCasesStatus={relatedCasesStatus}
                  isSubmitting={isChatSubmitting}
                  submissionPhase={submissionPhase}
                  isSlowChatResponse={isSlowChatResponse}
                  chatPendingElapsedSeconds={chatPendingElapsedSeconds}
                  onRetryLastRequest={onRetryLastRequest}
                  retryPrompt={retryPrompt}
                  showDiagnostics={showOperationalPanels}
                />

                <MessageList
                  endOfThreadRef={endOfThreadRef}
                  isChatSubmitting={isChatSubmitting}
                  chatPendingElapsedSeconds={chatPendingElapsedSeconds}
                  isSlowChatResponse={isSlowChatResponse}
                  enableAgentThinkingTimeline={enableAgentThinkingTimeline}
                  activityByTurn={activityByTurn}
                  activeActivityTurnId={activeActivityTurnId}
                  messages={messages}
                  submissionPhase={submissionPhase}
                  showDiagnostics={showOperationalPanels}
                />

                <MessageComposer
                  draft={draft}
                  isFirstRun={messages.every((message) => message.author !== "user")}
                  isSubmitting={isChatSubmitting}
                  onDraftChange={setDraft}
                  onQuickPromptClick={onQuickPromptClick}
                  onSubmit={onSubmit}
                  remainingCharacters={remainingCharacters}
                  sendDisabled={sendDisabled}
                  submissionPhase={submissionPhase}
                  textareaRef={textareaRef}
                />
              </div>

              {isMobileDrawerOpen ? (
                <div 
                  className="fixed inset-0 z-40 bg-[rgba(20,20,19,0.4)] backdrop-blur-[2px] transition-opacity duration-300 lg:hidden"
                  onClick={closeMobileDrawer}
                  aria-hidden="true"
                />
              ) : null}

              <aside
                id="mobile-case-law-drawer"
                ref={mobileDrawerRef}
                role={isMobileDrawerOpen ? "dialog" : undefined}
                aria-modal={isMobileDrawerOpen ? true : undefined}
                aria-labelledby={isMobileDrawerOpen ? "mobile-case-law-drawer-title" : undefined}
                tabIndex={isMobileDrawerOpen ? -1 : undefined}
                className={`
                  space-y-4 lg:sticky lg:top-4 lg:self-start
                  ${isMobileDrawerOpen 
                    ? "fixed bottom-0 left-0 right-0 z-50 max-h-[85vh] overflow-y-auto rounded-t-3xl border-t border-[rgba(176,174,165,0.75)] bg-[rgba(253,252,248,0.98)] p-4 shadow-[0_-12px_48px_rgba(20,20,19,0.15)] transition-transform duration-300 ease-out translate-y-0" 
                    : "hidden lg:block lg:translate-y-0"
                  }
                `}
              >
                {isMobileDrawerOpen ? (
                  <div className="mb-4 flex items-center justify-between lg:hidden">
                    <h3 className="font-heading text-lg font-semibold text-ink" id="mobile-case-law-drawer-title">
                      Case Law Tools
                    </h3>
                    <button
                      type="button"
                      className="imm-btn-secondary rounded-full border-[rgba(176,174,165,0.6)] bg-[rgba(247,243,234,0.8)] px-0"
                      onClick={closeMobileDrawer}
                      aria-label="Close Case Law Tools drawer"
                    >
                      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M18 6 6 18"/><path d="m6 6 12 12"/>
                      </svg>
                    </button>
                  </div>
                ) : null}

                <RelatedCasePanel
                  documentForum={documentForum}
                  documentMatterId={documentMatterId}
                  documentStatusMessage={documentStatusMessage}
                  documentUploads={documentUploads}
                  documentReadiness={documentReadiness}
                  isDocumentIntakeSubmitting={isDocumentIntakeSubmitting}
                  isDocumentReadinessSubmitting={isDocumentReadinessSubmitting}
                  isDocumentPackageSubmitting={isDocumentPackageSubmitting}
                  isDocumentDownloadSubmitting={isDocumentDownloadSubmitting}
                  isChatSubmitting={isChatSubmitting}
                  isCaseSearchSubmitting={isCaseSearchSubmitting}
                  isExportSubmitting={isExportSubmitting}
                  caseSearchQuery={caseSearchQuery}
                  lastCaseSearchQuery={lastCaseSearchQuery}
                  relatedCasesRetrievalMode={relatedCasesRetrievalMode}
                  sourceStatus={sourceStatus}
                  onCaseSearchQueryChange={onCaseSearchQueryChange}
                  onSearch={() => {
                    void runRelatedCaseSearch();
                  }}
                  relatedCases={relatedCases}
                  matterProfile={matterProfile}
                  relatedCasesStatus={relatedCasesStatus}
                  researchConfidence={researchConfidence}
                  confidenceReasons={confidenceReasons}
                  intakeCompleteness={intakeCompleteness}
                  intakeHints={intakeHints}
                  onExportCase={(caseResult) => {
                    void runCaseExport(caseResult);
                  }}
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
                  onDocumentForumChange={onDocumentForumChange}
                  onDocumentMatterIdChange={onDocumentMatterIdChange}
                  onDocumentUpload={(files) => {
                    void onDocumentUpload(files);
                  }}
                  onRefreshDocumentReadiness={onRefreshDocumentReadiness}
                  onBuildDocumentPackage={() => {
                    void onBuildDocumentPackage();
                  }}
                  onDownloadDocumentPackage={() => {
                    void onDownloadDocumentPackage();
                  }}
                  documentSupportMatrix={documentSupportMatrix}
                  showDiagnostics={showOperationalPanels}
                  statusToneClass={statusToneClass}
                  submissionPhase={submissionPhase}
                  supportStatus={supportContext?.status ?? null}
                  exportingCaseId={exportingCaseId}
                />

                {showOperationalPanels ? (
                  <SupportContextPanel
                    endpointLabel={endpointLabel}
                    supportContext={supportContext}
                  />
                ) : null}
              </aside>
            </div>
          </div>
        </div>
      </section>

      <div className="fixed bottom-6 right-4 z-30 lg:hidden">
        <button
          type="button"
          aria-expanded={isMobileDrawerOpen}
          aria-controls="mobile-case-law-drawer"
          aria-haspopup="dialog"
          className="imm-btn-primary min-h-[56px] rounded-full px-5 text-sm shadow-[0_8px_24px_rgba(217,119,87,0.35)]"
          onClick={openMobileDrawer}
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/>
          </svg>
          Case Law Tools
          {relatedCases.length > 0 ? (
            <span className="ml-1 flex h-5 w-5 items-center justify-center rounded-full bg-[#faf9f5] text-[11px] text-[var(--imm-brand-orange)]">
              {relatedCases.length}
            </span>
          ) : null}
        </button>
      </div>
    </>
  );
}
