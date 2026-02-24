import type { ApiErrorCode } from "@/lib/api-client";
import type { ErrorCopy } from "@/components/chat/types";

export const ERROR_COPY: Record<ApiErrorCode, ErrorCopy> = {
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

export const QUICK_PROMPTS = [
  "What are the eligibility basics for Express Entry?",
  "What documents are required for a study permit?",
  "How does sponsorship for a spouse work in Canada?",
];

export const ASSISTANT_BOOTSTRAP_TEXT =
  "Welcome to IMMCAD. Ask a Canada immigration question to begin.";

export const MAX_MESSAGE_LENGTH = 8000;
