import { describe, expect, it, vi } from "vitest";
import { NextRequest, NextResponse } from "next/server";

import { forwardPostRequest } from "@/lib/backend-proxy";
import { POST } from "@/app/api/documents/intake/route";

vi.mock("@/lib/backend-proxy", () => ({
  forwardPostRequest: vi.fn(),
}));

describe("documents intake api route", () => {
  it("forwards POST requests to backend documents intake endpoint", async () => {
    const forwardedResponse = NextResponse.json({ ok: true }, { status: 200 });
    vi.mocked(forwardPostRequest).mockResolvedValueOnce(forwardedResponse);

    const request = new NextRequest("http://localhost/api/documents/intake", {
      method: "POST",
      headers: { "content-type": "multipart/form-data; boundary=----test" },
      body: new Uint8Array([0x25, 0x50, 0x44, 0x46]),
    });

    const response = await POST(request);

    expect(forwardPostRequest).toHaveBeenCalledWith(request, "/api/documents/intake");
    expect(response).toBe(forwardedResponse);
  });
});
