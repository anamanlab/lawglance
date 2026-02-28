import type { Page } from "@playwright/test";

import {
  CASE_SEARCH_RESPONSE,
  CHAT_SUCCESS_RESPONSE,
} from "../fixtures/chat-data";

type JsonBody = Record<string, unknown>;

type StubOptions = {
  chatResponse?: JsonBody;
  caseSearchResponse?: JsonBody;
  lawyerResearchResponse?: JsonBody;
  chatStatus?: number;
  caseSearchStatus?: number;
  lawyerResearchStatus?: number;
};

export type ChatApiRecorder = {
  chatRequestCount: () => number;
  caseSearchRequestCount: () => number;
  lastChatMessage: () => string | null;
  lastCaseSearchQuery: () => string | null;
};

function toJsonBody(value: unknown): JsonBody | null {
  return typeof value === "object" && value !== null
    ? (value as JsonBody)
    : null;
}

function readStringField(body: JsonBody | null, key: string): string | null {
  const value = body?.[key];
  return typeof value === "string" ? value : null;
}

export async function installChatApiStubs(
  page: Page,
  options: StubOptions = {}
): Promise<ChatApiRecorder> {
  let chatCalls = 0;
  let caseSearchCalls = 0;
  let lastChatMessage: string | null = null;
  let lastCaseSearchQuery: string | null = null;

  const chatResponse = options.chatResponse ?? CHAT_SUCCESS_RESPONSE;
  const caseSearchResponse = options.caseSearchResponse ?? CASE_SEARCH_RESPONSE;
  const lawyerResearchResponse =
    options.lawyerResearchResponse ??
    {
      matter_profile: {
        objective: "support_precedent",
        target_court: "fct",
      },
      cases: CASE_SEARCH_RESPONSE.results.map((result) => ({
        case_id: result.case_id,
        title: result.title,
        citation: result.citation,
        source_id: result.source_id,
        court: "FC",
        decision_date: result.decision_date,
        url: result.url,
        document_url: result.document_url,
        pdf_status: "available",
        export_allowed: result.export_allowed ?? true,
        export_policy_reason: result.export_policy_reason ?? "source_export_allowed",
        relevance_reason: "Sample relevance rationale for e2e validation.",
      })),
      source_status: {
        official: "available",
        canlii: "available",
      },
      priority_source_status: {
        SCC_DECISIONS: "fresh",
        FC_DECISIONS: "fresh",
      },
      research_confidence: "high",
      confidence_reasons: ["source alignment"],
      intake_completeness: "medium",
      intake_hints: [],
    };

  await page.route("**/api/chat", async (route) => {
    chatCalls += 1;
    const requestBody = toJsonBody(route.request().postDataJSON());
    lastChatMessage = readStringField(requestBody, "message");

    await route.fulfill({
      status: options.chatStatus ?? 200,
      headers: {
        "content-type": "application/json",
        "x-trace-id": "trace-chat-e2e",
      },
      body: JSON.stringify(chatResponse),
    });
  });

  await page.route("**/api/search/cases", async (route) => {
    caseSearchCalls += 1;
    const requestBody = toJsonBody(route.request().postDataJSON());
    lastCaseSearchQuery = readStringField(requestBody, "query");

    await route.fulfill({
      status: options.caseSearchStatus ?? 200,
      headers: {
        "content-type": "application/json",
        "x-trace-id": "trace-cases-e2e",
      },
      body: JSON.stringify(caseSearchResponse),
    });
  });

  await page.route("**/api/research/lawyer-cases", async (route) => {
    caseSearchCalls += 1;
    const requestBody = toJsonBody(route.request().postDataJSON());
    lastCaseSearchQuery =
      readStringField(requestBody, "matter_summary") ??
      readStringField(requestBody, "query");

    await route.fulfill({
      status: options.lawyerResearchStatus ?? 200,
      headers: {
        "content-type": "application/json",
        "x-trace-id": "trace-lawyer-cases-e2e",
      },
      body: JSON.stringify(lawyerResearchResponse),
    });
  });

  return {
    chatRequestCount: () => chatCalls,
    caseSearchRequestCount: () => caseSearchCalls,
    lastChatMessage: () => lastChatMessage,
    lastCaseSearchQuery: () => lastCaseSearchQuery,
  };
}
