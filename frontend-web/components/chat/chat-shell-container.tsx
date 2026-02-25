"use client";

import {
  FormEvent,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import { createApiClient } from "@/lib/api-client";
import type { LawyerCaseSupport } from "@/lib/api-client";
import { ChatHeader } from "@/components/chat/chat-header";
import {
  ASSISTANT_BOOTSTRAP_TEXT,
  ERROR_COPY,
  MAX_MESSAGE_LENGTH,
} from "@/components/chat/constants";
import { MessageComposer } from "@/components/chat/message-composer";
import { MessageList } from "@/components/chat/message-list";
import { RelatedCasePanel } from "@/components/chat/related-case-panel";
import { StatusBanner } from "@/components/chat/status-banner";
import { SupportContextPanel } from "@/components/chat/support-context-panel";
import type {
  ChatErrorState,
  ChatMessage,
  ChatShellProps,
  SubmissionPhase,
  SupportContext,
} from "@/components/chat/types";
import {
  buildMessage,
  buildSessionId,
  buildStatusTone,
  nextMessageId,
} from "@/components/chat/utils";

function buildCaseExportUnavailableMessage(policyReason?: string | null): string {
  switch (policyReason) {
    case "source_export_blocked_by_policy":
      return "Case export is unavailable for this source under current policy.";
    case "export_url_not_allowed_for_source":
    case "export_redirect_url_not_allowed_for_source":
      return "Case export is unavailable because the document URL is not trusted for this source.";
    case "source_not_in_registry_for_export":
      return "Case export is unavailable because the source is not registered for export.";
    case "source_export_metadata_missing":
      return "Case export is unavailable because source metadata is missing for this result.";
    default:
      return "Case export is unavailable for this case result.";
  }
}

function buildCaseSearchErrorStatusMessage(params: {
  code: string;
  message: string;
  policyReason: string | null;
  traceId: string | null;
  showOperationalPanels: boolean;
}): string {
  const { code, message, policyReason, traceId, showOperationalPanels } = params;
  if (code === "VALIDATION_ERROR" && policyReason === "case_search_query_too_broad") {
    return "Case-law query is too broad. Add specific terms such as program, issue, court, or citation.";
  }
  if (showOperationalPanels) {
    return `Unable to search related case law: ${message}${policyReason ? ` (Policy: ${policyReason})` : ""} (Trace ID: ${traceId ?? "Unavailable"})`;
  }
  if (code === "SOURCE_UNAVAILABLE") {
    return "Case-law sources are temporarily unavailable. Please try again shortly.";
  }
  if (code === "RATE_LIMITED") {
    return "Case-law search is temporarily rate limited. Please wait a moment and try again.";
  }
  return "Case-law search is temporarily unavailable. Please try again shortly.";
}

export function ChatShell({
  apiBaseUrl,
  legalDisclaimer,
  showOperationalPanels = false,
}: ChatShellProps): JSX.Element {
  const sessionIdRef = useRef(buildSessionId());
  const messageCounterRef = useRef(0);
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);
  const endOfThreadRef = useRef<HTMLDivElement | null>(null);

  const [draft, setDraft] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [chatError, setChatError] = useState<ChatErrorState | null>(null);
  const [retryPrompt, setRetryPrompt] = useState<string | null>(null);
  const [supportContext, setSupportContext] = useState<SupportContext | null>(null);
  const [relatedCases, setRelatedCases] = useState<LawyerCaseSupport[]>([]);
  const [relatedCasesStatus, setRelatedCasesStatus] = useState("");
  const [caseSearchQuery, setCaseSearchQuery] = useState("");
  const [lastCaseSearchQuery, setLastCaseSearchQuery] = useState<string | null>(null);
  const [exportingCaseId, setExportingCaseId] = useState<string | null>(null);
  const [submissionPhase, setSubmissionPhase] = useState<SubmissionPhase>("idle");

  const apiClient = useMemo(() => createApiClient({ apiBaseUrl }), [apiBaseUrl]);

  const [messages, setMessages] = useState<ChatMessage[]>([
    buildMessage("assistant-bootstrap", "assistant", ASSISTANT_BOOTSTRAP_TEXT, {
      disclaimer: legalDisclaimer,
    }),
  ]);

  const trimmedDraft = draft.trim();
  const sendDisabled = isSubmitting || !trimmedDraft;
  const remainingCharacters = MAX_MESSAGE_LENGTH - draft.length;

  useEffect(() => {
    if (typeof endOfThreadRef.current?.scrollIntoView === "function") {
      endOfThreadRef.current.scrollIntoView({ behavior: "smooth", block: "end" });
    }
  }, [messages, isSubmitting]);

  const submitPrompt = useCallback(
    async (prompt: string, options?: { isRetry?: boolean }): Promise<void> => {
      if (isSubmitting) {
        return;
      }

      const promptToSubmit = prompt.trim();
      if (!promptToSubmit) {
        return;
      }

      if (!options?.isRetry) {
        const userMessageId = nextMessageId("user", messageCounterRef);
        setMessages((currentMessages) => [
          ...currentMessages,
          buildMessage(userMessageId, "user", promptToSubmit),
        ]);
        setDraft("");
      }

      setChatError(null);
      setRetryPrompt(null);
      setRelatedCases([]);
      setRelatedCasesStatus("");
      setLastCaseSearchQuery(null);
      setExportingCaseId(null);
      setIsSubmitting(true);
      setSubmissionPhase("chat");

      try {
        const chatResult = await apiClient.sendChatMessage({
          session_id: sessionIdRef.current,
          message: promptToSubmit,
          locale: "en-CA",
          mode: "standard",
        });

        if (!chatResult.ok) {
          const errorCopy = ERROR_COPY[chatResult.error.code];
          setChatError({
            title: errorCopy.title,
            detail: chatResult.error.message || errorCopy.detail,
            action: errorCopy.action,
            retryable: errorCopy.retryable,
            traceId: chatResult.traceId,
          });
          setRetryPrompt(errorCopy.retryable ? promptToSubmit : null);
          setSupportContext({
            endpoint: "/api/chat",
            status: "error",
            traceId: chatResult.traceId,
            code: chatResult.error.code,
            traceIdMismatch: chatResult.traceIdMismatch,
          });
          return;
        }

        const chatResponse = chatResult.data;
        const isPolicyRefusal = chatResponse.fallback_used.reason === "policy_block";
        const assistantMessageId = nextMessageId("assistant", messageCounterRef);

        setMessages((currentMessages) => [
          ...currentMessages,
          buildMessage(assistantMessageId, "assistant", chatResponse.answer, {
            disclaimer: chatResponse.disclaimer || legalDisclaimer,
            traceId: chatResult.traceId,
            citations: chatResponse.citations,
            isPolicyRefusal,
          }),
        ]);

        setSupportContext({
          endpoint: "/api/chat",
          status: "success",
          traceId: chatResult.traceId,
          traceIdMismatch: false,
        });

        if (isPolicyRefusal) {
          setRelatedCasesStatus(
            "This chat request was blocked by policy. You can still run case-law search with a specific Canadian immigration query."
          );
          return;
        }

        setCaseSearchQuery(promptToSubmit);
        setRelatedCasesStatus("Ready to find related Canadian case law.");
      } finally {
        setIsSubmitting(false);
        setSubmissionPhase("idle");
        textareaRef.current?.focus();
      }
    },
    [apiClient, isSubmitting, legalDisclaimer]
  );

  const runRelatedCaseSearch = useCallback(async (): Promise<void> => {
    const query = caseSearchQuery.trim();
    if (isSubmitting || query.length < 2) {
      return;
    }

    setIsSubmitting(true);
    setSubmissionPhase("cases");
    setExportingCaseId(null);
    setRelatedCasesStatus("Running grounded lawyer case research...");

    try {
      const caseSearchResult = await apiClient.researchLawyerCases({
        session_id: sessionIdRef.current,
        matter_summary: query,
        jurisdiction: "ca",
        limit: 5,
      });

      if (!caseSearchResult.ok) {
        const statusMessage = buildCaseSearchErrorStatusMessage({
          code: caseSearchResult.error.code,
          message: caseSearchResult.error.message,
          policyReason: caseSearchResult.policyReason,
          traceId: caseSearchResult.traceId,
          showOperationalPanels,
        });
        setRelatedCasesStatus(statusMessage);
        setSupportContext({
          endpoint: "/api/research/lawyer-cases",
          status: "error",
          traceId: caseSearchResult.traceId,
          code: caseSearchResult.error.code,
          traceIdMismatch: caseSearchResult.traceIdMismatch,
        });
        return;
      }

      setRelatedCases(caseSearchResult.data.cases);
      setLastCaseSearchQuery(query);
      const noMatchMessage =
        caseSearchResult.data.source_status.official === "unavailable"
          ? "Official case-law sources are temporarily unavailable. Please retry shortly."
          : "No matching case-law records were found for this query.";
      setRelatedCasesStatus(caseSearchResult.data.cases.length ? "" : noMatchMessage);
      setSupportContext({
        endpoint: "/api/research/lawyer-cases",
        status: "success",
        traceId: caseSearchResult.traceId,
        traceIdMismatch: false,
      });
    } finally {
      setIsSubmitting(false);
      setSubmissionPhase("idle");
    }
  }, [apiClient, caseSearchQuery, isSubmitting, showOperationalPanels]);

  const runCaseExport = useCallback(
    async (caseResult: LawyerCaseSupport): Promise<void> => {
      if (isSubmitting) {
        return;
      }

      if (caseResult.export_allowed === false) {
        setRelatedCasesStatus(
          buildCaseExportUnavailableMessage(caseResult.export_policy_reason)
        );
        return;
      }

      if (!caseResult.source_id || !caseResult.document_url) {
        setRelatedCasesStatus(
          buildCaseExportUnavailableMessage("source_export_metadata_missing")
        );
        return;
      }

      const userApproved =
        typeof window !== "undefined"
          ? window.confirm(
              "Export this case PDF now? This will download the document from the official source."
            )
          : false;
      if (!userApproved) {
        setRelatedCasesStatus("Case export cancelled. No file was downloaded.");
        return;
      }

      setIsSubmitting(true);
      setSubmissionPhase("export");
      setExportingCaseId(caseResult.case_id);
      setRelatedCasesStatus("Preparing case PDF export...");

      try {
        const approvalResult = await apiClient.requestCaseExportApproval({
          source_id: caseResult.source_id,
          case_id: caseResult.case_id,
          document_url: caseResult.document_url,
          user_approved: true,
        });

        if (!approvalResult.ok) {
          const errorCopy = ERROR_COPY[approvalResult.error.code];
          const errorDetail = approvalResult.error.message || errorCopy.detail;
          const policyReason = approvalResult.policyReason;
          const statusMessage = showOperationalPanels
            ? `${errorCopy.title}: ${errorDetail}${
                policyReason ? ` (Policy: ${policyReason})` : ""
              } (Trace ID: ${approvalResult.traceId ?? "Unavailable"})`
            : "Case export approval is temporarily unavailable. Please try again shortly.";
          setRelatedCasesStatus(statusMessage);
          setSupportContext({
            endpoint: "/api/export/cases/approval",
            status: "error",
            traceId: approvalResult.traceId,
            code: approvalResult.error.code,
            policyReason,
            traceIdMismatch: approvalResult.traceIdMismatch,
          });
          return;
        }

        const exportResult = await apiClient.exportCasePdf({
          source_id: caseResult.source_id,
          case_id: caseResult.case_id,
          document_url: caseResult.document_url,
          format: "pdf",
          user_approved: true,
          approval_token: approvalResult.data.approval_token,
        });

        if (!exportResult.ok) {
          const errorCopy = ERROR_COPY[exportResult.error.code];
          const errorDetail = exportResult.error.message || errorCopy.detail;
          const policyReason = exportResult.policyReason;
          const isPolicyBlocked = exportResult.error.code === "POLICY_BLOCKED";
          const policyBlockedMessage =
            policyReason === "source_export_user_approval_required"
              ? "Case export requires explicit user approval before download."
              : "Case export was blocked by source policy for this source.";
          const statusMessage = showOperationalPanels
            ? `${errorCopy.title}: ${errorDetail}${
                policyReason ? ` (Policy: ${policyReason})` : ""
              } (Trace ID: ${exportResult.traceId ?? "Unavailable"})`
            : isPolicyBlocked
              ? policyBlockedMessage
              : "Case export is temporarily unavailable. Please try again shortly.";
          setRelatedCasesStatus(statusMessage);
          setSupportContext({
            endpoint: "/api/export/cases",
            status: "error",
            traceId: exportResult.traceId,
            code: exportResult.error.code,
            policyReason,
            traceIdMismatch: exportResult.traceIdMismatch,
          });
          return;
        }

        const fallbackFilename = `${caseResult.case_id}.pdf`;
        const downloadFilename = exportResult.data.filename || fallbackFilename;
        if (typeof window.URL.createObjectURL !== "function") {
          setRelatedCasesStatus(
            `Case export completed, but automatic download is unavailable in this browser (${downloadFilename}).`
          );
          return;
        }
        const objectUrl = window.URL.createObjectURL(exportResult.data.blob);
        const downloadLink = document.createElement("a");
        downloadLink.href = objectUrl;
        downloadLink.download = downloadFilename;
        downloadLink.rel = "noopener";
        document.body.append(downloadLink);
        downloadLink.click();
        downloadLink.remove();
        if (typeof window.URL.revokeObjectURL === "function") {
          window.URL.revokeObjectURL(objectUrl);
        }

        setRelatedCasesStatus(`Download started: ${downloadFilename}`);
        setSupportContext({
          endpoint: "/api/export/cases",
          status: "success",
          traceId: exportResult.traceId,
          policyReason: exportResult.data.policyReason,
          traceIdMismatch: false,
        });
      } finally {
        setExportingCaseId(null);
        setIsSubmitting(false);
        setSubmissionPhase("idle");
      }
    },
    [apiClient, isSubmitting, showOperationalPanels]
  );

  const onSubmit = useCallback(
    (event: FormEvent<HTMLFormElement>): void => {
      event.preventDefault();
      void submitPrompt(draft);
    },
    [draft, submitPrompt]
  );

  const onRetryLastRequest = useCallback((): void => {
    if (!retryPrompt || isSubmitting) {
      return;
    }
    void submitPrompt(retryPrompt, { isRetry: true });
  }, [isSubmitting, retryPrompt, submitPrompt]);

  const onQuickPromptClick = useCallback(
    (prompt: string): void => {
      if (isSubmitting) {
        return;
      }
      setDraft(prompt);
      textareaRef.current?.focus();
    },
    [isSubmitting]
  );

  const onCaseSearchQueryChange = useCallback(
    (value: string): void => {
      setCaseSearchQuery(value);
      const nextQuery = value.trim().toLowerCase();
      const previousQuery = (lastCaseSearchQuery ?? "").trim().toLowerCase();
      if (!nextQuery || !previousQuery || relatedCases.length === 0) {
        return;
      }
      if (nextQuery !== previousQuery) {
        setRelatedCasesStatus(
          "Case-search query updated. Click Find related cases to refresh results."
        );
      }
    },
    [lastCaseSearchQuery, relatedCases.length]
  );

  const statusToneClass = useMemo(
    () => buildStatusTone(supportContext?.status ?? null),
    [supportContext]
  );

  return (
    <section className="mx-auto flex w-full max-w-6xl flex-col gap-4 rounded-3xl border border-slate-300/90 bg-white/90 p-4 shadow-[0_22px_56px_rgba(15,23,42,0.14)] backdrop-blur-sm md:p-6">
      <ChatHeader legalDisclaimer={legalDisclaimer} />

      <div className="grid gap-4 lg:grid-cols-[minmax(0,1.7fr)_minmax(18rem,1fr)]">
        <div className="space-y-4">
          <StatusBanner
            chatError={chatError}
            isSubmitting={isSubmitting}
            onRetryLastRequest={onRetryLastRequest}
            retryPrompt={retryPrompt}
            showDiagnostics={showOperationalPanels}
          />

          <MessageList
            endOfThreadRef={endOfThreadRef}
            isSubmitting={isSubmitting}
            messages={messages}
            submissionPhase={submissionPhase}
            showDiagnostics={showOperationalPanels}
          />

          <MessageComposer
            draft={draft}
            isSubmitting={isSubmitting}
            onDraftChange={setDraft}
            onQuickPromptClick={onQuickPromptClick}
            onSubmit={onSubmit}
            remainingCharacters={remainingCharacters}
            sendDisabled={sendDisabled}
            submissionPhase={submissionPhase}
            textareaRef={textareaRef}
          />
        </div>

        <aside className="space-y-4 lg:sticky lg:top-4 lg:self-start">
          <RelatedCasePanel
            isSubmitting={isSubmitting}
            caseSearchQuery={caseSearchQuery}
            lastCaseSearchQuery={lastCaseSearchQuery}
            onCaseSearchQueryChange={onCaseSearchQueryChange}
            onSearch={() => {
              void runRelatedCaseSearch();
            }}
            relatedCases={relatedCases}
            relatedCasesStatus={relatedCasesStatus}
            onExportCase={(caseResult) => {
              void runCaseExport(caseResult);
            }}
            showDiagnostics={showOperationalPanels}
            statusToneClass={statusToneClass}
            submissionPhase={submissionPhase}
            supportStatus={supportContext?.status ?? null}
            exportingCaseId={exportingCaseId}
          />

          {showOperationalPanels ? (
            <SupportContextPanel
              endpointLabel={apiBaseUrl.replace(/\/+$/, "")}
              supportContext={supportContext}
            />
          ) : null}
        </aside>
      </div>
    </section>
  );
}
