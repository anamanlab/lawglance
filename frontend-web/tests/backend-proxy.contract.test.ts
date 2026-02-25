import { afterEach, describe, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";

import { forwardPostRequest } from "@/lib/backend-proxy";
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

  it("preserves binary export responses without text decoding", async () => {
    vi.mocked(getServerRuntimeConfig).mockImplementation(() => ({
      backendBaseUrl: "https://api.example.com",
      backendBearerToken: null,
    }));

    const pdfPayload = new Uint8Array([0x25, 0x50, 0x44, 0x46, 0x2d, 0x31, 0x2e, 0x34]);
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
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
});
