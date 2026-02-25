export type ChatRequestPayload = {
  session_id: string;
  message: string;
  locale?: string;
  mode?: string;
};

export type ChatCitation = {
  source_id: string;
  title: string;
  url: string;
  pin: string;
  snippet: string;
};

export type FallbackUsed = {
  used: boolean;
  provider: string | null;
  reason: "timeout" | "rate_limit" | "policy_block" | "provider_error" | null;
};

export type ChatResponsePayload = {
  answer: string;
  citations: ChatCitation[];
  confidence: "low" | "medium" | "high";
  disclaimer: string;
  fallback_used: FallbackUsed;
};

export type CaseSearchRequestPayload = {
  query: string;
  jurisdiction?: string;
  court?: string;
  limit?: number;
};

export type CaseSearchResult = {
  case_id: string;
  title: string;
  citation: string;
  decision_date: string;
  url: string;
  source_id?: string | null;
  document_url?: string | null;
};

export type CaseSearchResponsePayload = {
  results: CaseSearchResult[];
};

export type CaseExportRequestPayload = {
  source_id: string;
  case_id: string;
  document_url: string;
  format?: "pdf";
  user_approved: true;
};

export type CaseExportResponsePayload = {
  blob: Blob;
  filename: string | null;
  contentType: string;
  policyReason: string | null;
};

export type ApiErrorCode =
  | "UNAUTHORIZED"
  | "VALIDATION_ERROR"
  | "PROVIDER_ERROR"
  | "SOURCE_UNAVAILABLE"
  | "POLICY_BLOCKED"
  | "RATE_LIMITED"
  | "UNKNOWN_ERROR";

export type ApiError = {
  code: ApiErrorCode;
  message: string;
};

export type ApiSuccess<TPayload> = {
  ok: true;
  status: number;
  traceId: string | null;
  data: TPayload;
};

export type ApiFailure = {
  ok: false;
  status: number;
  traceId: string | null;
  traceIdMismatch: boolean;
  error: ApiError;
};

export type ApiResult<TPayload> = ApiSuccess<TPayload> | ApiFailure;

type ParsedErrorEnvelope = {
  code: ApiErrorCode;
  message: string;
  traceId: string | null;
};

type ApiClientOptions = {
  apiBaseUrl: string;
  bearerToken?: string | null;
};

const DEFAULT_ERROR_MESSAGE = "Unable to complete the request. Please try again.";
const REQUEST_HEADERS: Record<string, string> = {
  accept: "application/json",
  "content-type": "application/json"
};
const PDF_ACCEPT_HEADER = "application/pdf, application/json";

function normalizeTraceId(value: string | null | undefined): string | null {
  const trimmedValue = value?.trim();
  return trimmedValue ? trimmedValue : null;
}

function toApiErrorCode(value: unknown): ApiErrorCode {
  if (typeof value !== "string") {
    return "UNKNOWN_ERROR";
  }

  switch (value) {
    case "UNAUTHORIZED":
    case "VALIDATION_ERROR":
    case "PROVIDER_ERROR":
    case "SOURCE_UNAVAILABLE":
    case "POLICY_BLOCKED":
    case "RATE_LIMITED":
      return value;
    default:
      return "UNKNOWN_ERROR";
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function parseErrorEnvelope(payload: unknown): ParsedErrorEnvelope | null {
  if (!isRecord(payload)) {
    return null;
  }

  const errorField = payload.error;
  if (!isRecord(errorField)) {
    return null;
  }

  const message = typeof errorField.message === "string" ? errorField.message : DEFAULT_ERROR_MESSAGE;
  return {
    code: toApiErrorCode(errorField.code),
    message,
    traceId: normalizeTraceId(
      typeof errorField.trace_id === "string" ? errorField.trace_id : null
    ),
  };
}

function buildApiUrl(apiBaseUrl: string, path: string): string {
  const normalizedBaseUrl = apiBaseUrl.trim().replace(/\/+$/, "");
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;

  if (!normalizedBaseUrl || normalizedBaseUrl === "/") {
    return `/api${normalizedPath}`;
  }
  if (normalizedBaseUrl.endsWith("/api")) {
    return `${normalizedBaseUrl}${normalizedPath}`;
  }
  return `${normalizedBaseUrl}/api${normalizedPath}`;
}

function buildRequestHeaders(bearerToken?: string | null): Record<string, string> {
  return buildRequestHeadersWithOverrides(bearerToken);
}

function buildRequestHeadersWithOverrides(
  bearerToken?: string | null,
  overrides?: Record<string, string>
): Record<string, string> {
  const headers: Record<string, string> = {
    ...REQUEST_HEADERS,
    ...overrides,
  };
  if (bearerToken) {
    headers.authorization = `Bearer ${bearerToken}`;
  }
  return headers;
}

async function parseResponseBody(response: Response): Promise<unknown> {
  const responseText = await response.text();
  if (!responseText) {
    return null;
  }
  try {
    return JSON.parse(responseText) as unknown;
  } catch {
    return null;
  }
}

function buildFallbackError(status: number): ApiError {
  if (status === 401) {
    return {
      code: "UNAUTHORIZED",
      message: "Missing or invalid API bearer token.",
    };
  }
  if (status === 422) {
    return {
      code: "VALIDATION_ERROR",
      message: "Request validation failed. Check the submitted payload and try again.",
    };
  }
  return {
    code: "UNKNOWN_ERROR",
    message: DEFAULT_ERROR_MESSAGE,
  };
}

async function postJson<TPayload>(
  options: ApiClientOptions,
  path: string,
  payload: unknown
): Promise<ApiResult<TPayload>> {
  const requestUrl = buildApiUrl(options.apiBaseUrl, path);

  try {
    const response = await fetch(requestUrl, {
      method: "POST",
      headers: buildRequestHeaders(options.bearerToken),
      body: JSON.stringify(payload),
      cache: "no-store",
    });
    const headerTraceId = normalizeTraceId(response.headers.get("x-trace-id"));
    const responseBody = await parseResponseBody(response);

    if (response.ok) {
      return {
        ok: true,
        status: response.status,
        traceId: headerTraceId,
        data: responseBody as TPayload,
      };
    }

    const parsedError = parseErrorEnvelope(responseBody);
    const bodyTraceId = parsedError?.traceId ?? null;
    const traceIdMismatch =
      Boolean(headerTraceId) && Boolean(bodyTraceId) && headerTraceId !== bodyTraceId;

    return {
      ok: false,
      status: response.status,
      traceId: headerTraceId ?? bodyTraceId,
      traceIdMismatch,
      error: parsedError
        ? {
            code: parsedError.code,
            message: parsedError.message,
          }
        : buildFallbackError(response.status),
    };
  } catch {
    return {
      ok: false,
      status: 0,
      traceId: null,
      traceIdMismatch: false,
      error: {
        code: "PROVIDER_ERROR",
        message: "Unable to reach the IMMCAD API endpoint.",
      },
    };
  }
}

function parseContentDispositionFilename(value: string | null): string | null {
  if (!value) {
    return null;
  }

  const utf8Match = value.match(/filename\*=UTF-8''([^;]+)/i);
  if (utf8Match?.[1]) {
    try {
      const decoded = decodeURIComponent(utf8Match[1].trim()).replace(/^"(.*)"$/, "$1");
      return decoded || null;
    } catch {
      // Fallback to legacy filename parsing below.
    }
  }

  const quotedMatch = value.match(/filename="([^"]+)"/i);
  if (quotedMatch?.[1]) {
    return quotedMatch[1].trim() || null;
  }

  const bareMatch = value.match(/filename=([^;]+)/i);
  if (bareMatch?.[1]) {
    return bareMatch[1].trim().replace(/^"(.*)"$/, "$1") || null;
  }

  return null;
}

async function postCaseExport(
  options: ApiClientOptions,
  payload: CaseExportRequestPayload
): Promise<ApiResult<CaseExportResponsePayload>> {
  if (payload.user_approved !== true) {
    return {
      ok: false,
      status: 422,
      traceId: null,
      traceIdMismatch: false,
      error: {
        code: "VALIDATION_ERROR",
        message: "Case export requires explicit user approval before download.",
      },
    };
  }

  const requestUrl = buildApiUrl(options.apiBaseUrl, "/export/cases");
  try {
    const response = await fetch(requestUrl, {
      method: "POST",
      headers: buildRequestHeadersWithOverrides(options.bearerToken, {
        accept: PDF_ACCEPT_HEADER,
      }),
      body: JSON.stringify(payload),
      cache: "no-store",
    });
    const headerTraceId = normalizeTraceId(response.headers.get("x-trace-id"));

    if (response.ok) {
      const exportBlob = await response.blob();
      return {
        ok: true,
        status: response.status,
        traceId: headerTraceId,
        data: {
          blob: exportBlob,
          filename: parseContentDispositionFilename(response.headers.get("content-disposition")),
          contentType: response.headers.get("content-type") ?? "application/pdf",
          policyReason: normalizeTraceId(response.headers.get("x-export-policy-reason")),
        },
      };
    }

    const responseBody = await parseResponseBody(response);
    const parsedError = parseErrorEnvelope(responseBody);
    const bodyTraceId = parsedError?.traceId ?? null;
    const traceIdMismatch =
      Boolean(headerTraceId) && Boolean(bodyTraceId) && headerTraceId !== bodyTraceId;

    return {
      ok: false,
      status: response.status,
      traceId: headerTraceId ?? bodyTraceId,
      traceIdMismatch,
      error: parsedError
        ? {
            code: parsedError.code,
            message: parsedError.message,
          }
        : buildFallbackError(response.status),
    };
  } catch {
    return {
      ok: false,
      status: 0,
      traceId: null,
      traceIdMismatch: false,
      error: {
        code: "PROVIDER_ERROR",
        message: "Unable to reach the IMMCAD API endpoint.",
      },
    };
  }
}

export function createApiClient(options: ApiClientOptions) {
  return {
    sendChatMessage(
      payload: ChatRequestPayload
    ): Promise<ApiResult<ChatResponsePayload>> {
      return postJson<ChatResponsePayload>(options, "/chat", payload);
    },
    searchCases(
      payload: CaseSearchRequestPayload
    ): Promise<ApiResult<CaseSearchResponsePayload>> {
      return postJson<CaseSearchResponsePayload>(options, "/search/cases", payload);
    },
    exportCasePdf(
      payload: CaseExportRequestPayload
    ): Promise<ApiResult<CaseExportResponsePayload>> {
      return postCaseExport(options, payload);
    },
  };
}
