"use client";

import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import {
  ApiErrorCode,
  CaseSearchResult,
  ChatCitation,
  createApiClient,
} from "@/lib/api-client";

type MessageAuthor = "assistant" | "user";

type ChatMessage = {
  id: string;
  author: MessageAuthor;
  content: string;
  disclaimer?: string;
  traceId?: string | null;
  citations?: ChatCitation[];
  isPolicyRefusal?: boolean;
};

type ChatShellProps = {
  apiBaseUrl: string;
  legalDisclaimer: string;
};

type SupportContext = {
  endpoint: "/api/chat" | "/api/search/cases";
  status: "success" | "error";
  traceId: string | null;
  code?: ApiErrorCode;
  traceIdMismatch: boolean;
};

type ErrorCopy = {
  title: string;
  detail: string;
  action: string;
  retryable: boolean;
};

const ERROR_COPY: Record<ApiErrorCode, ErrorCopy> = {
  UNAUTHORIZED: {
    title: "Authentication required",
    detail: "Confirm the backend authentication configuration is valid for this environment.",
    action: "Update credentials and submit the question again.",
    retryable: true,
  },
  VALIDATION_ERROR: {
    title: "Request validation failed",
    detail: "The request payload did not pass API validation checks.",
    action: "Use a shorter, plain-language question and retry.",
    retryable: true,
  },
  PROVIDER_ERROR: {
    title: "Provider unavailable",
    detail: "The upstream provider is temporarily unavailable. Please retry.",
    action: "Retry shortly. If this repeats, share the trace ID with support.",
    retryable: true,
  },
  SOURCE_UNAVAILABLE: {
    title: "Source unavailable",
    detail: "Authoritative case-law source is unavailable in hardened mode.",
    action: "Retry later when the source is back online.",
    retryable: true,
  },
  POLICY_BLOCKED: {
    title: "Policy-blocked request",
    detail: "The request violates policy constraints and cannot be completed.",
    action: "Ask for general information instead of personalized strategy or representation.",
    retryable: false,
  },
  RATE_LIMITED: {
    title: "Rate limited",
    detail: "Request quota exceeded. Wait briefly before submitting again.",
    action: "Wait a moment, then retry the same question.",
    retryable: true,
  },
  UNKNOWN_ERROR: {
    title: "Unexpected error",
    detail: "The API returned an unknown error state. Please retry.",
    action: "Retry once. If it fails again, share the trace ID with support.",
    retryable: true,
  },
};

const QUICK_PROMPTS = [
  "What are the eligibility basics for Express Entry?",
  "What documents are required for a study permit?",
  "How does sponsorship for a spouse work in Canada?",
];

const ASSISTANT_BOOTSTRAP_TEXT =
  "Welcome to IMMCAD. Ask a Canada immigration question to begin.";

const MAX_MESSAGE_LENGTH = 8000;

type SubmissionPhase = "idle" | "chat" | "cases";

function buildSessionId(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return `session-${Date.now()}-${Math.random().toString(16).slice(2, 10)}`;
}

function nextMessageId(prefix: string, messageCounterRef: { current: number }): string {
  const id = `${prefix}-${messageCounterRef.current}`;
  messageCounterRef.current += 1;
  return id;
}

function buildMessage(
  id: string,
  author: MessageAuthor,
  content: string,
  {
    disclaimer,
    traceId = null,
    citations = [],
    isPolicyRefusal = false,
  }: {
    disclaimer?: string;
    traceId?: string | null;
    citations?: ChatCitation[];
    isPolicyRefusal?: boolean;
  } = {}
): ChatMessage {
  return {
    id,
    author,
    content,
    disclaimer,
    traceId,
    citations,
    isPolicyRefusal,
  };
}

function buildStatusTone(status: SupportContext["status"] | null): string {
  if (status === "success") {
    return "bg-emerald-100 text-emerald-800 border-emerald-300";
  }
  if (status === "error") {
    return "bg-red-100 text-red-800 border-red-300";
  }
  return "bg-slate-100 text-slate-700 border-slate-300";
}

export function ChatShell({
  apiBaseUrl,
  legalDisclaimer
}: ChatShellProps): JSX.Element {
  const sessionIdRef = useRef(buildSessionId());
  const messageCounterRef = useRef(0);
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);
  const endOfThreadRef = useRef<HTMLDivElement | null>(null);

  const [draft, setDraft] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [chatError, setChatError] = useState<{
    title: string;
    detail: string;
    action: string;
    retryable: boolean;
    traceId: string | null;
  } | null>(null);
  const [retryPrompt, setRetryPrompt] = useState<string | null>(null);
  const [supportContext, setSupportContext] = useState<SupportContext | null>(null);
  const [relatedCases, setRelatedCases] = useState<CaseSearchResult[]>([]);
  const [relatedCasesStatus, setRelatedCasesStatus] = useState<string>("");
  const [pendingCaseQuery, setPendingCaseQuery] = useState<string | null>(null);
  const [submissionPhase, setSubmissionPhase] = useState<SubmissionPhase>("idle");

  const apiClient = useMemo(() => createApiClient({ apiBaseUrl }), [apiBaseUrl]);

  const [messages, setMessages] = useState<ChatMessage[]>([
    buildMessage(
      "assistant-bootstrap",
      "assistant",
      ASSISTANT_BOOTSTRAP_TEXT,
      {
        disclaimer: legalDisclaimer,
      }
    )
  ]);

  const endpointLabel = useMemo(() => apiBaseUrl.replace(/\/+$/, ""), [apiBaseUrl]);
  const trimmedDraft = draft.trim();
  const sendDisabled = isSubmitting || !trimmedDraft;
  const remainingCharacters = MAX_MESSAGE_LENGTH - draft.length;

  useEffect(() => {
    if (typeof endOfThreadRef.current?.scrollIntoView === "function") {
      endOfThreadRef.current.scrollIntoView({ behavior: "smooth", block: "end" });
    }
  }, [messages, isSubmitting]);

  const submitPrompt = async (
    prompt: string,
    options?: { isRetry?: boolean }
  ): Promise<void> => {
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
        buildMessage(userMessageId, "user", promptToSubmit)
      ]);
      setDraft("");
    }

    setChatError(null);
    setRetryPrompt(null);
    setRelatedCases([]);
    setRelatedCasesStatus("");
    setPendingCaseQuery(null);
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
          "Policy refusal response returned. Ask a general informational question to continue."
        );
        return;
      }
      setPendingCaseQuery(promptToSubmit);
      setRelatedCasesStatus(
        "Related case search is ready. Click Search related cases to fetch authoritative metadata."
      );
    } finally {
      setIsSubmitting(false);
      setSubmissionPhase("idle");
      textareaRef.current?.focus();
    }
  };

  const runRelatedCaseSearch = async (): Promise<void> => {
    if (isSubmitting || !pendingCaseQuery) {
      return;
    }

    setIsSubmitting(true);
    setSubmissionPhase("cases");
    setRelatedCasesStatus("Loading related case results...");

    try {
      const caseSearchResult = await apiClient.searchCases({
        query: pendingCaseQuery,
        jurisdiction: "ca",
        limit: 5,
      });

      if (!caseSearchResult.ok) {
        const errorCopy = ERROR_COPY[caseSearchResult.error.code];
        setRelatedCasesStatus(
          `${errorCopy.title}: ${caseSearchResult.error.message || errorCopy.detail} (Trace ID: ${caseSearchResult.traceId ?? "Unavailable"})`
        );
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
          : "No related case results returned for this question."
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
  };

  const onSubmit = async (event: FormEvent<HTMLFormElement>): Promise<void> => {
    event.preventDefault();
    await submitPrompt(draft);
  };

  const onRetryLastRequest = (): void => {
    if (!retryPrompt || isSubmitting) {
      return;
    }
    void submitPrompt(retryPrompt, { isRetry: true });
  };

  const onQuickPromptClick = (prompt: string): void => {
    if (isSubmitting) {
      return;
    }
    setDraft(prompt);
    textareaRef.current?.focus();
  };

  return (
    <section className="mx-auto flex w-full max-w-6xl flex-col gap-4 rounded-3xl border border-slate-300/90 bg-white/95 p-4 shadow-[0_18px_48px_rgba(15,23,42,0.16)] md:p-6">
      <header className="rounded-2xl border border-amber-300 bg-gradient-to-r from-amber-50 to-amber-100 p-4 text-sm text-warning">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <p className="text-lg font-semibold text-slate-900">Canada legal scope notice</p>
          <span className="rounded-full border border-amber-300 bg-white px-3 py-1 text-xs font-semibold uppercase tracking-wide text-amber-700">
            Informational only
          </span>
        </div>
        <p className="mt-2 leading-6 text-slate-800">{legalDisclaimer}</p>
      </header>

      <div className="grid gap-4 lg:grid-cols-[minmax(0,1.7fr)_minmax(18rem,1fr)]">
        <div className="space-y-4">
          {chatError ? (
            <div
              aria-live="assertive"
              className="rounded-xl border border-red-300 bg-red-50 p-3 text-sm text-red-900"
            >
              <p className="font-semibold">{chatError.title}</p>
              <p className="mt-1">{chatError.detail}</p>
              <p className="mt-2 text-xs">{chatError.action}</p>
              <p className="mt-1 text-xs">Trace ID: {chatError.traceId ?? "Unavailable"}</p>
              {chatError.retryable && retryPrompt ? (
                <button
                  className="mt-2 min-h-[44px] min-w-[44px] rounded-md bg-red-700 px-3 py-1.5 text-xs font-semibold text-white transition duration-200 ease-out hover:bg-red-800 disabled:cursor-not-allowed disabled:bg-red-500"
                  disabled={isSubmitting}
                  onClick={onRetryLastRequest}
                  type="button"
                >
                  Retry last request
                </button>
              ) : null}
            </div>
          ) : null}

          <section className="rounded-xl border border-slate-200 bg-white p-3">
            <div className="mb-3 flex items-center justify-between gap-2">
              <h1 className="text-xl font-semibold text-slate-900 md:text-2xl">IMMCAD Assistant</h1>
              <span className="rounded-full border px-3 py-1 text-xs font-semibold uppercase tracking-wide text-slate-700">
                Canada immigration
              </span>
            </div>
            <div
              aria-busy={isSubmitting}
              aria-live="polite"
              aria-relevant="additions"
              className="h-[52vh] min-h-[360px] overflow-y-auto rounded-lg border border-slate-200 bg-slate-50 p-3"
              role="log"
            >
              <ol className="space-y-3">
                {messages.map((message) => (
                  <li
                    className={`flex ${
                      message.author === "user" ? "justify-end" : "justify-start"
                    }`}
                    key={message.id}
                  >
                    <article
                      className={`max-w-[90%] rounded-xl px-3 py-2 text-sm leading-7 md:max-w-[78%] ${
                        message.author === "user"
                          ? "bg-gradient-to-br from-blue-900 to-blue-700 text-white"
                          : "border border-slate-200 bg-white text-ink"
                      }`}
                    >
                      <p>{message.content}</p>
                      {message.author === "assistant" && message.isPolicyRefusal ? (
                        <div className="mt-2 rounded-md border border-amber-300 bg-amber-50 p-2 text-xs text-amber-900">
                          <p className="font-semibold uppercase tracking-wide">
                            Policy refusal response
                          </p>
                          <p className="mt-1">
                            Rephrase the request as general immigration information (eligibility
                            criteria, official process steps, or document requirements).
                          </p>
                          {message.traceId ? (
                            <p className="mt-1 text-[11px] text-amber-800">
                              Trace ID: {message.traceId}
                            </p>
                          ) : null}
                        </div>
                      ) : null}
                      {message.author === "assistant" && message.citations?.length ? (
                        <div className="mt-3 border-t border-slate-200 pt-2">
                          <p className="text-xs font-semibold uppercase tracking-wide text-slate-600">
                            Sources
                          </p>
                          <ul className="mt-2 flex flex-wrap gap-2 text-xs">
                            {message.citations.map((citation) => (
                              <li key={`${message.id}-${citation.url}`}>
                                <a
                                  aria-label={`Open citation: ${citation.title}${citation.pin ? ` (${citation.pin})` : ""}`}
                                  className="inline-flex min-h-[44px] items-center gap-2 rounded-full border border-slate-300 bg-slate-50 px-3 py-1.5 font-medium text-slate-900 underline-offset-2 transition duration-200 ease-out hover:bg-slate-100 hover:underline"
                                  href={citation.url}
                                  rel="noreferrer"
                                  target="_blank"
                                >
                                  <span>{citation.title}</span>
                                  {citation.pin ? (
                                    <span className="rounded-full bg-slate-200 px-2 py-0.5 text-[11px] text-slate-700">
                                      {citation.pin}
                                    </span>
                                  ) : null}
                                </a>
                                {citation.snippet ? (
                                  <p className="mt-1 max-w-sm text-[11px] text-slate-600">
                                    {citation.snippet}
                                  </p>
                                ) : null}
                              </li>
                            ))}
                          </ul>
                        </div>
                      ) : null}
                      {message.author === "assistant" && message.disclaimer ? (
                        <p className="mt-2 border-t border-slate-200 pt-2 text-xs text-muted">
                          {message.disclaimer}
                        </p>
                      ) : null}
                      {message.author === "assistant" && message.traceId && !message.isPolicyRefusal ? (
                        <p className="mt-2 text-[11px] text-slate-500">Trace ID: {message.traceId}</p>
                      ) : null}
                    </article>
                  </li>
                ))}
                {isSubmitting ? (
                  <li className="flex justify-start">
                    <article className="max-w-[90%] rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm leading-relaxed text-ink md:max-w-[78%]">
                      <p className="motion-safe:animate-pulse text-slate-600">
                        {submissionPhase === "cases"
                          ? "Loading related case references..."
                          : "Submitting your question..."}
                      </p>
                    </article>
                  </li>
                ) : null}
              </ol>
              <div ref={endOfThreadRef} />
            </div>
          </section>

          <section className="rounded-xl border border-slate-200 bg-white p-3">
            <form className="space-y-3" onSubmit={onSubmit}>
              <label className="block text-sm font-semibold text-slate-700" htmlFor="chat-input">
                Ask a Canada immigration question
              </label>
              <div className="flex flex-wrap gap-2" role="group" aria-label="Quick prompts">
                {QUICK_PROMPTS.map((prompt) => (
                  <button
                    className="min-h-[44px] min-w-[44px] rounded-full border border-slate-300 bg-slate-50 px-3 py-1.5 text-xs font-medium text-slate-800 transition duration-200 ease-out hover:border-blue-300 hover:bg-blue-50 disabled:cursor-not-allowed disabled:opacity-60"
                    disabled={isSubmitting}
                    key={prompt}
                    onClick={() => onQuickPromptClick(prompt)}
                    type="button"
                  >
                    {prompt}
                  </button>
                ))}
              </div>
              <textarea
                className="h-28 w-full resize-y rounded-lg border border-slate-300 px-3 py-2 text-base leading-7 text-ink shadow-sm transition duration-200 ease-out focus:border-blue-600 focus:ring-2 focus:ring-blue-200"
                disabled={isSubmitting}
                id="chat-input"
                maxLength={MAX_MESSAGE_LENGTH}
                name="chat-input"
                onChange={(event) => setDraft(event.target.value)}
                placeholder="Example: What are the eligibility basics for Express Entry?"
                ref={textareaRef}
                value={draft}
              />
              <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <p className="text-xs text-muted">API target: {endpointLabel}</p>
                  <p className="text-[11px] text-slate-500">{remainingCharacters} characters remaining</p>
                  {isSubmitting ? (
                    <p aria-live="polite" className="text-[11px] text-slate-500">
                      {submissionPhase === "cases"
                        ? "Searching related cases..."
                        : "Sending request..."}
                    </p>
                  ) : null}
                </div>
                <button
                  className="min-h-[44px] min-w-[120px] rounded-lg bg-gradient-to-r from-blue-900 to-blue-700 px-4 py-2 text-sm font-semibold text-white transition duration-200 ease-out hover:from-blue-800 hover:to-blue-600 disabled:cursor-not-allowed disabled:from-slate-400 disabled:to-slate-400"
                  disabled={sendDisabled}
                  type="submit"
                >
                  {isSubmitting
                    ? submissionPhase === "cases"
                      ? "Loading..."
                      : "Sending..."
                    : "Send"}
                </button>
              </div>
            </form>
          </section>
        </div>

        <aside className="space-y-4">
          <section className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm">
            <div className="mb-2 flex items-center justify-between gap-2">
              <p className="font-semibold text-slate-800">Related case search</p>
              <span
                className={`rounded-full border px-2.5 py-1 text-[11px] font-semibold uppercase tracking-wide ${buildStatusTone(supportContext?.status ?? null)}`}
              >
                {supportContext?.status ?? "idle"}
              </span>
            </div>
            <button
              className="min-h-[44px] min-w-[44px] rounded-md border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-800 transition duration-200 ease-out hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-60"
              disabled={isSubmitting || !pendingCaseQuery}
              onClick={() => {
                void runRelatedCaseSearch();
              }}
              type="button"
            >
              {isSubmitting && submissionPhase === "cases" ? "Searching..." : "Search related cases"}
            </button>
            {relatedCasesStatus ? <p className="mt-1 text-slate-600">{relatedCasesStatus}</p> : null}
            {relatedCases.length ? (
              <ul className="mt-2 space-y-2 text-xs text-slate-700">
                {relatedCases.map((result) => (
                  <li className="rounded-md border border-slate-200 bg-white p-2" key={result.case_id}>
                    <a
                      className="font-medium text-slate-900 underline underline-offset-2"
                      href={result.url}
                      rel="noreferrer"
                      target="_blank"
                    >
                      {result.title}
                    </a>
                    <p className="mt-1">{result.citation}</p>
                  </li>
                ))}
              </ul>
            ) : null}
          </section>

          <section className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-xs text-slate-700">
            <p className="font-semibold text-slate-800">Support context</p>
            <p className="mt-1">API target: {endpointLabel}</p>
            <p>Last endpoint: {supportContext?.endpoint ?? "Not called yet"}</p>
            <p>Last outcome: {supportContext ? supportContext.status : "Not available"}</p>
            <p>Last error code: {supportContext?.code ?? "None"}</p>
            <p>Trace ID: {supportContext?.traceId ?? "Unavailable"}</p>
            {supportContext?.traceIdMismatch ? (
              <p className="mt-1 font-medium text-red-700">
                Trace mismatch detected between header and error body.
              </p>
            ) : null}
          </section>
        </aside>
      </div>
    </section>
  );
}
