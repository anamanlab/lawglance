import { memo, type RefObject } from "react";

import type { ChatMessage, SubmissionPhase } from "@/components/chat/types";

type MessageListProps = {
  messages: ChatMessage[];
  isSubmitting: boolean;
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
  return (
    <li className={`flex ${message.author === "user" ? "justify-end" : "justify-start"}`}>
      <article
        className={`max-w-[92%] rounded-2xl px-3 py-2 text-sm leading-7 shadow-sm md:max-w-[78%] ${
          message.author === "user"
            ? "border border-[#3b342e] bg-gradient-to-br from-[#141413] via-[#23211f] to-[#3a322c] text-[#faf9f5]"
            : "border border-[rgba(176,174,165,0.45)] bg-[rgba(250,249,245,0.96)] text-ink"
        }`}
      >
        <p>{message.content}</p>
        {message.author === "assistant" && message.isPolicyRefusal ? (
          <div className="mt-2 rounded-md border border-[rgba(217,119,87,0.35)] bg-[#f8eee8] p-2 text-xs text-[#6f3f2f]">
            <p className="font-semibold uppercase tracking-wide">Policy refusal response</p>
            <p className="mt-1">
              Rephrase the request as general immigration information (eligibility criteria,
              official process steps, or document requirements).
            </p>
            {showDiagnostics && message.traceId ? (
              <p className="mt-1 text-[11px] text-[#7c4a38]">Trace ID: {message.traceId}</p>
            ) : null}
          </div>
        ) : null}

        {message.author === "assistant" && message.citations?.length ? (
          <div className="mt-3 border-t border-[rgba(176,174,165,0.45)] pt-2">
            <p className="text-xs font-semibold uppercase tracking-wide text-muted">Sources</p>
            <ul className="mt-2 flex flex-wrap gap-2 text-xs">
              {message.citations.map((citation, citationIndex) => (
                <li key={`${message.id}-${citation.url}-${citationIndex}`}>
                  <a
                    aria-label={`Open citation: ${citation.title}${
                      citation.pin ? ` (${citation.pin})` : ""
                    }`}
                    className="inline-flex min-h-[44px] items-center gap-2 rounded-full border border-[rgba(176,174,165,0.8)] bg-[#f6f3eb] px-3 py-1.5 font-medium text-ink underline-offset-2 transition duration-200 ease-out hover:bg-[#ece8de] hover:underline"
                    href={citation.url}
                    rel="noreferrer"
                    target="_blank"
                  >
                    <span>{citation.title}</span>
                    {citation.pin ? (
                      <span className="rounded-full bg-[#e8e6dc] px-2 py-0.5 text-[11px] text-muted">
                        {citation.pin}
                      </span>
                    ) : null}
                  </a>
                  {citation.snippet ? (
                    <p className="mt-1 max-w-sm text-[11px] text-muted">{citation.snippet}</p>
                  ) : null}
                </li>
              ))}
            </ul>
          </div>
        ) : null}

        {message.author === "assistant" && message.disclaimer ? (
          <p className="mt-2 border-t border-[rgba(176,174,165,0.45)] pt-2 text-xs text-muted">
            {message.disclaimer}
          </p>
        ) : null}

        {showDiagnostics && message.author === "assistant" && message.traceId && !message.isPolicyRefusal ? (
          <p className="mt-2 text-[11px] text-muted">Trace ID: {message.traceId}</p>
        ) : null}
      </article>
    </li>
  );
});

export function MessageList({
  messages,
  isSubmitting,
  submissionPhase,
  showDiagnostics = false,
  endOfThreadRef,
}: MessageListProps): JSX.Element {
  return (
    <section className="rounded-xl border border-[rgba(176,174,165,0.45)] bg-[rgba(250,249,245,0.94)] p-3 shadow-[0_10px_28px_rgba(20,20,19,0.06)]">
      <div className="mb-3 flex items-center justify-between gap-2">
        <h1 className="text-xl font-semibold text-ink md:text-2xl">IMMCAD Assistant</h1>
        <span className="rounded-full border border-[rgba(176,174,165,0.75)] bg-[#f6f3eb] px-3 py-1 text-xs font-semibold uppercase tracking-wide text-muted">
          Canada immigration
        </span>
      </div>
      <div
        aria-busy={isSubmitting}
        aria-live="polite"
        aria-relevant="additions"
        className="h-[52vh] min-h-[360px] overflow-y-auto rounded-lg border border-[rgba(176,174,165,0.45)] bg-gradient-to-b from-[#f6f3eb] via-[#f6f3eb] to-[#ece8de] p-3"
        role="log"
      >
        <ol className="space-y-3">
          {messages.map((message) => (
            <MessageBubble
              key={message.id}
              message={message}
              showDiagnostics={showDiagnostics}
            />
          ))}
          {isSubmitting ? (
            <li className="flex justify-start">
              <article className="max-w-[90%] rounded-2xl border border-[rgba(176,174,165,0.45)] bg-[rgba(250,249,245,0.96)] px-3 py-2 text-sm leading-relaxed text-ink md:max-w-[78%]">
                <p className="motion-safe:animate-pulse text-muted">
                  {renderLoadingCopy(submissionPhase)}
                </p>
              </article>
            </li>
          ) : null}
        </ol>
        <div ref={endOfThreadRef} />
      </div>
    </section>
  );
}
