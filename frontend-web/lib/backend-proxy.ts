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
const FORWARDED_CLIENT_ID_HEADERS = [
  "x-real-ip",
  "x-forwarded-for",
  "true-client-ip",
  "cf-connecting-ip",
] as const;
const FALLBACK_ORIGIN_RETRY_PATHS = new Set([
  "/api/chat",
  "/api/search/cases",
  "/api/research/lawyer-cases",
  "/api/export/cases",
]);

type ProxyErrorCode = "PROVIDER_ERROR" | "SOURCE_UNAVAILABLE";
type ServiceBindingFetcher = {
  fetch: (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>;
};

function buildUpstreamUrl(baseUrl: string, path: string): string {
  const normalizedBase = baseUrl.replace(/\/+$/, "");
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return `${normalizedBase}${normalizedPath}`;
}

async function resolveBackendServiceBinding(): Promise<ServiceBindingFetcher | null> {
  try {
    const cloudflareModule = await import("@opennextjs/cloudflare");
    const context = await cloudflareModule.getCloudflareContext({ async: true });
    const candidateBinding = (context?.env as Record<string, unknown> | undefined)
      ?.IMMCAD_BACKEND;
    if (
      candidateBinding &&
      typeof (candidateBinding as ServiceBindingFetcher).fetch === "function"
    ) {
      return candidateBinding as ServiceBindingFetcher;
    }
  } catch {
    return null;
  }
  return null;
}

function buildProxyErrorResponse(
  status: number,
  message: string,
  traceId: string = randomUUID(),
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

function shouldCaptureFallbackRequestBody(upstreamPath: string): boolean {
  return FALLBACK_ORIGIN_RETRY_PATHS.has(upstreamPath);
}

function canUseFallbackOrigin(upstreamPath: string): boolean {
  return FALLBACK_ORIGIN_RETRY_PATHS.has(upstreamPath);
}

function buildForwardedResponseHeaders(
  upstreamResponse: Response,
  fallbackTraceId: string,
  usedFallbackOrigin: boolean = false
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
  if (usedFallbackOrigin) {
    responseHeaders.set("x-immcad-origin-fallback", "used");
  }
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
  if (
    upstreamPath === "/api/search/cases" ||
    upstreamPath === "/api/research/lawyer-cases" ||
    upstreamPath.startsWith("/api/export/cases") ||
    upstreamPath === "/api/sources/transparency"
  ) {
    return "SOURCE_UNAVAILABLE";
  }
  return "PROVIDER_ERROR";
}

function mapUpstreamNotFoundResponse(
  upstreamResponse: Response,
  upstreamPath: string,
  fallbackTraceId: string
): NextResponse | null {
  if (upstreamResponse.status !== 404) {
    return null;
  }
  if (upstreamPath !== "/api/research/lawyer-cases") {
    return null;
  }
  const traceId = upstreamResponse.headers.get("x-trace-id") ?? fallbackTraceId;
  return buildProxyErrorResponse(
    503,
    "The lawyer case research service is currently unavailable.",
    traceId,
    "SOURCE_UNAVAILABLE"
  );
}

async function isCloudflareTunnelOutageResponse(
  upstreamResponse: Response
): Promise<boolean> {
  if (upstreamResponse.status !== 530) {
    return false;
  }

  const contentType = upstreamResponse.headers
    .get("content-type")
    ?.toLowerCase() ?? "";
  if (
    contentType &&
    !contentType.includes("text/html") &&
    !contentType.includes("text/plain")
  ) {
    return false;
  }

  let bodyText = "";
  try {
    bodyText = (await upstreamResponse.clone().text()).toLowerCase();
  } catch {
    return false;
  }
  return (
    bodyText.includes("error code: 1033") ||
    bodyText.includes("cloudflare tunnel error") ||
    bodyText.includes("unable to resolve it")
  );
}

async function mapCloudflareTunnelOutageResponse(
  upstreamResponse: Response,
  upstreamPath: string,
  fallbackTraceId: string
): Promise<NextResponse | null> {
  const isTunnelResolveFailure = await isCloudflareTunnelOutageResponse(
    upstreamResponse
  );
  if (!isTunnelResolveFailure) {
    return null;
  }

  const traceId =
    upstreamResponse.headers.get("x-trace-id") ??
    upstreamResponse.headers.get("x-immcad-trace-id") ??
    fallbackTraceId;
  const errorCode = resolveProxyErrorCode(upstreamPath);
  return buildProxyErrorResponse(
    503,
    "IMMCAD backend origin tunnel is temporarily unavailable. Please retry shortly.",
    traceId,
    errorCode
  );
}

function buildUpstreamRequestHeaders(
  request: NextRequest,
  options: {
    backendBearerToken: string | null;
    method: "GET" | "POST";
  }
): Headers {
  const { backendBearerToken, method } = options;
  const headers = new Headers({
    accept: request.headers.get("accept") ?? "application/json",
  });
  const requestContentType = request.headers.get("content-type");
  if (requestContentType) {
    headers.set("content-type", requestContentType);
  } else if (method === "POST") {
    headers.set("content-type", "application/json");
  }
  if (backendBearerToken) {
    headers.set("authorization", `Bearer ${backendBearerToken}`);
  }
  for (const headerName of FORWARDED_CLIENT_ID_HEADERS) {
    const headerValue = request.headers.get(headerName);
    if (headerValue) {
      headers.set(headerName, headerValue);
    }
  }
  const requestUrl = new URL(request.url);
  const forwardedProto = requestUrl.protocol.replace(":", "");
  if (forwardedProto) {
    headers.set("x-forwarded-proto", forwardedProto);
  }
  if (requestUrl.host) {
    headers.set("x-forwarded-host", requestUrl.host);
  }
  const cfVisitorHeader = request.headers.get("cf-visitor");
  if (cfVisitorHeader) {
    headers.set("cf-visitor", cfVisitorHeader);
  }
  return headers;
}

async function forwardRequest(
  request: NextRequest,
  upstreamPath: string,
  options: {
    method: "GET" | "POST";
    requestBody?: BodyInit | null;
    requestBodyTextForFallback?: string;
  }
): Promise<NextResponse> {
  const { method, requestBody = null, requestBodyTextForFallback = "" } = options;
  const traceId = randomUUID();
  let backendBaseUrl: string;
  let backendBearerToken: string | null;
  let backendFallbackBaseUrl: string | null = null;
  try {
    const runtimeConfig = getServerRuntimeConfig();
    backendBaseUrl = runtimeConfig.backendBaseUrl;
    backendBearerToken = runtimeConfig.backendBearerToken;
    backendFallbackBaseUrl = runtimeConfig.backendFallbackBaseUrl ?? null;
  } catch {
    if (isScaffoldFallbackAllowed()) {
      const scaffoldResponse = buildScaffoldFallbackResponse(
        upstreamPath,
        requestBodyTextForFallback,
        traceId
      );
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

  const backendServiceBinding = await resolveBackendServiceBinding();
  const shouldTryFallbackOrigin =
    !backendServiceBinding &&
    canUseFallbackOrigin(upstreamPath) &&
    backendFallbackBaseUrl !== null &&
    backendFallbackBaseUrl !== backendBaseUrl;
  const upstreamUrl = buildUpstreamUrl(backendBaseUrl, upstreamPath);
  const serviceBindingUpstreamUrl = buildUpstreamUrl(
    "https://immcad-backend.internal",
    upstreamPath
  );
  const fallbackUpstreamUrl = shouldTryFallbackOrigin
    ? buildUpstreamUrl(backendFallbackBaseUrl!, upstreamPath)
    : null;
  const headers = buildUpstreamRequestHeaders(request, {
    backendBearerToken,
    method,
  });

  try {
    const requestInit: RequestInit & { duplex?: "half" } = {
      method,
      headers,
      body: method === "POST" ? requestBody : undefined,
      cache: "no-store",
    };
    if (method === "POST" && requestBody instanceof ReadableStream) {
      requestInit.duplex = "half";
    }
    let usedFallbackOrigin = false;
    let upstreamResponse: Response;
    try {
      if (backendServiceBinding) {
        upstreamResponse = await backendServiceBinding.fetch(
          serviceBindingUpstreamUrl,
          requestInit
        );
      } else {
        upstreamResponse = await fetch(upstreamUrl, requestInit);
      }
    } catch (primaryError) {
      if (!fallbackUpstreamUrl) {
        throw primaryError;
      }
      upstreamResponse = await fetch(fallbackUpstreamUrl, requestInit);
      usedFallbackOrigin = true;
    }
    if (!backendServiceBinding && !usedFallbackOrigin && fallbackUpstreamUrl) {
      const primaryTunnelOutage = await isCloudflareTunnelOutageResponse(
        upstreamResponse
      );
      if (primaryTunnelOutage) {
        upstreamResponse = await fetch(fallbackUpstreamUrl, requestInit);
        usedFallbackOrigin = true;
      }
    }
    const mappedNotFoundResponse = mapUpstreamNotFoundResponse(
      upstreamResponse,
      upstreamPath,
      traceId
    );
    if (mappedNotFoundResponse) {
      if (usedFallbackOrigin) {
        mappedNotFoundResponse.headers.set("x-immcad-origin-fallback", "used");
      }
      return mappedNotFoundResponse;
    }
    const mappedTunnelOutageResponse = await mapCloudflareTunnelOutageResponse(
      upstreamResponse,
      upstreamPath,
      traceId
    );
    if (mappedTunnelOutageResponse) {
      if (usedFallbackOrigin) {
        mappedTunnelOutageResponse.headers.set("x-immcad-origin-fallback", "used");
      }
      return mappedTunnelOutageResponse;
    }
    const response = new NextResponse(upstreamResponse.body, {
      status: upstreamResponse.status,
      headers: buildForwardedResponseHeaders(
        upstreamResponse,
        traceId,
        usedFallbackOrigin
      ),
    });
    if (!response.headers.get("content-type")) {
      response.headers.set("content-type", "application/octet-stream");
    }
    return response;
  } catch {
    if (isScaffoldFallbackAllowed()) {
      const scaffoldResponse = buildScaffoldFallbackResponse(
        upstreamPath,
        requestBodyTextForFallback,
        traceId
      );
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

export async function forwardPostRequest(
  request: NextRequest,
  upstreamPath: string
): Promise<NextResponse> {
  if (shouldCaptureFallbackRequestBody(upstreamPath)) {
    const requestBodyBytes = new Uint8Array(await request.arrayBuffer());
    return forwardRequest(request, upstreamPath, {
      method: "POST",
      requestBody: requestBodyBytes,
      requestBodyTextForFallback: new TextDecoder().decode(requestBodyBytes),
    });
  }
  return forwardRequest(request, upstreamPath, {
    method: "POST",
    requestBody: request.body,
  });
}

export async function forwardGetRequest(
  request: NextRequest,
  upstreamPath: string
): Promise<NextResponse> {
  return forwardRequest(request, upstreamPath, {
    method: "GET",
  });
}
