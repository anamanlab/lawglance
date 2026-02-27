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
  return "Service temporarily unavailable";
}

function buildWorkflowErrorAction(endpoint: SupportContext["endpoint"] | undefined): string {
  if (endpoint === "/api/research/lawyer-cases" || endpoint === "/api/search/cases") {
    return "Refine the case-law query and retry, or continue using the grounded chat response while sources recover.";
  }
  if (endpoint === "/api/export/cases" || endpoint === "/api/export/cases/approval") {
    return "The case result may still be usable online. Open the decision link directly and retry export later.";
  }
  return "Retry in a moment. If the issue persists, capture the trace ID for support.";
}

function workflowToneClasses(tone: "info" | "success" | "warning"): string {
  if (tone === "success") {
    return "border-[rgba(120,140,93,0.35)] bg-[rgba(238,242,231,0.95)] text-[#4f603d]";
  }
  if (tone === "warning") {
    return "border-[rgba(217,119,87,0.35)] bg-[rgba(248,238,232,0.95)] text-[#6b362a]";
  }
  return "border-[rgba(106,155,204,0.35)] bg-[rgba(238,243,248,0.95)] text-[#36506b]";
}

export function StatusBanner({
  chatError,
  supportContext = null,
  workflowStatus = null,
  relatedCasesStatus = "",
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
        className="imm-paper-card imm-fade-up rounded-2xl border-[rgba(176,174,165,0.45)] bg-[rgba(250,249,245,0.95)] p-4 text-sm text-ink"
        style={{ animationDelay: "120ms" }}
      >
        <div className="relative z-10">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <p className="inline-flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.14em] text-muted">
              <span className="inline-block h-2 w-2 rounded-full bg-[var(--imm-brand-orange)]" aria-hidden="true" />
              Response In Progress
            </p>
            <span className="imm-pill rounded-full border-[rgba(176,174,165,0.45)] bg-[rgba(255,255,255,0.6)] px-2.5 py-1 text-[10px] text-muted">
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
        className="imm-paper-card imm-fade-up rounded-2xl border-[rgba(172,63,47,0.2)] bg-[linear-gradient(180deg,rgba(252,248,243,0.98),rgba(248,239,232,0.92))] p-4 text-sm text-[var(--imm-danger-ink)]"
        style={{ animationDelay: "120ms" }}
      >
        <div className="relative z-10">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <p className="inline-flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.14em] text-[var(--imm-danger-ink)]">
              <span className="inline-block h-2 w-2 rounded-full bg-[var(--imm-brand-orange)]" aria-hidden="true" />
              Workflow Notice
            </p>
            <span className="imm-pill rounded-full border-[rgba(172,63,47,0.18)] bg-[rgba(255,255,255,0.6)] px-2.5 py-1 text-[10px] text-[var(--imm-danger-ink)]">
              {supportContext?.code ?? "Error"}
            </span>
          </div>
          <p className="mt-2 text-base font-semibold leading-snug text-[#4a2118]">
            {buildWorkflowErrorTitle(supportContext?.endpoint)}
          </p>
          <p className="mt-2 leading-7 text-[#6b362a]">
            {relatedCasesStatus || "A related workflow request could not be completed."}
          </p>
          <p className="mt-3 border-l-2 border-[rgba(172,63,47,0.18)] pl-3 text-xs leading-6 text-[#7a4032]">
            {buildWorkflowErrorAction(supportContext?.endpoint)}
          </p>
          {showDiagnostics ? (
            <p className="mt-3 font-mono text-[11px] leading-5 text-[#7a4032]">
              Trace ID: {supportContext?.traceId ?? "Unavailable"}
              {supportContext?.policyReason ? ` • Policy: ${supportContext.policyReason}` : ""}
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
      className="imm-paper-card imm-fade-up rounded-2xl border-[rgba(172,63,47,0.28)] bg-[linear-gradient(180deg,rgba(250,245,242,0.98),rgba(248,236,231,0.95))] p-4 text-sm text-[var(--imm-danger-ink)]"
      style={{ animationDelay: "120ms" }}
    >
      <div className="relative z-10">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <p className="inline-flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.14em] text-[var(--imm-danger-ink)]">
            <span className="inline-block h-2 w-2 rounded-full bg-[var(--imm-brand-orange)]" aria-hidden="true" />
            Incident Notice
          </p>
          <span className="imm-pill rounded-full border-[rgba(172,63,47,0.22)] bg-[rgba(255,255,255,0.6)] px-2.5 py-1 text-[10px] text-[var(--imm-danger-ink)]">
            Attention needed
          </span>
        </div>

        <p className="mt-2 text-base font-semibold leading-snug text-[#4a2118]">{blockingChatError.title}</p>
        <p className="mt-2 leading-7 text-[#6b362a]">{blockingChatError.detail}</p>
        <p className="mt-3 border-l-2 border-[rgba(172,63,47,0.22)] pl-3 text-xs leading-6 text-[#7a4032]">
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
