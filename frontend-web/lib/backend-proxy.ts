import { randomUUID } from "node:crypto";
import { NextRequest, NextResponse } from "next/server";

import { getServerRuntimeConfig } from "@/lib/server-runtime-config";

function buildUpstreamUrl(baseUrl: string, path: string): string {
  const normalizedBase = baseUrl.replace(/\/+$/, "");
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return `${normalizedBase}${normalizedPath}`;
}

export async function forwardPostRequest(
  request: NextRequest,
  upstreamPath: string
): Promise<NextResponse> {
  const { backendBaseUrl, backendBearerToken } = getServerRuntimeConfig();
  const upstreamUrl = buildUpstreamUrl(backendBaseUrl, upstreamPath);
  const requestBody = await request.text();

  const headers = new Headers({
    accept: request.headers.get("accept") ?? "application/json",
    "content-type": request.headers.get("content-type") ?? "application/json",
  });
  if (backendBearerToken) {
    headers.set("authorization", `Bearer ${backendBearerToken}`);
  }

  try {
    const upstreamResponse = await fetch(upstreamUrl, {
      method: "POST",
      headers,
      body: requestBody,
      cache: "no-store",
    });
    const payload = await upstreamResponse.text();
    const traceId = upstreamResponse.headers.get("x-trace-id");
    const contentType = upstreamResponse.headers.get("content-type") ?? "application/json";

    const response = new NextResponse(payload, {
      status: upstreamResponse.status,
      headers: { "content-type": contentType },
    });
    if (traceId) {
      response.headers.set("x-trace-id", traceId);
    }
    return response;
  } catch {
    const traceId = randomUUID();
    return NextResponse.json(
      {
        error: {
          code: "PROVIDER_ERROR",
          message: "Unable to reach the IMMCAD backend service.",
          trace_id: traceId,
        },
      },
      {
        status: 502,
        headers: { "x-trace-id": traceId },
      }
    );
  }
}
