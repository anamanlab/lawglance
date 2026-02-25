import { afterEach, describe, expect, it, vi } from "vitest";

import {
  createApiClient,
  type CaseExportRequestPayload,
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

const CASE_EXPORT_PAYLOAD: CaseExportRequestPayload = {
  source_id: "canlii",
  case_id: "case-1",
  document_url: "https://example.test/cases/1/document.pdf",
  format: "pdf",
  user_approved: true,
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

  it("posts approved case export requests and returns binary payload metadata", async () => {
    const pdfPayload = new Uint8Array([0x25, 0x50, 0x44, 0x46, 0x2d]);
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(pdfPayload, {
        status: 200,
        headers: {
          "content-type": "application/pdf",
          "content-disposition": 'attachment; filename="case-export.pdf"',
          "x-trace-id": "trace-export-success",
          "x-export-policy-reason": "source_export_allowed",
        },
      })
    );

    const client = createApiClient({
      apiBaseUrl: "https://api.immcad.test",
      bearerToken: "token-123",
    });
    const result = await client.exportCasePdf(CASE_EXPORT_PAYLOAD);

    expect(result.ok).toBe(true);
    if (!result.ok) {
      return;
    }
    expect(result.traceId).toBe("trace-export-success");
    expect(result.data.filename).toBe("case-export.pdf");
    expect(result.data.contentType).toBe("application/pdf");
    expect(result.data.policyReason).toBe("source_export_allowed");
    expect(result.data.blob.size).toBe(pdfPayload.byteLength);
    expect(fetchMock).toHaveBeenCalledWith(
      "https://api.immcad.test/api/export/cases",
      expect.objectContaining({
        method: "POST",
        headers: expect.objectContaining({
          accept: "application/pdf, application/json",
          authorization: "Bearer token-123",
        }),
        body: JSON.stringify(CASE_EXPORT_PAYLOAD),
      })
    );
  });

  it("fails fast when export payload is not explicitly user-approved", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch");
    const client = createApiClient({
      apiBaseUrl: "https://api.immcad.test",
    });

    const result = await client.exportCasePdf({
      ...CASE_EXPORT_PAYLOAD,
      user_approved: false,
    } as unknown as CaseExportRequestPayload);

    expect(result.ok).toBe(false);
    if (result.ok) {
      return;
    }
    expect(result.status).toBe(422);
    expect(result.error.code).toBe("VALIDATION_ERROR");
    expect(fetchMock).not.toHaveBeenCalled();
  });
});
