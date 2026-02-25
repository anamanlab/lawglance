import { randomUUID } from "node:crypto";
import { NextRequest, NextResponse } from "next/server";

import {
  getServerRuntimeConfig,
  isHardenedRuntimeEnvironment,
} from "@/lib/server-runtime-config";

const LEGAL_DISCLAIMER =
  "IMMCAD provides Canadian immigration information only and does not provide legal advice or representation.";
const SCAFFOLD_CITATION = {
  source_id: "IRPA",
  title: "Immigration and Refugee Protection Act",
  url: "https://laws-lois.justice.gc.ca/eng/acts/I-2.5/FullText.html",
  pin: "s.11",
  snippet: "A foreign national must apply for a visa or authorization before entering Canada.",
};
const FORWARDED_RESPONSE_HEADERS = [
  "content-type",
  "content-disposition",
  "x-export-policy-reason",
] as const;

type ProxyErrorCode = "PROVIDER_ERROR" | "SOURCE_UNAVAILABLE";

function buildUpstreamUrl(baseUrl: string, path: string): string {
  const normalizedBase = baseUrl.replace(/\/+$/, "");
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return `${normalizedBase}${normalizedPath}`;
}

function buildProxyErrorResponse(
  status: number,
  message: string,
  traceId = randomUUID(),
  code: ProxyErrorCode = "PROVIDER_ERROR"
): NextResponse {
  return NextResponse.json(
    {
      error: {
        code,
        message,
        trace_id: traceId,
      },
    },
    {
      status,
      headers: { "x-trace-id": traceId },
    }
  );
}

function parseRequestPayload(rawBody: string): Record<string, unknown> | null {
  if (!rawBody.trim()) {
    return null;
  }
  try {
    const parsed = JSON.parse(rawBody) as unknown;
    if (typeof parsed === "object" && parsed !== null) {
      return parsed as Record<string, unknown>;
    }
    return null;
  } catch {
    return null;
  }
}

function buildValidationErrorResponse(traceId: string): NextResponse {
  return NextResponse.json(
    {
      error: {
        code: "VALIDATION_ERROR",
        message: "Request validation failed.",
        trace_id: traceId,
      },
    },
    {
      status: 422,
      headers: { "x-trace-id": traceId },
    }
  );
}

function buildScaffoldChatResponse(rawBody: string, traceId: string): NextResponse {
  const payload = parseRequestPayload(rawBody);
  const message = payload?.message;
  if (typeof message !== "string" || !message.trim()) {
    return buildValidationErrorResponse(traceId);
  }

  return NextResponse.json(
    {
      answer: `Scaffold response: backend service is not configured in this deployment yet. Query received: ${message.trim()}`,
      citations: [SCAFFOLD_CITATION],
      confidence: "low",
      disclaimer: LEGAL_DISCLAIMER,
      fallback_used: {
        used: true,
        provider: "scaffold",
        reason: "provider_error",
      },
    },
    {
      status: 200,
      headers: {
        "x-trace-id": traceId,
        "x-immcad-fallback": "scaffold",
      },
    }
  );
}

function buildScaffoldFallbackResponse(
  upstreamPath: string,
  rawBody: string,
  traceId: string
): NextResponse | null {
  if (upstreamPath === "/api/chat") {
    return buildScaffoldChatResponse(rawBody, traceId);
  }
  return null;
}

function buildForwardedResponseHeaders(
  upstreamResponse: Response,
  fallbackTraceId: string
): Headers {
  const responseHeaders = new Headers();
  for (const headerName of FORWARDED_RESPONSE_HEADERS) {
    const headerValue = upstreamResponse.headers.get(headerName);
    if (headerValue) {
      responseHeaders.set(headerName, headerValue);
    }
  }
  const traceId = upstreamResponse.headers.get("x-trace-id") ?? fallbackTraceId;
  responseHeaders.set("x-trace-id", traceId);
  return responseHeaders;
}

function parseBooleanEnvironmentValue(value: string | undefined): boolean {
  const normalized = value?.trim().toLowerCase();
  return (
    normalized === "1" ||
    normalized === "true" ||
    normalized === "yes" ||
    normalized === "on"
  );
}

function isScaffoldFallbackAllowed(): boolean {
  try {
    const explicitFallbackOptIn = parseBooleanEnvironmentValue(
      process.env.IMMCAD_ALLOW_PROXY_SCAFFOLD_FALLBACK
    );
    if (!explicitFallbackOptIn) {
      return false;
    }
    return !isHardenedRuntimeEnvironment();
  } catch {
    return false;
  }
}

function resolveProxyErrorCode(upstreamPath: string): ProxyErrorCode {
  if (upstreamPath === "/api/search/cases" || upstreamPath.startsWith("/api/export/cases")) {
    return "SOURCE_UNAVAILABLE";
  }
  return "PROVIDER_ERROR";
}

export async function forwardPostRequest(
  request: NextRequest,
  upstreamPath: string
): Promise<NextResponse> {
  const requestBody = await request.text();
  const traceId = randomUUID();
  let backendBaseUrl: string;
  let backendBearerToken: string | null;
  try {
    const runtimeConfig = getServerRuntimeConfig();
    backendBaseUrl = runtimeConfig.backendBaseUrl;
    backendBearerToken = runtimeConfig.backendBearerToken;
  } catch {
    if (isScaffoldFallbackAllowed()) {
      const scaffoldResponse = buildScaffoldFallbackResponse(upstreamPath, requestBody, traceId);
      if (scaffoldResponse) {
        return scaffoldResponse;
      }
    }
    const errorCode = resolveProxyErrorCode(upstreamPath);
    return buildProxyErrorResponse(
      503,
      "IMMCAD backend configuration is missing for this deployment. Set IMMCAD_API_BASE_URL (https://...) and IMMCAD_API_BEARER_TOKEN (or API_BEARER_TOKEN compatibility alias).",
      traceId,
      errorCode
    );
  }

  const upstreamUrl = buildUpstreamUrl(backendBaseUrl, upstreamPath);

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
    const payload = await upstreamResponse.arrayBuffer();
    const response = new NextResponse(payload, {
      status: upstreamResponse.status,
      headers: buildForwardedResponseHeaders(upstreamResponse, traceId),
    });
    if (!response.headers.get("content-type")) {
      response.headers.set("content-type", "application/octet-stream");
    }
    return response;
  } catch {
    if (isScaffoldFallbackAllowed()) {
      const scaffoldResponse = buildScaffoldFallbackResponse(upstreamPath, requestBody, traceId);
      if (scaffoldResponse) {
        return scaffoldResponse;
      }
    }
    const errorCode = resolveProxyErrorCode(upstreamPath);
    return buildProxyErrorResponse(
      502,
      "Unable to reach the IMMCAD backend service.",
      traceId,
      errorCode
    );
  }
}
