import type {
  CaseSearchResponsePayload,
  ChatResponsePayload,
} from "@/lib/api-client";

export const CHAT_SUCCESS_RESPONSE: ChatResponsePayload = {
  answer: "Express Entry uses a points-based ranking system for candidates.",
  confidence: "high",
  disclaimer:
    "IMMCAD provides Canadian immigration information only and does not provide legal advice or representation.",
  fallback_used: {
    used: false,
    provider: null,
    reason: null,
  },
  citations: [
    {
      source_id: "ircc-express-entry-overview",
      title: "IRCC Express Entry Overview",
      url: "https://www.canada.ca/en/immigration-refugees-citizenship/services/immigrate-canada/express-entry/works.html",
      pin: "Eligibility",
      snippet: "Candidates are ranked under the Comprehensive Ranking System (CRS).",
    },
  ],
};

export const CHAT_POLICY_REFUSAL_RESPONSE: ChatResponsePayload = {
  answer:
    "I can provide general information, but I cannot provide personalized legal representation strategy.",
  confidence: "low",
  disclaimer:
    "IMMCAD provides Canadian immigration information only and does not provide legal advice or representation.",
  fallback_used: {
    used: true,
    provider: "policy",
    reason: "policy_block",
  },
  citations: [],
};

export const CASE_SEARCH_SUCCESS_RESPONSE: CaseSearchResponsePayload = {
  results: [
    {
      case_id: "case-1",
      title: "Sample Tribunal Decision",
      citation: "2025 FC 100",
      decision_date: "2025-01-11",
      url: "https://example.test/cases/1",
      source_id: "canlii",
      document_url: "https://example.test/cases/1/document.pdf",
    },
  ],
};

export const SOURCE_UNAVAILABLE_ERROR = {
  error: {
    code: "SOURCE_UNAVAILABLE",
    message: "Authoritative source is unavailable.",
    trace_id: "error-trace-body",
  },
};

export const UNAUTHORIZED_ERROR = {
  error: {
    code: "UNAUTHORIZED",
    message: "Missing or invalid bearer token",
    trace_id: "error-trace-auth",
  },
};
