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
            ? "border border-blue-800 bg-gradient-to-br from-blue-950 via-blue-900 to-blue-700 text-white"
            : "border border-slate-200 bg-white text-ink"
        }`}
      >
        <p>{message.content}</p>
        {message.author === "assistant" && message.isPolicyRefusal ? (
          <div className="mt-2 rounded-md border border-amber-300 bg-amber-50 p-2 text-xs text-amber-900">
            <p className="font-semibold uppercase tracking-wide">Policy refusal response</p>
            <p className="mt-1">
              Rephrase the request as general immigration information (eligibility criteria,
              official process steps, or document requirements).
            </p>
            {showDiagnostics && message.traceId ? (
              <p className="mt-1 text-[11px] text-amber-800">Trace ID: {message.traceId}</p>
            ) : null}
          </div>
        ) : null}

        {message.author === "assistant" && message.citations?.length ? (
          <div className="mt-3 border-t border-slate-200 pt-2">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-600">Sources</p>
            <ul className="mt-2 flex flex-wrap gap-2 text-xs">
              {message.citations.map((citation, citationIndex) => (
                <li key={`${message.id}-${citation.url}-${citationIndex}`}>
                  <a
                    aria-label={`Open citation: ${citation.title}${
                      citation.pin ? ` (${citation.pin})` : ""
                    }`}
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
                    <p className="mt-1 max-w-sm text-[11px] text-slate-600">{citation.snippet}</p>
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

        {showDiagnostics && message.author === "assistant" && message.traceId && !message.isPolicyRefusal ? (
          <p className="mt-2 text-[11px] text-slate-500">Trace ID: {message.traceId}</p>
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
    <section className="rounded-xl border border-slate-200 bg-white p-3 shadow-[0_10px_28px_rgba(15,23,42,0.08)]">
      <div className="mb-3 flex items-center justify-between gap-2">
        <h1 className="text-xl font-semibold text-slate-900 md:text-2xl">IMMCAD Assistant</h1>
        <span className="rounded-full border border-slate-300 bg-slate-50 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-slate-700">
          Canada immigration
        </span>
      </div>
      <div
        aria-busy={isSubmitting}
        aria-live="polite"
        aria-relevant="additions"
        className="h-[52vh] min-h-[360px] overflow-y-auto rounded-lg border border-slate-200 bg-gradient-to-b from-slate-50 via-slate-50 to-slate-100/80 p-3"
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
              <article className="max-w-[90%] rounded-2xl border border-slate-200 bg-white px-3 py-2 text-sm leading-relaxed text-ink md:max-w-[78%]">
                <p className="motion-safe:animate-pulse text-slate-600">
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
