import { describe, expect, it, vi } from "vitest";
import { NextRequest, NextResponse } from "next/server";

import { forwardGetRequest } from "@/lib/backend-proxy";
import { GET } from "@/app/api/documents/matters/[matterId]/readiness/route";

vi.mock("@/lib/backend-proxy", () => ({
  forwardGetRequest: vi.fn(),
}));

describe("document readiness api route", () => {
  it("forwards GET requests to backend document readiness endpoint", async () => {
    const forwardedResponse = NextResponse.json({ is_ready: false }, { status: 200 });
    vi.mocked(forwardGetRequest).mockResolvedValueOnce(forwardedResponse);

    const request = new NextRequest(
      "http://localhost/api/documents/matters/matter-abc123/readiness",
      { method: "GET" }
    );

    const response = await GET(request, { params: { matterId: "matter-abc123" } });

    expect(forwardGetRequest).toHaveBeenCalledWith(
      request,
      "/api/documents/matters/matter-abc123/readiness"
    );
    expect(response).toBe(forwardedResponse);
  });
});
