import { memo, type RefObject } from "react";

import type { ChatMessage, SubmissionPhase } from "@/components/chat/types";

type MessageListProps = {
  messages: ChatMessage[];
  isChatSubmitting: boolean;
  chatPendingElapsedSeconds: number;
  isSlowChatResponse: boolean;
  submissionPhase: SubmissionPhase;
  showDiagnostics?: boolean;
  endOfThreadRef: RefObject<HTMLDivElement>;
};

function renderLoadingCopy(submissionPhase: SubmissionPhase): string {
  if (submissionPhase === "cases") {
    return "Loading related case references...";
  }
  if (submissionPhase === "export") {
    return "Preparing case PDF export...";
  }
  return "Submitting your question...";
}

const MessageBubble = memo(function MessageBubble({
  message,
  showDiagnostics,
}: {
  message: ChatMessage;
  showDiagnostics: boolean;
}): JSX.Element {
  const isUser = message.author === "user";

  return (
    <li className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <article
        className={`relative max-w-[94%] overflow-hidden rounded-2xl px-3 py-3 text-sm shadow-sm md:max-w-[82%] md:px-4 ${
          isUser
            ? "border border-[#3b342e] bg-gradient-to-br from-[#141413] via-[#23211f] to-[#3a322c] text-[#faf9f5] shadow-[0_12px_28px_rgba(20,20,19,0.22)]"
            : "border border-[rgba(176,174,165,0.45)] bg-[rgba(250,249,245,0.97)] text-ink"
        }`}
      >
        {!isUser ? (
          <div className="absolute left-0 top-0 h-full w-1 bg-gradient-to-b from-[#d97757] via-[#6a9bcc] to-[#788c5d]" aria-hidden="true" />
        ) : null}

        <div className={`relative ${isUser ? "" : "pl-1"}`}>
          <div className="mb-1 flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[0.14em]">
            <span className={isUser ? "text-[#f0e9df]" : "text-muted"}>{isUser ? "You" : "IMMCAD"}</span>
            {!isUser && message.citations?.length ? (
              <span className="rounded-full border border-[rgba(176,174,165,0.45)] bg-[#f3f1ea] px-2 py-0.5 text-[9px] text-muted">
                {message.citations.length} source{message.citations.length === 1 ? "" : "s"}
              </span>
            ) : null}
            {!isUser && message.confidence ? (
              <span className={`rounded-full border px-2 py-0.5 text-[9px] ${
                message.confidence === "high" 
                  ? "border-[#b8c6a6] bg-[#eef2e7] text-[#5f7248]" 
                  : message.confidence === "medium" 
                    ? "border-[rgba(217,119,87,0.35)] bg-[#f8eee8] text-[#8a543f]" 
                    : "border-[rgba(172,63,47,0.22)] bg-[#fcece9] text-[#8f4635]"
              }`}>
                {message.confidence} confidence
              </span>
            ) : null}
            {!isUser && message.fallbackUsed?.used ? (
              <span className="rounded-full border border-[rgba(217,119,87,0.35)] bg-[#f8eee8] px-2 py-0.5 text-[9px] text-[#8a543f]">
                fallback response
              </span>
            ) : null}
          </div>

          <p className={`leading-7 ${isUser ? "text-[#faf9f5]" : "text-ink"}`}>{message.content}</p>

          {message.author === "assistant" && message.fallbackUsed?.used ? (
            <p className="mt-2 text-[11px] leading-5 text-muted">
              Response generated in degraded mode due to temporary provider issues. Verify against the grounded sources below.
            </p>
          ) : null}

          {message.author === "assistant" && message.isPolicyRefusal ? (
            <div className="mt-3 rounded-xl border border-[rgba(217,119,87,0.35)] bg-[#f8eee8] p-3 text-xs text-[#6f3f2f]">
              <p className="font-semibold uppercase tracking-wide">Policy refusal response</p>
              <p className="mt-1 leading-6">
                Rephrase the request as general immigration information (eligibility criteria,
                official process steps, or document requirements).
              </p>
              {showDiagnostics && message.traceId ? (
                <p className="mt-2 font-mono text-[11px] text-[#7c4a38]">Trace ID: {message.traceId}</p>
              ) : null}
            </div>
          ) : null}

          {message.author === "assistant" && message.citations?.length ? (
            <div className="mt-3 border-t border-[rgba(176,174,165,0.4)] pt-3">
              <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-muted">Grounded sources</p>
              <ul className="mt-2 grid gap-2 text-xs">
                {message.citations.map((citation, citationIndex) => (
                  <li key={`${message.id}-${citation.url}-${citationIndex}`}>
                    <a
                      aria-label={`Open citation: ${citation.title}${citation.pin ? ` (${citation.pin})` : ""}`}
                      className="block rounded-xl border border-[rgba(176,174,165,0.42)] bg-[#f7f4ec] px-3 py-2 transition duration-200 ease-out hover:border-[rgba(106,155,204,0.35)] hover:bg-[#f2f5f8]"
                      href={citation.url}
                      rel="noreferrer"
                      target="_blank"
                    >
                      <span className="flex flex-wrap items-center gap-2">
                        <span className="font-semibold text-ink underline-offset-2 hover:underline">
                          {citation.title}
                        </span>
                        {citation.pin ? (
                          <span className="rounded-full border border-[rgba(176,174,165,0.4)] bg-white px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.08em] text-muted">
                            {citation.pin}
                          </span>
                        ) : null}
                      </span>
                      {citation.snippet ? (
                        <span className="mt-1 block leading-5 text-muted">{citation.snippet}</span>
                      ) : null}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          ) : null}

          {message.author === "assistant" && message.disclaimer ? (
            <p className="mt-3 border-t border-[rgba(176,174,165,0.4)] pt-2 text-xs leading-6 text-muted">
              {message.disclaimer}
            </p>
          ) : null}
        </div>
      </article>
    </li>
  );
});

export function MessageList({
  messages,
  isChatSubmitting,
  chatPendingElapsedSeconds,
  isSlowChatResponse,
  submissionPhase,
  showDiagnostics = false,
  endOfThreadRef,
}: MessageListProps): JSX.Element {
  return (
    <section className="imm-fade-up" style={{ animationDelay: "140ms" }}>
      <div className="relative z-10">
        <div
          aria-busy={isChatSubmitting}
          aria-live="polite"
          aria-relevant="additions"
          className="imm-scrollbar relative h-[46vh] min-h-[300px] overflow-y-auto overscroll-contain rounded-2xl border border-[rgba(176,174,165,0.45)] bg-[linear-gradient(180deg,#f8f5ee_0%,#f3efe5_100%)] p-3 md:h-[54vh] md:min-h-[380px] md:p-4 shadow-inner"
          role="log"
        >
          <div className="pointer-events-none absolute inset-0 opacity-60" aria-hidden="true">
            <div className="h-full w-full bg-[repeating-linear-gradient(to_bottom,transparent_0,transparent_39px,rgba(176,174,165,0.14)_39px,rgba(176,174,165,0.14)_40px)]" />
          </div>
          <div
            aria-hidden="true"
            className="pointer-events-none absolute inset-x-0 top-0 h-8 bg-gradient-to-b from-[rgba(248,245,238,0.95)] to-transparent"
          />
          <div
            aria-hidden="true"
            className="pointer-events-none absolute inset-x-0 bottom-0 h-10 bg-gradient-to-t from-[rgba(243,239,229,0.96)] to-transparent"
          />
          <ol className="relative space-y-3">
            {messages.map((message) => (
              <MessageBubble key={message.id} message={message} showDiagnostics={showDiagnostics} />
            ))}
            {isChatSubmitting ? (
              <li className="flex justify-start">
                <article className="max-w-[90%] w-full sm:w-[280px] rounded-2xl border border-[rgba(176,174,165,0.42)] bg-[rgba(250,249,245,0.96)] px-4 py-3 text-sm leading-relaxed text-ink md:max-w-[78%]">
                  <p className="mb-2.5 text-[10px] font-semibold uppercase tracking-[0.14em] text-muted">
                    Processing
                  </p>
                  <div className="flex animate-pulse flex-col gap-2.5">
                    <div className="h-2.5 w-full rounded-full bg-[rgba(176,174,165,0.3)]" />
                    <div className="h-2.5 w-3/4 rounded-full bg-[rgba(176,174,165,0.3)]" />
                    <div className="h-2.5 w-1/2 rounded-full bg-[rgba(176,174,165,0.3)]" />
                  </div>
                  <p className="mt-3 text-[11px] leading-5 text-muted">
                    {chatPendingElapsedSeconds > 0
                      ? `Waiting ${chatPendingElapsedSeconds}s for a response...`
                      : "Submitting your question..."}
                  </p>
                  {isSlowChatResponse ? (
                    <p className="mt-1 text-[11px] leading-5 text-warning">
                      Taking longer than usual. The request is still running.
                    </p>
                  ) : null}
                  <span className="sr-only">{renderLoadingCopy(submissionPhase)}</span>
                </article>
              </li>
            ) : null}
          </ol>
          <div ref={endOfThreadRef} />
        </div>
      </div>
    </section>
  );
}
