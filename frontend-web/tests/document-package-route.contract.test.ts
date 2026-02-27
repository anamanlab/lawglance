import { describe, expect, it, vi } from "vitest";
import { NextRequest, NextResponse } from "next/server";

import { forwardPostRequest } from "@/lib/backend-proxy";
import { POST } from "@/app/api/documents/matters/[matterId]/package/route";

vi.mock("@/lib/backend-proxy", () => ({
  forwardPostRequest: vi.fn(),
}));

describe("document package api route", () => {
  it("forwards POST requests to backend document package endpoint", async () => {
    const forwardedResponse = NextResponse.json({ ok: true }, { status: 200 });
    vi.mocked(forwardPostRequest).mockResolvedValueOnce(forwardedResponse);

    const request = new NextRequest(
      "http://localhost/api/documents/matters/matter-abc123/package",
      { method: "POST" }
    );

    const response = await POST(request, { params: { matterId: "matter-abc123" } });

    expect(forwardPostRequest).toHaveBeenCalledWith(
      request,
      "/api/documents/matters/matter-abc123/package"
    );
    expect(response).toBe(forwardedResponse);
  });
});
