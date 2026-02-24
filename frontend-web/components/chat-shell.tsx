"use client";

import { FormEvent, useMemo, useRef, useState } from "react";

type MessageAuthor = "assistant" | "user";

type ChatMessage = {
  id: string;
  author: MessageAuthor;
  content: string;
  disclaimer?: string;
};

type ChatShellProps = {
  apiBaseUrl: string;
  legalDisclaimer: string;
};

const ASSISTANT_BOOTSTRAP_TEXT =
  "Welcome to IMMCAD. Ask a Canada immigration question to begin. API wiring lands in US-007.";

function buildMessage(
  id: string,
  author: MessageAuthor,
  content: string,
  disclaimer?: string
): ChatMessage {
  return {
    id,
    author,
    content,
    disclaimer
  };
}

export function ChatShell({
  apiBaseUrl,
  legalDisclaimer
}: ChatShellProps): JSX.Element {
  const messageCounterRef = useRef(0);
  const [draft, setDraft] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([
    buildMessage(
      "assistant-bootstrap",
      "assistant",
      ASSISTANT_BOOTSTRAP_TEXT,
      legalDisclaimer
    )
  ]);

  const endpointLabel = useMemo(() => apiBaseUrl.replace(/\/+$/, ""), [apiBaseUrl]);

  const onSubmit = (event: FormEvent<HTMLFormElement>): void => {
    event.preventDefault();

    const trimmedDraft = draft.trim();
    if (!trimmedDraft) {
      return;
    }

    const userMessageId = `user-${messageCounterRef.current}`;
    messageCounterRef.current += 1;
    const assistantMessageId = `assistant-${messageCounterRef.current}`;
    messageCounterRef.current += 1;

    setMessages((currentMessages) => [
      ...currentMessages,
      buildMessage(userMessageId, "user", trimmedDraft),
      buildMessage(
        assistantMessageId,
        "assistant",
        "Frontend shell captured your message. Backend integration with trace IDs is queued for the next story.",
        legalDisclaimer
      )
    ]);
    setDraft("");
  };

  return (
    <section className="mx-auto flex w-full max-w-4xl flex-col gap-4 rounded-2xl border border-slate-300 bg-white/95 p-4 shadow-xl md:p-6">
      <header className="rounded-lg border border-amber-300 bg-amber-50 p-3 text-sm text-warning">
        <p className="font-semibold">Canada legal scope notice</p>
        <p className="mt-1">{legalDisclaimer}</p>
      </header>

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
                {message.author === "assistant" && message.disclaimer ? (
                  <p className="mt-2 border-t border-slate-200 pt-2 text-xs text-muted">
                    {message.disclaimer}
                  </p>
                ) : null}
              </article>
            </li>
          ))}
        </ol>
      </div>

      <form className="space-y-2" onSubmit={onSubmit}>
        <label className="block text-sm font-medium text-slate-700" htmlFor="chat-input">
          Ask a Canada immigration question
        </label>
        <textarea
          className="h-24 w-full resize-y rounded-lg border border-slate-300 px-3 py-2 text-sm text-ink shadow-sm outline-none ring-accent transition focus:border-accent focus:ring-2"
          id="chat-input"
          name="chat-input"
          onChange={(event) => setDraft(event.target.value)}
          placeholder="Example: What are the eligibility basics for Express Entry?"
          value={draft}
        />
        <div className="flex items-center justify-between gap-3">
          <p className="text-xs text-muted">API target: {endpointLabel}</p>
          <button
            className="rounded-lg bg-ink px-4 py-2 text-sm font-semibold text-white transition hover:bg-slate-700"
            type="submit"
          >
            Send
          </button>
        </div>
      </form>
    </section>
  );
}
