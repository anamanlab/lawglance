export const SAMPLE_PROMPT = "What are the eligibility basics for Express Entry?";

export const CHAT_SUCCESS_RESPONSE = {
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

export const CHAT_POLICY_REFUSAL_RESPONSE = {
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

export const CASE_SEARCH_RESPONSE = {
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

export const EXPORT_APPROVAL_RESPONSE = {
  approval_token: "signed-approval-token",
  expires_in_seconds: 300,
};

export const EXPORT_PDF_FILENAME = "sample-case.pdf";
export const EXPORT_PDF_BYTES = "%PDF-1.4\n% IMMCAD test PDF\n1 0 obj\n<< /Type /Catalog >>\nendobj\n%%EOF";
