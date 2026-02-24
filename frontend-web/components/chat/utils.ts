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
    return "bg-emerald-100 text-emerald-800 border-emerald-300";
  }
  if (status === "error") {
    return "bg-red-100 text-red-800 border-red-300";
  }
  return "bg-slate-100 text-slate-700 border-slate-300";
}

export function phaseLabel(submissionPhase: "chat" | "cases" | "idle"): string {
  if (submissionPhase === "cases") {
    return "Searching related cases...";
  }
  if (submissionPhase === "chat") {
    return "Sending request...";
  }
  return "Ready";
}
