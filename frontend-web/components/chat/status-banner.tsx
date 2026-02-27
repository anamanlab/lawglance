import type {
  ChatErrorState,
  SubmissionPhase,
  SupportContext,
} from "@/components/chat/types";

type StatusBannerProps = {
  chatError: ChatErrorState | null;
  supportContext?: SupportContext | null;
  workflowStatus?:
    | {
        title: string;
        message: string;
        tone: "info" | "success" | "warning";
      }
    | null;
  relatedCasesStatus?: string;
  documentStatusMessage?: string;
  isSubmitting: boolean;
  retryPrompt: string | null;
  submissionPhase?: SubmissionPhase;
  isSlowChatResponse?: boolean;
  chatPendingElapsedSeconds?: number;
  showDiagnostics?: boolean;
  onRetryLastRequest: () => void;
};

function buildWorkflowErrorTitle(endpoint: SupportContext["endpoint"] | undefined): string {
  if (endpoint === "/api/research/lawyer-cases" || endpoint === "/api/search/cases") {
    return "Related case-law search unavailable";
  }
  if (endpoint === "/api/export/cases" || endpoint === "/api/export/cases/approval") {
    return "Case export unavailable";
  }
  if (endpoint === "/api/documents/support-matrix") {
    return "Document support matrix unavailable";
  }
  return "Service temporarily unavailable";
}

function buildWorkflowErrorAction(endpoint: SupportContext["endpoint"] | undefined): string {
  if (endpoint === "/api/research/lawyer-cases" || endpoint === "/api/search/cases") {
    return "Refine the case-law query and retry, or continue using the grounded chat response while sources recover.";
  }
  if (endpoint === "/api/export/cases" || endpoint === "/api/export/cases/approval") {
    return "The case result may still be usable online. Open the decision link directly and retry export later.";
  }
  if (endpoint === "/api/documents/support-matrix") {
    return "Upload and readiness can continue with fallback profile guidance. Retry in a moment and share the trace ID with support if it persists.";
  }
  return "Retry in a moment. If the issue persists, capture the trace ID for support.";
}

function buildWorkflowErrorMessage(params: {
  endpoint: SupportContext["endpoint"] | undefined;
  relatedCasesStatus: string;
  documentStatusMessage: string;
}): string {
  const { endpoint, relatedCasesStatus, documentStatusMessage } = params;
  const normalizedCaseStatus = relatedCasesStatus.trim();
  const normalizedDocumentStatus = documentStatusMessage.trim();

  if (endpoint?.startsWith("/api/documents")) {
    return (
      normalizedDocumentStatus || "A document workflow request could not be completed."
    );
  }
  if (
    endpoint === "/api/research/lawyer-cases" ||
    endpoint === "/api/search/cases" ||
    endpoint === "/api/export/cases" ||
    endpoint === "/api/export/cases/approval"
  ) {
    return normalizedCaseStatus || "A related workflow request could not be completed.";
  }
  return (
    normalizedCaseStatus ||
    normalizedDocumentStatus ||
    "A related workflow request could not be completed."
  );
}

function workflowToneClasses(tone: "info" | "success" | "warning"): string {
  if (tone === "success") {
    return "border-[rgba(111,132,89,0.35)] bg-[var(--imm-success-soft)] text-[var(--imm-success-ink)]";
  }
  if (tone === "warning") {
    return "border-[rgba(192,106,77,0.35)] bg-[var(--imm-primary-soft)] text-[var(--imm-danger-ink)]";
  }
  return "border-[rgba(95,132,171,0.35)] bg-[var(--imm-accent-soft)] text-[var(--imm-accent-ink)]";
}

export function StatusBanner({
  chatError,
  supportContext = null,
  workflowStatus = null,
  relatedCasesStatus = "",
  documentStatusMessage = "",
  isSubmitting,
  retryPrompt,
  submissionPhase,
  isSlowChatResponse = false,
  chatPendingElapsedSeconds = 0,
  showDiagnostics = false,
  onRetryLastRequest,
}: StatusBannerProps): JSX.Element | null {
  const hasNonChatWorkflowError =
    !chatError &&
    supportContext?.status === "error" &&
    supportContext.endpoint !== "/api/chat";
  const showWorkflowTraceId = showDiagnostics || Boolean(supportContext?.traceId);
  const showSlowResponseBanner =
    !chatError &&
    !hasNonChatWorkflowError &&
    isSlowChatResponse &&
    submissionPhase === "chat";

  if (
    !chatError &&
    !hasNonChatWorkflowError &&
    !showSlowResponseBanner &&
    !workflowStatus
  ) {
    return null;
  }

  if (showSlowResponseBanner) {
    return (
      <div
        aria-live="polite"
        className="imm-paper-card imm-fade-up rounded-2xl border-[var(--imm-border-soft)] bg-[var(--imm-surface-soft)] p-4 text-sm text-ink"
        style={{ animationDelay: "120ms" }}
      >
        <div className="relative z-10">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <p className="inline-flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.14em] text-muted">
              <span className="inline-block h-2 w-2 rounded-full bg-[var(--imm-brand-orange)]" aria-hidden="true" />
              Response In Progress
            </p>
            <span className="imm-pill rounded-full border-[var(--imm-border-soft)] bg-[var(--imm-surface-soft)] px-2.5 py-1 text-[10px] text-muted">
              {chatPendingElapsedSeconds}s
            </span>
          </div>
          <p className="mt-2 text-base font-semibold leading-snug text-ink">
            This response is taking longer than usual
          </p>
          <p className="mt-2 leading-7 text-muted">
            The request is still running. You can wait for the answer or retry if it remains stuck.
          </p>
        </div>
      </div>
    );
  }

  if (hasNonChatWorkflowError) {
    return (
      <div
        aria-live="assertive"
        className="imm-paper-card imm-fade-up rounded-2xl border-[rgba(172,63,47,0.2)] bg-[linear-gradient(180deg,rgba(246,238,233,0.96),rgba(242,229,224,0.92))] p-4 text-sm text-[var(--imm-danger-ink)]"
        style={{ animationDelay: "120ms" }}
      >
        <div className="relative z-10">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <p className="inline-flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.14em] text-[var(--imm-danger-ink)]">
              <span className="inline-block h-2 w-2 rounded-full bg-[var(--imm-brand-orange)]" aria-hidden="true" />
              Workflow Notice
            </p>
            <span className="imm-pill rounded-full border-[rgba(172,63,47,0.18)] bg-[var(--imm-surface-soft)] px-2.5 py-1 text-[10px] text-[var(--imm-danger-ink)]">
              {supportContext?.code ?? "Error"}
            </span>
          </div>
          <p className="mt-2 text-base font-semibold leading-snug text-[var(--imm-danger-ink)]">
            {buildWorkflowErrorTitle(supportContext?.endpoint)}
          </p>
          <p className="mt-2 leading-7 text-[var(--imm-danger-ink)]">
            {buildWorkflowErrorMessage({
              endpoint: supportContext?.endpoint,
              relatedCasesStatus,
              documentStatusMessage,
            })}
          </p>
          <p className="mt-3 border-l-2 border-[rgba(172,63,47,0.18)] pl-3 text-xs leading-6 text-[var(--imm-danger-ink)]">
            {buildWorkflowErrorAction(supportContext?.endpoint)}
          </p>
          {showWorkflowTraceId ? (
            <p className="mt-3 font-mono text-[11px] leading-5 text-[var(--imm-danger-ink)]">
              Trace ID: {supportContext?.traceId ?? "Unavailable"}
              {showDiagnostics && supportContext?.policyReason
                ? ` • Policy: ${supportContext.policyReason}`
                : ""}
            </p>
          ) : null}
        </div>
      </div>
    );
  }

  if (workflowStatus) {
    return (
      <div
        aria-live="polite"
        className={`imm-paper-card imm-fade-up rounded-2xl border p-4 text-sm ${workflowToneClasses(workflowStatus.tone)}`}
        style={{ animationDelay: "120ms" }}
      >
        <div className="relative z-10">
          <p className="text-[11px] font-semibold uppercase tracking-[0.14em]">
            Workflow update
          </p>
          <p className="mt-2 text-base font-semibold leading-snug">{workflowStatus.title}</p>
          <p className="mt-2 leading-7">{workflowStatus.message}</p>
        </div>
      </div>
    );
  }

  const blockingChatError = chatError;
  if (!blockingChatError) {
    return null;
  }

  return (
    <div
      aria-live="assertive"
      className="imm-paper-card imm-fade-up rounded-2xl border-[rgba(172,63,47,0.28)] bg-[linear-gradient(180deg,rgba(246,238,233,0.96),rgba(241,226,221,0.95))] p-4 text-sm text-[var(--imm-danger-ink)]"
      style={{ animationDelay: "120ms" }}
    >
      <div className="relative z-10">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <p className="inline-flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.14em] text-[var(--imm-danger-ink)]">
            <span className="inline-block h-2 w-2 rounded-full bg-[var(--imm-brand-orange)]" aria-hidden="true" />
            Incident Notice
          </p>
          <span className="imm-pill rounded-full border-[rgba(172,63,47,0.22)] bg-[var(--imm-surface-soft)] px-2.5 py-1 text-[10px] text-[var(--imm-danger-ink)]">
            Attention needed
          </span>
        </div>

        <p className="mt-2 text-base font-semibold leading-snug text-[var(--imm-danger-ink)]">{blockingChatError.title}</p>
        <p className="mt-2 leading-7 text-[var(--imm-danger-ink)]">{blockingChatError.detail}</p>
        <p className="mt-3 border-l-2 border-[rgba(172,63,47,0.22)] pl-3 text-xs leading-6 text-[var(--imm-danger-ink)]">
          {blockingChatError.action}
        </p>

        {blockingChatError.retryable && retryPrompt ? (
          <button
            className="imm-btn-danger mt-3 px-4 py-2 w-full sm:w-auto text-[11px]"
            disabled={isSubmitting}
            onClick={onRetryLastRequest}
            type="button"
          >
            Retry last request
          </button>
        ) : null}
      </div>
    </div>
  );
}
