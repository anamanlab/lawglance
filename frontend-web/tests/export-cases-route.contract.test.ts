import { describe, expect, it, vi } from "vitest";
import { NextRequest, NextResponse } from "next/server";

import { forwardPostRequest } from "@/lib/backend-proxy";
import { POST } from "@/app/api/export/cases/route";

vi.mock("@/lib/backend-proxy", () => ({
  forwardPostRequest: vi.fn(),
}));

describe("export cases api route", () => {
  it("forwards POST requests to backend export endpoint", async () => {
    const forwardedResponse = NextResponse.json({ ok: true }, { status: 200 });
    vi.mocked(forwardPostRequest).mockResolvedValueOnce(forwardedResponse);

    const request = new NextRequest("http://localhost/api/export/cases", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ user_approved: true }),
    });

    const response = await POST(request);

    expect(forwardPostRequest).toHaveBeenCalledWith(request, "/api/export/cases");
    expect(response).toBe(forwardedResponse);
  });
});
