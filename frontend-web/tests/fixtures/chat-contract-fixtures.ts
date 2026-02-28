import type {
  CaseSearchResponsePayload,
  ChatResponsePayload,
  LawyerCaseResearchResponsePayload,
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

export const CHAT_SUCCESS_WITH_RESEARCH_PREVIEW: ChatResponsePayload = {
  answer: "I found a relevant Federal Court precedent and included it in the case-law panel.",
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
      source_id: "FC_DECISIONS",
      title: "Federal Court decision feed",
      url: "https://decisions.fct-cf.gc.ca/fc-cf/decisions/en/rss.do",
      pin: "2024 FC 101",
      snippet: "Relevant FC precedent surfaced for this chat answer.",
    },
  ],
  research_preview: {
    retrieval_mode: "auto",
    query: "Need precedent on inadmissibility findings in Federal Court",
    source_status: {
      official: "ok",
      canlii: "not_used",
    },
    cases: [
      {
        case_id: "2024-FC-101",
        title: "Auto Preview Decision",
        citation: "2024 FC 101",
        source_id: "FC_DECISIONS",
        court: "FC",
        decision_date: "2024-03-01",
        url: "https://example.test/cases/auto-preview",
        document_url: "https://example.test/cases/auto-preview/document.pdf",
        docket_numbers: ["IMM-2024-101"],
        source_event_type: "new",
        pdf_status: "available",
        pdf_reason: null,
        export_allowed: true,
        export_policy_reason: "source_export_allowed",
        relevance_reason: "Auto-selected because citation anchor and target court match.",
        summary: null,
      },
    ],
  },
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
      source_id: "SCC_DECISIONS",
      document_url:
        "https://decisions.scc-csc.ca/scc-csc/scc-csc/en/item/123/index.do",
      export_allowed: true,
      export_policy_reason: "source_export_allowed",
    },
  ],
};

export const LAWYER_RESEARCH_SUCCESS_RESPONSE: LawyerCaseResearchResponsePayload = {
  matter_profile: {
    issue_tags: ["procedural_fairness"],
    target_court: "fc",
  },
  cases: [
    {
      case_id: "case-1",
      title: "Sample Tribunal Decision",
      citation: "2025 FC 100",
      source_id: "SCC_DECISIONS",
      court: "SCC",
      decision_date: "2025-01-11",
      url: "https://example.test/cases/1",
      document_url:
        "https://decisions.scc-csc.ca/scc-csc/scc-csc/en/item/123/index.do",
      docket_numbers: ["IMM-2025-100"],
      source_event_type: "updated",
      pdf_status: "available",
      pdf_reason: "document_url_trusted",
      export_allowed: true,
      export_policy_reason: "source_export_allowed",
      relevance_reason:
        "This case aligns with the matter issues and appears relevant for FC precedent support.",
      summary: "Sample summary for legal research support.",
    },
  ],
  source_status: {
    official: "ok",
    canlii: "not_used",
  },
  priority_source_status: {
    SCC_DECISIONS: "fresh",
    FC_DECISIONS: "fresh",
  },
  research_confidence: "medium",
  confidence_reasons: [
    "Official court sources returned relevant case-law results.",
    "Confidence could improve with structured intake (court, issues, anchors).",
  ],
  intake_completeness: "medium",
  intake_hints: [
    "Add target court to narrow precedents (FC/FCA/SCC).",
    "Add citation or docket anchor when available.",
  ],
};

export const SOURCE_UNAVAILABLE_ERROR = {
  error: {
    code: "SOURCE_UNAVAILABLE",
    message: "Authoritative source is unavailable.",
    trace_id: "error-trace-body",
  },
};

export const CASE_SEARCH_TOO_BROAD_ERROR = {
  error: {
    code: "VALIDATION_ERROR",
    message:
      "Case-law query is too broad. Please include specific terms such as program, issue, court, or citation.",
    trace_id: "error-trace-case-broad",
    policy_reason: "case_search_query_too_broad",
  },
};

export const UNAUTHORIZED_ERROR = {
  error: {
    code: "UNAUTHORIZED",
    message: "Missing or invalid bearer token",
    trace_id: "error-trace-auth",
  },
};

export const EXPORT_POLICY_BLOCKED_ERROR = {
  error: {
    code: "POLICY_BLOCKED",
    message: "Case export blocked by source policy (source_export_blocked_by_policy)",
    trace_id: "error-trace-export-policy",
    policy_reason: "source_export_blocked_by_policy",
  },
};
