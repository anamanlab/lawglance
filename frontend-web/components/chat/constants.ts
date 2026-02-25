import type { ApiErrorCode } from "@/lib/api-client";
import type { ErrorCopy } from "@/components/chat/types";

export const ERROR_COPY: Record<ApiErrorCode, ErrorCopy> = {
  UNAUTHORIZED: {
    title: "Authentication required",
    detail: "We could not authenticate your request to the service.",
    action:
      "Verify IMMCAD_API_BEARER_TOKEN (or API_BEARER_TOKEN) is configured on the frontend server, then retry.",
    retryable: true,
  },
  VALIDATION_ERROR: {
    title: "We couldn't process that question",
    detail: "Please rephrase your question in plain language and try again.",
    action: "Try a shorter question with one topic.",
    retryable: true,
  },
  PROVIDER_ERROR: {
    title: "Service temporarily unavailable",
    detail: "The answer service is temporarily unavailable.",
    action: "Please try again in a moment.",
    retryable: true,
  },
  SOURCE_UNAVAILABLE: {
    title: "Case-law source unavailable",
    detail: "Official case-law sources are temporarily unavailable.",
    action: "Please try again shortly.",
    retryable: true,
  },
  POLICY_BLOCKED: {
    title: "Request outside scope",
    detail: "We can only provide general Canadian immigration information.",
    action: "Ask a general informational question instead of personalized legal strategy.",
    retryable: false,
  },
  RATE_LIMITED: {
    title: "Rate limited",
    detail: "Too many requests were sent in a short period.",
    action: "Wait a moment, then retry the same question.",
    retryable: true,
  },
  UNKNOWN_ERROR: {
    title: "Unexpected error",
    detail: "Something went wrong while processing your request.",
    action: "Please retry once.",
    retryable: true,
  },
};

export const QUICK_PROMPTS = [
  "What are the eligibility basics for Express Entry?",
  "What documents are required for a study permit?",
  "How does sponsorship for a spouse work in Canada?",
];

export const ASSISTANT_BOOTSTRAP_TEXT =
  "Welcome to IMMCAD. Ask a Canadian immigration question to get started.";

export const MAX_MESSAGE_LENGTH = 8000;
