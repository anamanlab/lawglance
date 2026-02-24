"use client";

import { FormEvent, useMemo, useRef, useState } from "react";
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
  apiBearerToken: string | null;
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
};

const ERROR_COPY: Record<ApiErrorCode, ErrorCopy> = {
  UNAUTHORIZED: {
    title: "Authentication required",
    detail: "Confirm the frontend bearer token matches the API configuration.",
  },
  VALIDATION_ERROR: {
    title: "Request validation failed",
    detail: "The request payload did not pass API validation checks.",
  },
  PROVIDER_ERROR: {
    title: "Provider unavailable",
    detail: "The upstream provider is temporarily unavailable. Please retry.",
  },
  SOURCE_UNAVAILABLE: {
    title: "Source unavailable",
    detail: "Authoritative case-law source is unavailable in hardened mode.",
  },
  POLICY_BLOCKED: {
    title: "Policy-blocked request",
    detail: "The request violates policy constraints and cannot be completed.",
  },
  RATE_LIMITED: {
    title: "Rate limited",
    detail: "Request quota exceeded. Wait briefly before submitting again.",
  },
  UNKNOWN_ERROR: {
    title: "Unexpected error",
    detail: "The API returned an unknown error state. Please retry.",
  },
};

const ASSISTANT_BOOTSTRAP_TEXT =
  "Welcome to IMMCAD. Ask a Canada immigration question to begin.";

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

export function ChatShell({
  apiBaseUrl,
  apiBearerToken,
  legalDisclaimer
}: ChatShellProps): JSX.Element {
  const sessionIdRef = useRef(buildSessionId());
  const messageCounterRef = useRef(0);
  const [draft, setDraft] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [chatError, setChatError] = useState<{
    title: string;
    detail: string;
    traceId: string | null;
  } | null>(null);
  const [supportContext, setSupportContext] = useState<SupportContext | null>(null);
  const [relatedCases, setRelatedCases] = useState<CaseSearchResult[]>([]);
  const [relatedCasesStatus, setRelatedCasesStatus] = useState<string>("");

  const apiClient = useMemo(
    () => createApiClient({ apiBaseUrl, bearerToken: apiBearerToken }),
    [apiBaseUrl, apiBearerToken]
  );

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

  const onSubmit = async (event: FormEvent<HTMLFormElement>): Promise<void> => {
    event.preventDefault();

    if (isSubmitting) {
      return;
    }

    const trimmedDraft = draft.trim();
    if (!trimmedDraft) {
      return;
    }

    const userMessageId = nextMessageId("user", messageCounterRef);

    setMessages((currentMessages) => [
      ...currentMessages,
      buildMessage(userMessageId, "user", trimmedDraft)
    ]);
    setDraft("");
    setChatError(null);
    setRelatedCases([]);
    setRelatedCasesStatus("");
    setIsSubmitting(true);

    try {
      const chatResult = await apiClient.sendChatMessage({
        session_id: sessionIdRef.current,
        message: trimmedDraft,
        locale: "en-CA",
        mode: "standard",
      });

      if (!chatResult.ok) {
        const errorCopy = ERROR_COPY[chatResult.error.code];
        setChatError({
          title: errorCopy.title,
          detail: chatResult.error.message || errorCopy.detail,
          traceId: chatResult.traceId,
        });
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
        setRelatedCasesStatus("Policy refusal response returned. Case search skipped.");
        return;
      }

      const caseSearchResult = await apiClient.searchCases({
        query: trimmedDraft,
        jurisdiction: "ca",
        limit: 5,
      });

      if (!caseSearchResult.ok) {
        const errorCopy = ERROR_COPY[caseSearchResult.error.code];
        setRelatedCasesStatus(
          `${errorCopy.title}: ${caseSearchResult.error.message || errorCopy.detail}`
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
    }
  };

  return (
    <section className="mx-auto flex w-full max-w-4xl flex-col gap-4 rounded-2xl border border-slate-300 bg-white/95 p-4 shadow-xl md:p-6">
      <header className="rounded-lg border border-amber-300 bg-amber-50 p-3 text-sm text-warning">
        <p className="font-semibold">Canada legal scope notice</p>
        <p className="mt-1">{legalDisclaimer}</p>
      </header>

      {chatError ? (
        <div
          aria-live="assertive"
          className="rounded-lg border border-red-300 bg-red-50 p-3 text-sm text-red-900"
        >
          <p className="font-semibold">{chatError.title}</p>
          <p className="mt-1">{chatError.detail}</p>
          <p className="mt-2 text-xs">Trace ID: {chatError.traceId ?? "Unavailable"}</p>
        </div>
      ) : null}

      <div
        aria-live="polite"
        className="h-[52vh] min-h-[360px] overflow-y-auto rounded-lg border border-slate-200 bg-panel p-3"
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
                className={`max-w-[86%] rounded-xl px-3 py-2 text-sm leading-relaxed md:max-w-[74%] ${
                  message.author === "user"
                    ? "bg-accent text-white"
                    : "border border-slate-200 bg-white text-ink"
                }`}
              >
                <p>{message.content}</p>
                {message.author === "assistant" && message.isPolicyRefusal ? (
                  <p className="mt-2 text-xs font-semibold uppercase tracking-wide text-amber-700">
                    Policy refusal response
                  </p>
                ) : null}
                {message.author === "assistant" && message.citations?.length ? (
                  <div className="mt-3 border-t border-slate-200 pt-2">
                    <p className="text-xs font-semibold uppercase tracking-wide text-slate-600">
                      Sources
                    </p>
                    <ul className="mt-2 space-y-2 text-xs">
                      {message.citations.map((citation) => (
                        <li className="rounded-md bg-slate-50 p-2" key={`${message.id}-${citation.url}`}>
                          <a
                            className="font-medium text-slate-900 underline underline-offset-2"
                            href={citation.url}
                            rel="noreferrer"
                            target="_blank"
                          >
                            {citation.title}
                          </a>
                          <p className="mt-1 text-slate-600">{citation.pin}</p>
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
                {message.author === "assistant" && message.traceId ? (
                  <p className="mt-2 text-[11px] text-slate-500">Trace ID: {message.traceId}</p>
                ) : null}
              </article>
            </li>
          ))}
        </ol>
      </div>

      <section className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm">
        <p className="font-semibold text-slate-800">Related case search</p>
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

      <form className="space-y-2" onSubmit={onSubmit}>
        <label className="block text-sm font-medium text-slate-700" htmlFor="chat-input">
          Ask a Canada immigration question
        </label>
        <textarea
          className="h-24 w-full resize-y rounded-lg border border-slate-300 px-3 py-2 text-sm text-ink shadow-sm outline-none ring-accent transition focus:border-accent focus:ring-2"
          disabled={isSubmitting}
          id="chat-input"
          name="chat-input"
          onChange={(event) => setDraft(event.target.value)}
          placeholder="Example: What are the eligibility basics for Express Entry?"
          value={draft}
        />
        <div className="flex items-center justify-between gap-3">
          <p className="text-xs text-muted">API target: {endpointLabel}</p>
          <button
            className="rounded-lg bg-ink px-4 py-2 text-sm font-semibold text-white transition hover:bg-slate-700 disabled:cursor-not-allowed disabled:bg-slate-500"
            disabled={isSubmitting}
            type="submit"
          >
            {isSubmitting ? "Sending..." : "Send"}
          </button>
        </div>
      </form>

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
    </section>
  );
}
