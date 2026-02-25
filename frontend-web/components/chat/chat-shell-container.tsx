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
import type { CaseSearchResult } from "@/lib/api-client";
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
  const [relatedCases, setRelatedCases] = useState<CaseSearchResult[]>([]);
  const [relatedCasesStatus, setRelatedCasesStatus] = useState("");
  const [pendingCaseQuery, setPendingCaseQuery] = useState<string | null>(null);
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
      setPendingCaseQuery(null);
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
          setPendingCaseQuery(null);
          setRelatedCasesStatus(
            "Case-law search is unavailable for this request. Ask a general immigration question to continue."
          );
          return;
        }

        setPendingCaseQuery(promptToSubmit);
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
    if (isSubmitting || !pendingCaseQuery) {
      return;
    }

    setIsSubmitting(true);
    setSubmissionPhase("cases");
    setExportingCaseId(null);
    setRelatedCasesStatus("Searching official Canadian case law...");

    try {
      const caseSearchResult = await apiClient.searchCases({
        query: pendingCaseQuery,
        jurisdiction: "ca",
        limit: 5,
      });

      if (!caseSearchResult.ok) {
        const errorCopy = ERROR_COPY[caseSearchResult.error.code];
        const errorDetail = caseSearchResult.error.message || errorCopy.detail;
        const statusMessage = showOperationalPanels
          ? `${errorCopy.title}: ${errorDetail} (Trace ID: ${caseSearchResult.traceId ?? "Unavailable"})`
          : "Case-law search is temporarily unavailable. Please try again shortly.";
        setRelatedCasesStatus(statusMessage);
        setSupportContext({
          endpoint: "/api/search/cases",
          status: "error",
          traceId: caseSearchResult.traceId,
          code: caseSearchResult.error.code,
          traceIdMismatch: caseSearchResult.traceIdMismatch,
        });
        return;
      }

      setRelatedCases(caseSearchResult.data.results);
      setRelatedCasesStatus(
        caseSearchResult.data.results.length
          ? ""
          : "No matching case-law records were found for this question."
      );
      setSupportContext({
        endpoint: "/api/search/cases",
        status: "success",
        traceId: caseSearchResult.traceId,
        traceIdMismatch: false,
      });
    } finally {
      setIsSubmitting(false);
      setSubmissionPhase("idle");
    }
  }, [apiClient, isSubmitting, pendingCaseQuery, showOperationalPanels]);

  const runCaseExport = useCallback(
    async (caseResult: CaseSearchResult): Promise<void> => {
      if (isSubmitting) {
        return;
      }

      if (!caseResult.source_id || !caseResult.document_url) {
        setRelatedCasesStatus(
          "Case export is unavailable because the source metadata is missing for this result."
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
        const exportResult = await apiClient.exportCasePdf({
          source_id: caseResult.source_id,
          case_id: caseResult.case_id,
          document_url: caseResult.document_url,
          format: "pdf",
          user_approved: true,
        });

        if (!exportResult.ok) {
          const errorCopy = ERROR_COPY[exportResult.error.code];
          const errorDetail = exportResult.error.message || errorCopy.detail;
          const statusMessage = showOperationalPanels
            ? `${errorCopy.title}: ${errorDetail} (Trace ID: ${exportResult.traceId ?? "Unavailable"})`
            : "Case export is temporarily unavailable. Please try again shortly.";
          setRelatedCasesStatus(statusMessage);
          setSupportContext({
            endpoint: "/api/export/cases",
            status: "error",
            traceId: exportResult.traceId,
            code: exportResult.error.code,
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
            onSearch={() => {
              void runRelatedCaseSearch();
            }}
            pendingCaseQuery={pendingCaseQuery}
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
