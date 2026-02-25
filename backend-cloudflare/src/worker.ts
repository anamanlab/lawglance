interface Env {
  BACKEND_ORIGIN: string;
  BACKEND_REQUEST_TIMEOUT_MS?: string;
  BACKEND_RETRY_ATTEMPTS?: string;
}

const ALLOWED_PATH_PREFIXES = ["/api/", "/ops/"];
const ALLOWED_EXACT_PATHS = new Set(["/healthz"]);
const RETRYABLE_METHODS = new Set(["GET", "HEAD"]);
const RETRYABLE_STATUS_CODES = new Set([502, 503, 504]);
const DEFAULT_REQUEST_TIMEOUT_MS = 15_000;
const MIN_REQUEST_TIMEOUT_MS = 1_000;
const MAX_REQUEST_TIMEOUT_MS = 60_000;
const DEFAULT_RETRY_ATTEMPTS = 1;
const MIN_RETRY_ATTEMPTS = 0;
const MAX_RETRY_ATTEMPTS = 2;
type ProxyErrorCode =
  | "VALIDATION_ERROR"
  | "PROVIDER_ERROR"
  | "SOURCE_UNAVAILABLE"
  | "UNKNOWN_ERROR";

function isAllowedPath(pathname: string): boolean {
  if (ALLOWED_EXACT_PATHS.has(pathname)) {
    return true;
  }
  return ALLOWED_PATH_PREFIXES.some((prefix) => pathname.startsWith(prefix));
}

function stripHopByHopHeaders(headers: Headers): Headers {
  const next = new Headers(headers);
  // Hop-by-hop headers should not be forwarded by intermediaries.
  next.delete("connection");
  next.delete("keep-alive");
  next.delete("proxy-authenticate");
  next.delete("proxy-authorization");
  next.delete("te");
  next.delete("trailer");
  next.delete("trailers");
  next.delete("transfer-encoding");
  next.delete("upgrade");
  return next;
}

function parseIntegerSetting(
  raw: string | undefined,
  fallback: number,
  min: number,
  max: number
): number {
  const parsed = raw ? Number.parseInt(raw, 10) : Number.NaN;
  if (!Number.isFinite(parsed)) {
    return fallback;
  }
  return Math.min(max, Math.max(min, parsed));
}

function isRetryableMethod(method: string): boolean {
  return RETRYABLE_METHODS.has(method);
}

function normalizeOrigin(origin: string): URL {
  const parsed = new URL(origin);
  if (parsed.protocol !== "https:" && parsed.protocol !== "http:") {
    throw new Error("BACKEND_ORIGIN must be an HTTP or HTTPS URL");
  }
  return parsed;
}

function createErrorResponse(
  status: number,
  code: ProxyErrorCode,
  message: string,
  traceId: string,
  policyReason: string | null = null
): Response {
  return new Response(
    JSON.stringify({
      error: {
        code,
        message,
        trace_id: traceId,
        policy_reason: policyReason,
      },
    }),
    {
      status,
      headers: {
        "cache-control": "no-store",
        "content-type": "application/json; charset=utf-8",
        "x-immcad-edge-proxy": "cloudflare-worker",
        "x-trace-id": traceId,
        "x-immcad-trace-id": traceId,
      },
    }
  );
}

function buildForwardedHeaders(
  request: Request,
  incomingUrl: URL,
  traceId: string
): Headers {
  const forwardedHeaders = stripHopByHopHeaders(request.headers);
  forwardedHeaders.set("x-immcad-edge-proxy", "cloudflare-worker");
  forwardedHeaders.set("x-immcad-trace-id", traceId);

  if (!forwardedHeaders.has("x-request-id")) {
    forwardedHeaders.set("x-request-id", traceId);
  }

  const cfClientIp =
    request.headers.get("cf-connecting-ip") ??
    request.headers.get("true-client-ip");
  if (cfClientIp) {
    const prior = forwardedHeaders.get("x-forwarded-for");
    if (!prior) {
      forwardedHeaders.set("x-forwarded-for", cfClientIp);
    } else if (!prior.includes(cfClientIp)) {
      forwardedHeaders.set("x-forwarded-for", `${prior}, ${cfClientIp}`);
    }
  }

  forwardedHeaders.set(
    "x-forwarded-proto",
    incomingUrl.protocol.replace(":", "")
  );
  forwardedHeaders.set("x-forwarded-host", incomingUrl.host);

  return forwardedHeaders;
}

function withProxyResponseHeaders(response: Response, traceId: string): Response {
  const headers = stripHopByHopHeaders(response.headers);
  headers.set("x-immcad-edge-proxy", "cloudflare-worker");
  headers.set("x-trace-id", traceId);
  headers.set("x-immcad-trace-id", traceId);
  return new Response(response.body, {
    status: response.status,
    statusText: response.statusText,
    headers,
  });
}

async function fetchWithTimeout(
  request: Request,
  timeoutMs: number
): Promise<Response> {
  const controller = new AbortController();
  const timeoutHandle = setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetch(request, { signal: controller.signal });
  } finally {
    clearTimeout(timeoutHandle);
  }
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const traceId = request.headers.get("cf-ray") ?? crypto.randomUUID();

    if (!env.BACKEND_ORIGIN) {
      return createErrorResponse(
        500,
        "PROVIDER_ERROR",
        "BACKEND_ORIGIN is not configured",
        traceId
      );
    }

    let origin: URL;
    try {
      origin = normalizeOrigin(env.BACKEND_ORIGIN);
    } catch (error) {
      return createErrorResponse(
        500,
        "PROVIDER_ERROR",
        `Invalid BACKEND_ORIGIN configuration: ${(error as Error).message}`,
        traceId
      );
    }
    const timeoutMs = parseIntegerSetting(
      env.BACKEND_REQUEST_TIMEOUT_MS,
      DEFAULT_REQUEST_TIMEOUT_MS,
      MIN_REQUEST_TIMEOUT_MS,
      MAX_REQUEST_TIMEOUT_MS
    );
    const retryAttempts = parseIntegerSetting(
      env.BACKEND_RETRY_ATTEMPTS,
      DEFAULT_RETRY_ATTEMPTS,
      MIN_RETRY_ATTEMPTS,
      MAX_RETRY_ATTEMPTS
    );

    const incomingUrl = new URL(request.url);
    if (!isAllowedPath(incomingUrl.pathname)) {
      return createErrorResponse(
        404,
        "VALIDATION_ERROR",
        "Path is not exposed by edge proxy allowlist",
        traceId
      );
    }

    const targetUrl = new URL(incomingUrl.pathname + incomingUrl.search, origin);
    const method = request.method.toUpperCase();
    const body = method === "GET" || method === "HEAD" ? undefined : request.body;
    const maxAttempts = isRetryableMethod(method) ? retryAttempts : 0;

    let lastError: unknown = null;

    for (let attempt = 0; attempt <= maxAttempts; attempt += 1) {
      const forwardedRequest = new Request(targetUrl.toString(), {
        method,
        headers: buildForwardedHeaders(request, incomingUrl, traceId),
        body,
        redirect: "manual",
      });

      try {
        const response = await fetchWithTimeout(forwardedRequest, timeoutMs);
        if (
          attempt < maxAttempts &&
          RETRYABLE_STATUS_CODES.has(response.status) &&
          isRetryableMethod(method)
        ) {
          continue;
        }
        return withProxyResponseHeaders(response, traceId);
      } catch (error) {
        lastError = error;
        if (attempt < maxAttempts && isRetryableMethod(method)) {
          continue;
        }
      }
    }

    if (lastError instanceof DOMException && lastError.name === "AbortError") {
      return createErrorResponse(
        504,
        "PROVIDER_ERROR",
        `Backend origin timed out after ${timeoutMs}ms`,
        traceId
      );
    }

    const fallbackMessage =
      lastError instanceof Error ? lastError.message : "Unknown upstream error";
    return createErrorResponse(
      502,
      "PROVIDER_ERROR",
      `Failed to reach backend origin: ${fallbackMessage}`,
      traceId
    );
  },
};
