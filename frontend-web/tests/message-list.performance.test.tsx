import { createRef } from "react";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { MessageList } from "@/components/chat/message-list";
import type { ChatMessage } from "@/components/chat/types";

function buildThreadMessage(index: number): ChatMessage {
  return {
    id: `msg-${index}`,
    author: index % 2 === 0 ? "assistant" : "user",
    content: `Thread message ${index}`,
    disclaimer: index % 6 === 0 ? "General information only." : undefined,
    traceId: index % 4 === 0 ? `trace-${index}` : null,
    citations:
      index % 3 === 0
        ? [
            {
              source_id: `src-${index}`,
              title: `Source ${index}`,
              url: `https://example.com/${index}`,
              pin: "Section 1",
              snippet: "Example citation snippet.",
            },
          ]
        : [],
    isPolicyRefusal: false,
  };
}

describe("message list long-thread behavior", () => {
  afterEach(() => {
    cleanup();
  });

  it("renders a long thread without dropping earliest or latest messages", () => {
    const messages = Array.from({ length: 140 }, (_, index) => buildThreadMessage(index));

    render(
      <MessageList
        endOfThreadRef={createRef<HTMLDivElement>()}
        isChatSubmitting={false}
        chatPendingElapsedSeconds={0}
        isSlowChatResponse={false}
        messages={messages}
        submissionPhase="idle"
      />
    );

    expect(screen.getByText("Thread message 0")).toBeTruthy();
    expect(screen.getByText("Thread message 139")).toBeTruthy();
    expect(screen.getByText("Source 138")).toBeTruthy();
  });

  it("keeps thread content stable when submission state toggles", () => {
    const messages = Array.from({ length: 60 }, (_, index) => buildThreadMessage(index));

    const { rerender } = render(
      <MessageList
        endOfThreadRef={createRef<HTMLDivElement>()}
        isChatSubmitting={false}
        chatPendingElapsedSeconds={0}
        isSlowChatResponse={false}
        messages={messages}
        submissionPhase="idle"
      />
    );

    rerender(
      <MessageList
        endOfThreadRef={createRef<HTMLDivElement>()}
        isChatSubmitting={true}
        chatPendingElapsedSeconds={3}
        isSlowChatResponse={false}
        messages={messages}
        submissionPhase="chat"
      />
    );

    expect(screen.getByText("Thread message 59")).toBeTruthy();
    expect(screen.getByText("Submitting your question...")).toBeTruthy();
  });
});
