interface Env {
  BACKEND_ORIGIN: string;
}

const ALLOWED_PATH_PREFIXES = ["/api/", "/ops/"];
const ALLOWED_EXACT_PATHS = new Set(["/healthz"]);

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
  next.delete("trailers");
  next.delete("transfer-encoding");
  next.delete("upgrade");
  return next;
}

function normalizeOrigin(origin: string): URL {
  const parsed = new URL(origin);
  if (parsed.protocol !== "https:" && parsed.protocol !== "http:") {
    throw new Error("BACKEND_ORIGIN must be an HTTP or HTTPS URL");
  }
  return parsed;
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    if (!env.BACKEND_ORIGIN) {
      return new Response("BACKEND_ORIGIN is not configured", { status: 500 });
    }

    let origin: URL;
    try {
      origin = normalizeOrigin(env.BACKEND_ORIGIN);
    } catch (error) {
      return new Response(
        `Invalid BACKEND_ORIGIN configuration: ${(error as Error).message}`,
        { status: 500 }
      );
    }
    const incomingUrl = new URL(request.url);

    if (!isAllowedPath(incomingUrl.pathname)) {
      return new Response("Not Found", { status: 404 });
    }

    const targetUrl = new URL(incomingUrl.pathname + incomingUrl.search, origin);
    const forwardedHeaders = stripHopByHopHeaders(request.headers);
    forwardedHeaders.set("x-immcad-edge-proxy", "cloudflare-worker");
    const method = request.method.toUpperCase();
    const body = method === "GET" || method === "HEAD" ? undefined : request.body;

    const forwardedRequest = new Request(targetUrl.toString(), {
      method,
      headers: forwardedHeaders,
      body,
      redirect: "manual",
    });

    return fetch(forwardedRequest);
  },
};
