import { afterEach, describe, expect, it, vi } from "vitest";

import {
  createApiClient,
  type CaseExportRequestPayload,
  type ChatRequestPayload,
  type LawyerCaseResearchRequestPayload,
} from "@/lib/api-client";
import {
  CHAT_POLICY_REFUSAL_RESPONSE,
  CHAT_SUCCESS_RESPONSE,
  EXPORT_POLICY_BLOCKED_ERROR,
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

const LAWYER_RESEARCH_PAYLOAD: LawyerCaseResearchRequestPayload = {
  session_id: "session-1",
  matter_summary:
    "Federal Court appeal on procedural fairness and inadmissibility findings.",
  jurisdiction: "ca",
  court: "fc",
  limit: 5,
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
    expect(result.policyReason).toBeNull();
  });

  it("parses legacy proxy error envelope and x-immcad-trace-id fallback header", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse(
        {
          error: "PROVIDER_ERROR",
          message: "Backend origin is unavailable",
          trace_id: "trace-body-legacy",
        },
        {
          status: 502,
          headers: { "x-immcad-trace-id": "trace-header-legacy" },
        }
      )
    );

    const client = createApiClient({
      apiBaseUrl: "https://api.immcad.test",
    });
    const result = await client.sendChatMessage(REQUEST_PAYLOAD);

    expect(result.ok).toBe(false);
    if (result.ok) {
      return;
    }
    expect(result.status).toBe(502);
    expect(result.error.code).toBe("PROVIDER_ERROR");
    expect(result.error.message).toBe("Backend origin is unavailable");
    expect(result.traceId).toBe("trace-header-legacy");
    expect(result.traceIdMismatch).toBe(true);
  });

  it("uses root trace_id and policy_reason when nested error object omits them", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse(
        {
          error: {
            code: "POLICY_BLOCKED",
            message: "Export blocked by policy.",
          },
          trace_id: "trace-root-envelope",
          policy_reason: "source_export_blocked_by_policy",
        },
        {
          status: 403,
        }
      )
    );

    const client = createApiClient({
      apiBaseUrl: "https://api.immcad.test",
    });
    const result = await client.sendChatMessage(REQUEST_PAYLOAD);

    expect(result.ok).toBe(false);
    if (result.ok) {
      return;
    }
    expect(result.status).toBe(403);
    expect(result.error.code).toBe("POLICY_BLOCKED");
    expect(result.error.message).toBe("Export blocked by policy.");
    expect(result.traceId).toBe("trace-root-envelope");
    expect(result.policyReason).toBe("source_export_blocked_by_policy");
  });

  it("generates a client trace id when error responses omit trace metadata", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response("upstream html error", {
        status: 500,
        headers: { "content-type": "text/html" },
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
    expect(result.status).toBe(500);
    expect(result.error.code).toBe("UNKNOWN_ERROR");
    expect(result.traceId?.startsWith("client-")).toBe(true);
  });

  it("retries once on transient network failures before returning success", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockRejectedValueOnce(new TypeError("network down"))
      .mockResolvedValueOnce(
        jsonResponse(CHAT_SUCCESS_RESPONSE, {
          headers: { "x-trace-id": "trace-after-retry" },
        })
      );

    const client = createApiClient({
      apiBaseUrl: "https://api.immcad.test",
    });
    const result = await client.sendChatMessage(REQUEST_PAYLOAD);

    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(result.ok).toBe(true);
    if (!result.ok) {
      return;
    }
    expect(result.traceId).toBe("trace-after-retry");
    expect(result.data.answer).toBe(CHAT_SUCCESS_RESPONSE.answer);
  });

  it("returns provider error with client trace id when network fails after retry", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockRejectedValue(new TypeError("network down"));

    const client = createApiClient({
      apiBaseUrl: "https://api.immcad.test",
    });
    const result = await client.sendChatMessage(REQUEST_PAYLOAD);

    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(result.ok).toBe(false);
    if (result.ok) {
      return;
    }
    expect(result.status).toBe(0);
    expect(result.error.code).toBe("PROVIDER_ERROR");
    expect(result.traceId?.startsWith("client-")).toBe(true);
  });

  it("parses export policy reason from error envelopes", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse(EXPORT_POLICY_BLOCKED_ERROR, {
        status: 403,
        headers: { "x-trace-id": "trace-export-policy" },
      })
    );

    const client = createApiClient({
      apiBaseUrl: "https://api.immcad.test",
    });
    const result = await client.exportCasePdf(CASE_EXPORT_PAYLOAD);

    expect(result.ok).toBe(false);
    if (result.ok) {
      return;
    }
    expect(result.status).toBe(403);
    expect(result.error.code).toBe("POLICY_BLOCKED");
    expect(result.policyReason).toBe("source_export_blocked_by_policy");
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
    expect(result.policyReason).toBe("source_export_user_approval_required");
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("posts export approval requests and returns signed approval metadata", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse(
        {
          approval_token: "signed-approval-token",
          expires_at_epoch: 1_900_000_000,
        },
        {
          headers: { "x-trace-id": "trace-approval-success" },
        }
      )
    );
    const client = createApiClient({
      apiBaseUrl: "https://api.immcad.test",
      bearerToken: "token-123",
    });

    const result = await client.requestCaseExportApproval({
      source_id: "SCC_DECISIONS",
      case_id: "case-1",
      document_url: "https://decisions.scc-csc.ca/scc-csc/scc-csc/en/item/123/index.do",
      user_approved: true,
    });

    expect(result.ok).toBe(true);
    if (!result.ok) {
      return;
    }
    expect(result.traceId).toBe("trace-approval-success");
    expect(result.data.approval_token).toBe("signed-approval-token");
    expect(result.data.expires_at_epoch).toBe(1_900_000_000);
    expect(fetchMock).toHaveBeenCalledWith(
      "https://api.immcad.test/api/export/cases/approval",
      expect.objectContaining({
        method: "POST",
        headers: expect.objectContaining({
          authorization: "Bearer token-123",
        }),
      })
    );
  });

  it("fails fast when export approval payload is not explicitly user-approved", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch");
    const client = createApiClient({
      apiBaseUrl: "https://api.immcad.test",
    });

    const result = await client.requestCaseExportApproval({
      source_id: "SCC_DECISIONS",
      case_id: "case-1",
      document_url: "https://decisions.scc-csc.ca/scc-csc/scc-csc/en/item/123/index.do",
      user_approved: false,
    } as unknown as {
      source_id: string;
      case_id: string;
      document_url: string;
      user_approved: true;
    });

    expect(result.ok).toBe(false);
    if (result.ok) {
      return;
    }
    expect(result.status).toBe(422);
    expect(result.error.code).toBe("VALIDATION_ERROR");
    expect(result.policyReason).toBe("source_export_user_approval_required");
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("downloads matter package pdf and returns binary payload metadata", async () => {
    const pdfPayload = new Uint8Array([0x25, 0x50, 0x44, 0x46, 0x2d]);
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(pdfPayload, {
        status: 200,
        headers: {
          "content-type": "application/pdf",
          "content-disposition": 'attachment; filename="matter-package.pdf"',
          "x-trace-id": "trace-package-download-success",
        },
      })
    );

    const client = createApiClient({
      apiBaseUrl: "https://api.immcad.test",
      bearerToken: "token-123",
    });
    const result = await client.downloadMatterPackagePdf("matter-abc123");

    expect(result.ok).toBe(true);
    if (!result.ok) {
      return;
    }
    expect(result.traceId).toBe("trace-package-download-success");
    expect(result.data.filename).toBe("matter-package.pdf");
    expect(result.data.contentType).toBe("application/pdf");
    expect(result.data.blob.size).toBe(pdfPayload.byteLength);
    expect(fetchMock).toHaveBeenCalledWith(
      "https://api.immcad.test/api/documents/matters/matter-abc123/package/download",
      expect.objectContaining({
        method: "GET",
        headers: expect.objectContaining({
          accept: "application/pdf, application/json",
          authorization: "Bearer token-123",
        }),
      })
    );
  });

  it("fails fast when matter package download matter id is empty", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch");
    const client = createApiClient({
      apiBaseUrl: "https://api.immcad.test",
    });

    const result = await client.downloadMatterPackagePdf("   ");

    expect(result.ok).toBe(false);
    if (result.ok) {
      return;
    }
    expect(result.status).toBe(422);
    expect(result.error.code).toBe("VALIDATION_ERROR");
    expect(result.error.message).toBe("Matter ID is required.");
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("posts lawyer research requests and returns structured case support payload", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse(
        {
          matter_profile: {
            issue_tags: ["procedural_fairness", "inadmissibility"],
            target_court: "fc",
          },
          cases: [
            {
              case_id: "2026-FC-101",
              title: "Example v Canada",
              citation: "2026 FC 101",
              court: "FC",
              decision_date: "2026-02-01",
              url: "https://decisions.fct-cf.gc.ca/fc-cf/decisions/en/item/101/index.do",
              document_url:
                "https://decisions.fct-cf.gc.ca/fc-cf/decisions/en/101/1/document.do",
              docket_numbers: ["IMM-2026-101"],
              source_event_type: "updated",
              pdf_status: "available",
              relevance_reason:
                "Addresses procedural fairness in immigration refusal reasons.",
              summary:
                "The court set aside a refusal due to inadequate decision reasons.",
            },
          ],
          source_status: {
            official: "ok",
            canlii: "not_used",
          },
        },
        {
          headers: { "x-trace-id": "trace-lawyer-research" },
        }
      )
    );

    const client = createApiClient({
      apiBaseUrl: "https://api.immcad.test",
      bearerToken: "token-123",
    });
    const result = await client.researchLawyerCases(LAWYER_RESEARCH_PAYLOAD);

    expect(result.ok).toBe(true);
    if (!result.ok) {
      return;
    }
    expect(result.traceId).toBe("trace-lawyer-research");
    expect(result.data.cases).toHaveLength(1);
    expect(result.data.cases[0].pdf_status).toBe("available");
    expect(result.data.cases[0].docket_numbers).toEqual(["IMM-2026-101"]);
    expect(result.data.cases[0].source_event_type).toBe("updated");
    expect(result.data.source_status.official).toBe("ok");
    expect(fetchMock).toHaveBeenCalledWith(
      "https://api.immcad.test/api/research/lawyer-cases",
      expect.objectContaining({
        method: "POST",
        headers: expect.objectContaining({
          authorization: "Bearer token-123",
        }),
        body: JSON.stringify(LAWYER_RESEARCH_PAYLOAD),
      })
    );
  });
});
