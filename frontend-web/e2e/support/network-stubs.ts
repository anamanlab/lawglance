import type { Page } from "@playwright/test";

import {
  CASE_SEARCH_RESPONSE,
  CHAT_SUCCESS_RESPONSE,
} from "../fixtures/chat-data";

type JsonBody = Record<string, unknown>;

type StubOptions = {
  chatResponse?: JsonBody;
  caseSearchResponse?: JsonBody;
  chatStatus?: number;
  caseSearchStatus?: number;
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

  return {
    chatRequestCount: () => chatCalls,
    caseSearchRequestCount: () => caseSearchCalls,
    lastChatMessage: () => lastChatMessage,
    lastCaseSearchQuery: () => lastCaseSearchQuery,
  };
}
