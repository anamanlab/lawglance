import type { ChatCitation } from "@/lib/api-client";
import type {
  ChatMessage,
  MessageAuthor,
  SupportContext,
} from "@/components/chat/types";

export function buildSessionId(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return `session-${Date.now()}-${Math.random().toString(16).slice(2, 10)}`;
}

export function nextMessageId(
  prefix: string,
  messageCounterRef: { current: number }
): string {
  const id = `${prefix}-${messageCounterRef.current}`;
  messageCounterRef.current += 1;
  return id;
}

export function buildMessage(
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

export function buildStatusTone(status: SupportContext["status"] | null): string {
  if (status === "success") {
    return "bg-[#eef2e7] text-[#5f7248] border-[#b8c6a6]";
  }
  if (status === "error") {
    return "bg-red-100 text-red-800 border-red-300";
  }
  return "bg-[#eeeae0] text-muted border-[rgba(176,174,165,0.75)]";
}

export function phaseLabel(submissionPhase: "chat" | "cases" | "export" | "idle"): string {
  if (submissionPhase === "cases") {
    return "Searching related cases...";
  }
  if (submissionPhase === "export") {
    return "Preparing case PDF export...";
  }
  if (submissionPhase === "chat") {
    return "Sending request...";
  }
  return "Ready";
}
