import { afterEach, describe, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";

import { forwardPostRequest } from "@/lib/backend-proxy";
import { getServerRuntimeConfig } from "@/lib/server-runtime-config";

vi.mock("@/lib/server-runtime-config", () => ({
  getServerRuntimeConfig: vi.fn(),
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
    vi.mocked(getServerRuntimeConfig).mockImplementation(() => {
      throw new Error("missing runtime config");
    });
    vi.stubEnv("NODE_ENV", "development");

    const response = await forwardPostRequest(buildRequest("/api/chat", { message: "hi" }), "/api/chat");
    const body = await response.json();

    expect(response.status).toBe(200);
    expect(response.headers.get("x-immcad-fallback")).toBe("scaffold");
    expect(body.answer).toContain("Scaffold response");
  });

  it("returns explicit provider error in production when backend config is missing", async () => {
    vi.mocked(getServerRuntimeConfig).mockImplementation(() => {
      throw new Error("missing runtime config");
    });
    vi.stubEnv("NODE_ENV", "production");

    const response = await forwardPostRequest(buildRequest("/api/chat", { message: "hi" }), "/api/chat");
    const body = await response.json();

    expect(response.status).toBe(503);
    expect(response.headers.get("x-immcad-fallback")).toBeNull();
    expect(body.error.code).toBe("PROVIDER_ERROR");
  });
});
