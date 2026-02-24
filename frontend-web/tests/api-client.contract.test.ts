import { afterEach, describe, expect, it, vi } from "vitest";

import {
  createApiClient,
  type ChatRequestPayload,
} from "@/lib/api-client";
import {
  CHAT_POLICY_REFUSAL_RESPONSE,
  CHAT_SUCCESS_RESPONSE,
  SOURCE_UNAVAILABLE_ERROR,
} from "@/tests/fixtures/chat-contract-fixtures";

function jsonResponse(
  body: unknown,
  {
    status = 200,
    headers = {},
  }: {
    status?: number;
    headers?: Record<string, string>;
  } = {}
): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: {
      "content-type": "application/json",
      ...headers,
    },
  });
}

const REQUEST_PAYLOAD: ChatRequestPayload = {
  session_id: "session-1",
  message: "How does Express Entry work?",
  locale: "en-CA",
  mode: "standard",
};

describe("api client chat contract", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("returns success payload with trace id for regular chat responses", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(
        jsonResponse(CHAT_SUCCESS_RESPONSE, {
          headers: { "x-trace-id": "trace-chat-success" },
        })
      );

    const client = createApiClient({
      apiBaseUrl: "https://api.immcad.test",
      bearerToken: "token-123",
    });
    const result = await client.sendChatMessage(REQUEST_PAYLOAD);

    expect(result.ok).toBe(true);
    if (!result.ok) {
      return;
    }
    expect(result.traceId).toBe("trace-chat-success");
    expect(result.data.answer).toBe(CHAT_SUCCESS_RESPONSE.answer);
    expect(result.data.citations).toEqual(CHAT_SUCCESS_RESPONSE.citations);
    expect(fetchMock).toHaveBeenCalledWith(
      "https://api.immcad.test/api/chat",
      expect.objectContaining({
        method: "POST",
        headers: expect.objectContaining({
          authorization: "Bearer token-123",
        }),
      })
    );
  });

  it("uses proxy-safe path joining without double /api prefixes", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(
        jsonResponse(CHAT_SUCCESS_RESPONSE, {
          headers: { "x-trace-id": "trace-chat-success" },
        })
      );

    const client = createApiClient({
      apiBaseUrl: "/api",
    });
    const result = await client.sendChatMessage(REQUEST_PAYLOAD);

    expect(result.ok).toBe(true);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/chat",
      expect.objectContaining({
        method: "POST",
      })
    );
  });

  it("preserves policy refusal success envelope", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse(CHAT_POLICY_REFUSAL_RESPONSE, {
        headers: { "x-trace-id": "trace-policy-refusal" },
      })
    );

    const client = createApiClient({
      apiBaseUrl: "https://api.immcad.test",
    });
    const result = await client.sendChatMessage(REQUEST_PAYLOAD);

    expect(result.ok).toBe(true);
    if (!result.ok) {
      return;
    }
    expect(result.traceId).toBe("trace-policy-refusal");
    expect(result.data.fallback_used.reason).toBe("policy_block");
  });

  it("maps error envelope and flags trace mismatch when header/body differ", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse(SOURCE_UNAVAILABLE_ERROR, {
        status: 503,
        headers: { "x-trace-id": "trace-header" },
      })
    );

    const client = createApiClient({
      apiBaseUrl: "https://api.immcad.test",
    });
    const result = await client.sendChatMessage(REQUEST_PAYLOAD);

    expect(result.ok).toBe(false);
    if (result.ok) {
      return;
    }
    expect(result.status).toBe(503);
    expect(result.error.code).toBe("SOURCE_UNAVAILABLE");
    expect(result.error.message).toBe("Authoritative source is unavailable.");
    expect(result.traceId).toBe("trace-header");
    expect(result.traceIdMismatch).toBe(true);
  });
});
