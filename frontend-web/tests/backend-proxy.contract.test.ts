import { afterEach, describe, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";

import { forwardGetRequest, forwardPostRequest } from "@/lib/backend-proxy";
import {
  getServerRuntimeConfig,
  isHardenedRuntimeEnvironment,
} from "@/lib/server-runtime-config";

vi.mock("@/lib/server-runtime-config", () => ({
  getServerRuntimeConfig: vi.fn(),
  isHardenedRuntimeEnvironment: vi.fn(),
}));

function buildRequest(path: string, body: Record<string, unknown>): NextRequest {
  return new NextRequest(`http://localhost${path}`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
}

function buildBinaryMultipartRequest(path: string): {
  request: NextRequest;
  payload: Uint8Array;
} {
  const boundary = "----immcad-proxy-boundary";
  const encoder = new TextEncoder();
  const start = encoder.encode(
    `--${boundary}\r\n` +
      'Content-Disposition: form-data; name="files"; filename="scan.pdf"\r\n' +
      "Content-Type: application/pdf\r\n\r\n"
  );
  const binarySegment = new Uint8Array([0x25, 0x50, 0x44, 0x46, 0x00, 0xff, 0x2d, 0x31]);
  const end = encoder.encode(`\r\n--${boundary}--\r\n`);
  const payload = new Uint8Array(start.length + binarySegment.length + end.length);
  payload.set(start, 0);
  payload.set(binarySegment, start.length);
  payload.set(end, start.length + binarySegment.length);

  return {
    request: new NextRequest(`http://localhost${path}`, {
      method: "POST",
      headers: { "content-type": `multipart/form-data; boundary=${boundary}` },
      body: payload,
    }),
    payload,
  };
}

describe("backend proxy scaffold fallback behavior", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
    vi.restoreAllMocks();
  });

  it("returns scaffold fallback in non-production when backend config is missing", async () => {
    vi.stubEnv("IMMCAD_ALLOW_PROXY_SCAFFOLD_FALLBACK", "true");
    vi.mocked(getServerRuntimeConfig).mockImplementation(() => {
      throw new Error("missing runtime config");
    });
    vi.mocked(isHardenedRuntimeEnvironment).mockReturnValue(false);

    const response = await forwardPostRequest(buildRequest("/api/chat", { message: "hi" }), "/api/chat");
    const body = await response.json();

    expect(response.status).toBe(200);
    expect(response.headers.get("x-immcad-fallback")).toBe("scaffold");
    expect(body.answer).toContain("Scaffold response");
  });

  it("returns provider error in non-production when scaffold fallback opt-in is disabled", async () => {
    vi.stubEnv("IMMCAD_ALLOW_PROXY_SCAFFOLD_FALLBACK", "false");
    vi.mocked(getServerRuntimeConfig).mockImplementation(() => {
      throw new Error("missing runtime config");
    });
    vi.mocked(isHardenedRuntimeEnvironment).mockReturnValue(false);

    const response = await forwardPostRequest(buildRequest("/api/chat", { message: "hi" }), "/api/chat");
    const body = await response.json();

    expect(response.status).toBe(503);
    expect(response.headers.get("x-immcad-fallback")).toBeNull();
    expect(body.error.code).toBe("PROVIDER_ERROR");
  });

  it("returns source-unavailable error for case search when backend config is missing", async () => {
    vi.mocked(getServerRuntimeConfig).mockImplementation(() => {
      throw new Error("missing runtime config");
    });
    vi.mocked(isHardenedRuntimeEnvironment).mockReturnValue(false);

    const response = await forwardPostRequest(
      buildRequest("/api/search/cases", { query: "express entry", jurisdiction: "ca" }),
      "/api/search/cases"
    );
    const body = await response.json();

    expect(response.status).toBe(503);
    expect(response.headers.get("x-immcad-fallback")).toBeNull();
    expect(body.error.code).toBe("SOURCE_UNAVAILABLE");
  });

  it("returns source-unavailable error for lawyer research when backend config is missing", async () => {
    vi.mocked(getServerRuntimeConfig).mockImplementation(() => {
      throw new Error("missing runtime config");
    });
    vi.mocked(isHardenedRuntimeEnvironment).mockReturnValue(false);

    const response = await forwardPostRequest(
      buildRequest("/api/research/lawyer-cases", {
        session_id: "session-123456",
        matter_summary: "Federal Court appeal on procedural fairness",
      }),
      "/api/research/lawyer-cases"
    );
    const body = await response.json();

    expect(response.status).toBe(503);
    expect(response.headers.get("x-immcad-fallback")).toBeNull();
    expect(body.error.code).toBe("SOURCE_UNAVAILABLE");
  });

  it("returns explicit provider error in production when backend config is missing", async () => {
    vi.mocked(getServerRuntimeConfig).mockImplementation(() => {
      throw new Error("missing runtime config");
    });
    vi.mocked(isHardenedRuntimeEnvironment).mockReturnValue(true);

    const response = await forwardPostRequest(buildRequest("/api/chat", { message: "hi" }), "/api/chat");
    const body = await response.json();

    expect(response.status).toBe(503);
    expect(response.headers.get("x-immcad-fallback")).toBeNull();
    expect(body.error.code).toBe("PROVIDER_ERROR");
  });

  it("returns explicit provider error when hardened detection itself fails", async () => {
    vi.mocked(getServerRuntimeConfig).mockImplementation(() => {
      throw new Error("missing runtime config");
    });
    vi.mocked(isHardenedRuntimeEnvironment).mockImplementation(() => {
      throw new Error("environment mismatch");
    });

    const response = await forwardPostRequest(buildRequest("/api/chat", { message: "hi" }), "/api/chat");
    const body = await response.json();

    expect(response.status).toBe(503);
    expect(response.headers.get("x-immcad-fallback")).toBeNull();
    expect(body.error.code).toBe("PROVIDER_ERROR");
  });

  it("forwards authorization header when runtime bearer token is configured", async () => {
    vi.mocked(getServerRuntimeConfig).mockImplementation(() => ({
      backendBaseUrl: "https://api.example.com",
      backendBearerToken: "proxy-token",
      backendFallbackBaseUrl: null,
    }));

    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ answer: "ok" }), {
        status: 200,
        headers: {
          "content-type": "application/json",
          "x-trace-id": "trace-upstream",
        },
      })
    );

    const response = await forwardPostRequest(buildRequest("/api/chat", { message: "hi" }), "/api/chat");

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [upstreamUrl, init] = fetchMock.mock.calls[0]!;
    expect(upstreamUrl).toBe("https://api.example.com/api/chat");
    const forwardedHeaders = new Headers(init?.headers as HeadersInit);
    expect(forwardedHeaders.get("authorization")).toBe("Bearer proxy-token");
    expect(response.status).toBe(200);
    expect(response.headers.get("x-trace-id")).toBe("trace-upstream");
  });

  it("fails over chat requests to fallback origin when primary reports tunnel outage", async () => {
    vi.mocked(getServerRuntimeConfig).mockImplementation(() => ({
      backendBaseUrl: "https://api-primary.example.com",
      backendBearerToken: "proxy-token",
      backendFallbackBaseUrl: "https://api-fallback.example.com",
    }));

    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(
        new Response("error code: 1033", {
          status: 530,
          headers: {
            "content-type": "text/plain; charset=UTF-8",
            "x-trace-id": "trace-primary-down",
          },
        })
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ answer: "ok" }), {
          status: 200,
          headers: {
            "content-type": "application/json",
            "x-trace-id": "trace-fallback-ok",
          },
        })
      );

    const response = await forwardPostRequest(
      buildRequest("/api/chat", { message: "hi" }),
      "/api/chat"
    );
    const body = await response.json();

    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(fetchMock.mock.calls[0]?.[0]).toBe(
      "https://api-primary.example.com/api/chat"
    );
    expect(fetchMock.mock.calls[1]?.[0]).toBe(
      "https://api-fallback.example.com/api/chat"
    );
    expect(response.status).toBe(200);
    expect(response.headers.get("x-immcad-origin-fallback")).toBe("used");
    expect(body.answer).toBe("ok");
  });

  it("fails over chat requests to fallback origin when primary network call throws", async () => {
    vi.mocked(getServerRuntimeConfig).mockImplementation(() => ({
      backendBaseUrl: "https://api-primary.example.com",
      backendBearerToken: "proxy-token",
      backendFallbackBaseUrl: "https://api-fallback.example.com",
    }));

    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockRejectedValueOnce(new TypeError("network down"))
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ answer: "ok-network-fallback" }), {
          status: 200,
          headers: {
            "content-type": "application/json",
            "x-trace-id": "trace-fallback-network",
          },
        })
      );

    const response = await forwardPostRequest(
      buildRequest("/api/chat", { message: "hi" }),
      "/api/chat"
    );
    const body = await response.json();

    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(fetchMock.mock.calls[0]?.[0]).toBe(
      "https://api-primary.example.com/api/chat"
    );
    expect(fetchMock.mock.calls[1]?.[0]).toBe(
      "https://api-fallback.example.com/api/chat"
    );
    expect(response.status).toBe(200);
    expect(response.headers.get("x-immcad-origin-fallback")).toBe("used");
    expect(body.answer).toBe("ok-network-fallback");
  });

  it("fails over case-search requests to fallback origin when primary tunnel is down", async () => {
    vi.mocked(getServerRuntimeConfig).mockImplementation(() => ({
      backendBaseUrl: "https://api-primary.example.com",
      backendBearerToken: "proxy-token",
      backendFallbackBaseUrl: "https://api-fallback.example.com",
    }));

    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(
        new Response("error code: 1033", {
          status: 530,
          headers: {
            "content-type": "text/plain; charset=UTF-8",
            "x-trace-id": "trace-search-primary-down",
          },
        })
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            cases: [],
            query: "Express Entry",
            source_status: {
              source_id: "canlii",
              status: "ok",
              details: "fallback origin",
            },
          }),
          {
            status: 200,
            headers: {
              "content-type": "application/json",
              "x-trace-id": "trace-search-fallback-ok",
            },
          }
        )
      );

    const response = await forwardPostRequest(
      buildRequest("/api/search/cases", { query: "Express Entry", top_k: 1 }),
      "/api/search/cases"
    );

    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(fetchMock.mock.calls[0]?.[0]).toBe(
      "https://api-primary.example.com/api/search/cases"
    );
    expect(fetchMock.mock.calls[1]?.[0]).toBe(
      "https://api-fallback.example.com/api/search/cases"
    );
    expect(response.status).toBe(200);
    expect(response.headers.get("x-immcad-origin-fallback")).toBe("used");
  });

  it("fails over lawyer-research requests when primary tunnel is down", async () => {
    vi.mocked(getServerRuntimeConfig).mockImplementation(() => ({
      backendBaseUrl: "https://api-primary.example.com",
      backendBearerToken: "proxy-token",
      backendFallbackBaseUrl: "https://api-fallback.example.com",
    }));

    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(
        new Response("error code: 1033", {
          status: 530,
          headers: {
            "content-type": "text/plain; charset=UTF-8",
            "x-trace-id": "trace-research-primary-down",
          },
        })
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            matter_profile: {},
            cases: [],
            source_status: {},
            research_confidence: "low",
            confidence_reasons: [],
            intake_completeness: "low",
            intake_hints: [],
          }),
          {
            status: 200,
            headers: {
              "content-type": "application/json",
              "x-trace-id": "trace-research-fallback-ok",
            },
          }
        )
      );

    const response = await forwardPostRequest(
      buildRequest("/api/research/lawyer-cases", {
        session_id: "session-123456",
        matter_summary: "Federal Court procedural fairness",
      }),
      "/api/research/lawyer-cases"
    );
    const body = await response.json();

    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(fetchMock.mock.calls[0]?.[0]).toBe(
      "https://api-primary.example.com/api/research/lawyer-cases"
    );
    expect(fetchMock.mock.calls[1]?.[0]).toBe(
      "https://api-fallback.example.com/api/research/lawyer-cases"
    );
    expect(response.status).toBe(200);
    expect(response.headers.get("x-immcad-origin-fallback")).toBe("used");
    expect(body.source_status).toEqual({});
  });

  it("does not fail over export-approval requests when primary tunnel is down", async () => {
    vi.mocked(getServerRuntimeConfig).mockImplementation(() => ({
      backendBaseUrl: "https://api-primary.example.com",
      backendBearerToken: "proxy-token",
      backendFallbackBaseUrl: "https://api-fallback.example.com",
    }));

    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(
        new Response("error code: 1033", {
          status: 530,
          headers: {
            "content-type": "text/plain; charset=UTF-8",
            "x-trace-id": "trace-approval-primary-down",
          },
        })
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            approval_token: "token-fallback",
            expires_at_epoch: 1770000000,
          }),
          {
            status: 200,
            headers: {
              "content-type": "application/json",
              "x-trace-id": "trace-approval-fallback-ok",
            },
          }
        )
      );

    const response = await forwardPostRequest(
      buildRequest("/api/export/cases/approval", {
        source_id: "canlii",
        case_id: "2026-fc-001",
        document_url: "https://example.test/cases/2026-fc-001/document.pdf",
        user_approved: true,
      }),
      "/api/export/cases/approval"
    );
    const body = await response.json();

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock.mock.calls[0]?.[0]).toBe(
      "https://api-primary.example.com/api/export/cases/approval"
    );
    expect(response.status).toBe(503);
    expect(response.headers.get("x-immcad-origin-fallback")).toBeNull();
    expect(body.error.code).toBe("SOURCE_UNAVAILABLE");
    expect(body.error.message).toContain("origin tunnel");
  });

  it("preserves binary export responses without text decoding", async () => {
    vi.mocked(getServerRuntimeConfig).mockImplementation(() => ({
      backendBaseUrl: "https://api.example.com",
      backendBearerToken: null,
    }));

    const pdfPayload = new Uint8Array([0x25, 0x50, 0x44, 0x46, 0x2d, 0x31, 0x2e, 0x34]);
    const upstreamResponse = new Response(pdfPayload, {
      status: 200,
      headers: {
        "content-type": "application/pdf",
        "content-disposition": 'attachment; filename="case-export.pdf"',
        "x-trace-id": "trace-export-success",
        "x-export-policy-reason": "source_export_allowed",
      },
    });
    const upstreamArrayBufferSpy = vi.spyOn(upstreamResponse, "arrayBuffer");
    vi.spyOn(globalThis, "fetch").mockResolvedValue(upstreamResponse);

    const response = await forwardPostRequest(
      buildRequest("/api/export/cases", {
        source_id: "canlii",
        case_id: "case-1",
        document_url: "https://example.test/cases/1/document.pdf",
        user_approved: true,
      }),
      "/api/export/cases"
    );

    expect(response.status).toBe(200);
    expect(response.headers.get("content-type")).toBe("application/pdf");
    expect(response.headers.get("content-disposition")).toContain("case-export.pdf");
    expect(response.headers.get("x-export-policy-reason")).toBe("source_export_allowed");
    expect(response.headers.get("x-trace-id")).toBe("trace-export-success");
    expect(upstreamArrayBufferSpy).not.toHaveBeenCalled();

    const responseBytes = new Uint8Array(await response.arrayBuffer());
    expect(Array.from(responseBytes)).toEqual(Array.from(pdfPayload));
  });

  it("adds a proxy trace header when upstream omits x-trace-id", async () => {
    vi.mocked(getServerRuntimeConfig).mockImplementation(() => ({
      backendBaseUrl: "https://api.example.com",
      backendBearerToken: null,
    }));

    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ answer: "ok" }), {
        status: 200,
        headers: {
          "content-type": "application/json",
        },
      })
    );

    const response = await forwardPostRequest(
      buildRequest("/api/chat", { message: "hi" }),
      "/api/chat"
    );

    expect(response.status).toBe(200);
    const traceId = response.headers.get("x-trace-id");
    expect(traceId).toBeTruthy();
    expect(traceId?.length).toBeGreaterThan(10);
  });

  it("maps upstream lawyer research 404 responses to source-unavailable contract errors", async () => {
    vi.mocked(getServerRuntimeConfig).mockImplementation(() => ({
      backendBaseUrl: "https://api.example.com",
      backendBearerToken: null,
    }));

    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ detail: "Not Found" }), {
        status: 404,
        headers: {
          "content-type": "application/json",
          "x-trace-id": "trace-upstream-404",
        },
      })
    );

    const response = await forwardPostRequest(
      buildRequest("/api/research/lawyer-cases", {
        session_id: "session-123456",
        matter_summary: "Federal Court appeal on procedural fairness",
      }),
      "/api/research/lawyer-cases"
    );
    const body = await response.json();

    expect(response.status).toBe(503);
    expect(response.headers.get("x-trace-id")).toBe("trace-upstream-404");
    expect(body.error.code).toBe("SOURCE_UNAVAILABLE");
    expect(body.error.message).toContain("lawyer case research");
  });

  it("maps Cloudflare tunnel 1033 outage responses to provider errors for chat", async () => {
    vi.mocked(getServerRuntimeConfig).mockImplementation(() => ({
      backendBaseUrl: "https://api.example.com",
      backendBearerToken: null,
    }));

    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response("error code: 1033", {
        status: 530,
        headers: {
          "content-type": "text/plain",
          "x-immcad-trace-id": "trace-upstream-530",
        },
      })
    );

    const response = await forwardPostRequest(
      buildRequest("/api/chat", { message: "hi" }),
      "/api/chat"
    );
    const body = await response.json();

    expect(response.status).toBe(503);
    expect(response.headers.get("x-trace-id")).toBe("trace-upstream-530");
    expect(body.error.code).toBe("PROVIDER_ERROR");
    expect(body.error.message).toContain("origin tunnel");
  });

  it("maps Cloudflare tunnel 1033 outage responses to source-unavailable for search routes", async () => {
    vi.mocked(getServerRuntimeConfig).mockImplementation(() => ({
      backendBaseUrl: "https://api.example.com",
      backendBearerToken: null,
    }));

    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        "<title>Cloudflare Tunnel error</title><p>error code: 1033</p>",
        {
          status: 530,
          headers: {
            "content-type": "text/html; charset=UTF-8",
            "x-trace-id": "trace-upstream-530-search",
          },
        }
      )
    );

    const response = await forwardPostRequest(
      buildRequest("/api/search/cases", { query: "express entry", jurisdiction: "ca" }),
      "/api/search/cases"
    );
    const body = await response.json();

    expect(response.status).toBe(503);
    expect(response.headers.get("x-trace-id")).toBe("trace-upstream-530-search");
    expect(body.error.code).toBe("SOURCE_UNAVAILABLE");
    expect(body.error.message).toContain("origin tunnel");
  });

  it("forwards multipart request bodies without text decoding", async () => {
    vi.mocked(getServerRuntimeConfig).mockImplementation(() => ({
      backendBaseUrl: "https://api.example.com",
      backendBearerToken: null,
    }));

    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ matter_id: "matter-1", results: [] }), {
        status: 200,
        headers: {
          "content-type": "application/json",
          "x-trace-id": "trace-documents-upstream",
        },
      })
    );

    const { request, payload } = buildBinaryMultipartRequest("/api/documents/intake");
    const response = await forwardPostRequest(request, "/api/documents/intake");

    expect(response.status).toBe(200);
    expect(fetchMock).toHaveBeenCalledTimes(1);

    const [, init] = fetchMock.mock.calls[0]!;
    const forwardedBody = init?.body;
    const forwardedBytes = new Uint8Array(await new Response(forwardedBody as BodyInit).arrayBuffer());
    expect(Array.from(forwardedBytes)).toEqual(Array.from(payload));
  });

  it("does not buffer non-chat multipart requests via request.arrayBuffer", async () => {
    vi.mocked(getServerRuntimeConfig).mockImplementation(() => ({
      backendBaseUrl: "https://api.example.com",
      backendBearerToken: null,
    }));

    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ matter_id: "matter-1", results: [] }), {
        status: 200,
        headers: {
          "content-type": "application/json",
          "x-trace-id": "trace-documents-upstream",
        },
      })
    );

    const { request } = buildBinaryMultipartRequest("/api/documents/intake");
    const arrayBufferSpy = vi.spyOn(request, "arrayBuffer");
    const response = await forwardPostRequest(request, "/api/documents/intake");

    expect(response.status).toBe(200);
    expect(arrayBufferSpy).not.toHaveBeenCalled();
  });

  it("skips TextDecoder fallback decoding for non-chat multipart uploads", async () => {
    vi.mocked(getServerRuntimeConfig).mockImplementation(() => ({
      backendBaseUrl: "https://api.example.com",
      backendBearerToken: null,
    }));
    const decodeSpy = vi.spyOn(TextDecoder.prototype, "decode");

    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ matter_id: "matter-1", results: [] }), {
        status: 200,
        headers: {
          "content-type": "application/json",
          "x-trace-id": "trace-documents-upstream",
        },
      })
    );

    const { request, payload } = buildBinaryMultipartRequest("/api/documents/intake");
    const response = await forwardPostRequest(request, "/api/documents/intake");

    expect(response.status).toBe(200);
    const multipartPayloadWasDecoded = decodeSpy.mock.calls.some(([input]) => {
      if (input === undefined || input === null) {
        return false;
      }
      const view =
        input instanceof Uint8Array
          ? input
          : input instanceof ArrayBuffer
            ? new Uint8Array(input)
            : ArrayBuffer.isView(input)
              ? new Uint8Array(input.buffer, input.byteOffset, input.byteLength)
              : null;
      if (!view || view.length !== payload.length) {
        return false;
      }
      return view.every((byte, index) => byte === payload[index]);
    });
    expect(multipartPayloadWasDecoded).toBe(false);
  });

  it("forwards GET requests to readiness-style upstream paths", async () => {
    vi.mocked(getServerRuntimeConfig).mockImplementation(() => ({
      backendBaseUrl: "https://api.example.com",
      backendBearerToken: "proxy-token",
    }));

    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ is_ready: false }), {
        status: 200,
        headers: {
          "content-type": "application/json",
          "x-trace-id": "trace-doc-readiness",
        },
      })
    );

    const request = new NextRequest(
      "http://localhost/api/documents/matters/matter-abc/readiness",
      { method: "GET" }
    );
    const response = await forwardGetRequest(
      request,
      "/api/documents/matters/matter-abc/readiness"
    );

    expect(response.status).toBe(200);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [upstreamUrl, init] = fetchMock.mock.calls[0]!;
    expect(upstreamUrl).toBe("https://api.example.com/api/documents/matters/matter-abc/readiness");
    expect(init?.method).toBe("GET");
    expect(init?.body).toBeUndefined();
    const forwardedHeaders = new Headers(init?.headers as HeadersInit);
    expect(forwardedHeaders.get("authorization")).toBe("Bearer proxy-token");
  });

  it("forwards client identity headers for upstream matter scoping", async () => {
    vi.mocked(getServerRuntimeConfig).mockImplementation(() => ({
      backendBaseUrl: "https://api.example.com",
      backendBearerToken: null,
    }));

    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ is_ready: false }), {
        status: 200,
        headers: {
          "content-type": "application/json",
          "x-trace-id": "trace-doc-readiness",
        },
      })
    );

    const request = new NextRequest(
      "http://localhost/api/documents/matters/matter-abc/readiness",
      {
        method: "GET",
        headers: {
          "x-real-ip": "203.0.113.10",
          "x-forwarded-for": "203.0.113.10, 10.0.0.2",
          "true-client-ip": "203.0.113.10",
        },
      }
    );
    const response = await forwardGetRequest(
      request,
      "/api/documents/matters/matter-abc/readiness"
    );

    expect(response.status).toBe(200);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [, init] = fetchMock.mock.calls[0]!;
    const forwardedHeaders = new Headers(init?.headers as HeadersInit);
    expect(forwardedHeaders.get("x-real-ip")).toBe("203.0.113.10");
    expect(forwardedHeaders.get("x-forwarded-for")).toBe("203.0.113.10, 10.0.0.2");
    expect(forwardedHeaders.get("true-client-ip")).toBe("203.0.113.10");
    expect(forwardedHeaders.get("cf-connecting-ip")).toBeNull();
  });

  it("forwards protocol and Cloudflare client headers for document middleware checks", async () => {
    vi.mocked(getServerRuntimeConfig).mockImplementation(() => ({
      backendBaseUrl: "https://api.example.com",
      backendBearerToken: null,
    }));

    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ supported_profiles_by_forum: {}, unsupported_profile_families: [] }), {
        status: 200,
        headers: {
          "content-type": "application/json",
          "x-trace-id": "trace-doc-support-matrix",
        },
      })
    );

    const request = new NextRequest(
      "https://immcad.arkiteto.dpdns.org/api/documents/support-matrix",
      {
        method: "GET",
        headers: {
          "cf-connecting-ip": "203.0.113.15",
        },
      }
    );
    const response = await forwardGetRequest(request, "/api/documents/support-matrix");

    expect(response.status).toBe(200);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [, init] = fetchMock.mock.calls[0]!;
    const forwardedHeaders = new Headers(init?.headers as HeadersInit);
    expect(forwardedHeaders.get("x-forwarded-proto")).toBe("https");
    expect(forwardedHeaders.get("x-forwarded-host")).toBe("immcad.arkiteto.dpdns.org");
    expect(forwardedHeaders.get("cf-connecting-ip")).toBe("203.0.113.15");
  });
});
