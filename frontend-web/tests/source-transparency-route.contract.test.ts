import { describe, expect, it, vi } from "vitest";
import { NextRequest, NextResponse } from "next/server";

import { forwardGetRequest } from "@/lib/backend-proxy";
import { GET } from "@/app/api/sources/transparency/route";

vi.mock("@/lib/backend-proxy", () => ({
  forwardGetRequest: vi.fn(),
}));

describe("source transparency api route", () => {
  it("forwards GET requests to backend source transparency endpoint", async () => {
    const forwardedResponse = NextResponse.json(
      { supported_courts: ["SCC", "FC", "FCA"] },
      { status: 200 }
    );
    vi.mocked(forwardGetRequest).mockResolvedValueOnce(forwardedResponse);

    const request = new NextRequest("http://localhost/api/sources/transparency", {
      method: "GET",
    });

    const response = await GET(request);

    expect(forwardGetRequest).toHaveBeenCalledWith(
      request,
      "/api/sources/transparency"
    );
    expect(response).toBe(forwardedResponse);
  });
});
