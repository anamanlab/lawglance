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

export type ChatResearchPreviewPayload = {
  retrieval_mode: "auto" | "manual";
  query: string;
  source_status: Record<string, string>;
  cases: LawyerCaseSupport[];
};

export type ChatResponsePayload = {
  answer: string;
  citations: ChatCitation[];
  confidence: "low" | "medium" | "high";
  disclaimer: string;
  fallback_used: FallbackUsed;
  research_preview?: ChatResearchPreviewPayload | null;
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
  export_allowed?: boolean | null;
  export_policy_reason?: string | null;
};

export type CaseSearchResponsePayload = {
  results: CaseSearchResult[];
};

export type LawyerCaseResearchRequestPayload = {
  session_id: string;
  matter_summary: string;
  jurisdiction?: string;
  court?: string;
  intake?: LawyerResearchIntakePayload;
  limit?: number;
};

export type LawyerResearchIntakePayload = {
  objective?: "support_precedent" | "distinguish_precedent" | "background_research";
  target_court?: string;
  procedural_posture?: "judicial_review" | "appeal" | "motion" | "application";
  issue_tags?: string[];
  anchor_citations?: string[];
  anchor_dockets?: string[];
  fact_keywords?: string[];
  date_from?: string;
  date_to?: string;
};

export type LawyerCaseSupport = {
  case_id: string;
  title: string;
  citation: string;
  source_id?: string | null;
  court?: string | null;
  decision_date: string;
  url: string;
  document_url?: string | null;
  pdf_status: "available" | "unavailable";
  pdf_reason?: string | null;
  export_allowed?: boolean | null;
  export_policy_reason?: string | null;
  relevance_reason: string;
  summary?: string | null;
};

export type LawyerCaseResearchResponsePayload = {
  matter_profile: Record<string, string | string[] | null>;
  cases: LawyerCaseSupport[];
  source_status: Record<string, string>;
  research_confidence: "low" | "medium" | "high";
  confidence_reasons: string[];
  intake_completeness: "low" | "medium" | "high";
  intake_hints: string[];
};

export type CaseExportRequestPayload = {
  source_id: string;
  case_id: string;
  document_url: string;
  format?: "pdf";
  user_approved: true;
  approval_token?: string | null;
};

export type CaseExportResponsePayload = {
  blob: Blob;
  filename: string | null;
  contentType: string;
  policyReason: string | null;
};

export type CaseExportApprovalRequestPayload = {
  source_id: string;
  case_id: string;
  document_url: string;
  user_approved: true;
};

export type CaseExportApprovalResponsePayload = {
  approval_token: string;
  expires_at_epoch: number;
};

export type DocumentForum =
  | "federal_court_jr"
  | "rpd"
  | "rad"
  | "iad"
  | "id";

export type DocumentIntakeRequestPayload = {
  forum: DocumentForum;
  matter_id?: string;
  files: File[];
};

export type DocumentIntakeResult = {
  file_id: string;
  original_filename: string;
  normalized_filename: string;
  classification: string | null;
  quality_status: string;
  issues: string[];
};

export type DocumentIntakeResponsePayload = {
  matter_id: string;
  forum: DocumentForum;
  results: DocumentIntakeResult[];
  blocking_issues: string[];
  warnings: string[];
};

export type MatterReadinessResponsePayload = {
  matter_id: string;
  forum: DocumentForum;
  is_ready: boolean;
  missing_required_items: string[];
  blocking_issues: string[];
  warnings: string[];
  requirement_statuses?: {
    item: string;
    status: "present" | "missing" | "warning";
    rule_scope?: "base" | "conditional";
    reason?: string | null;
  }[];
};

export type MatterPackageTocItem = {
  position: number;
  document_type: string;
  filename: string;
};

export type MatterPackageChecklistItem = {
  item: string;
  status: string;
  rule_scope?: "base" | "conditional";
  reason?: string | null;
};

export type MatterPackageResponsePayload = {
  matter_id: string;
  forum: DocumentForum;
  table_of_contents: MatterPackageTocItem[];
  disclosure_checklist: MatterPackageChecklistItem[];
  cover_letter_draft: string;
  is_ready: boolean;
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
  policyReason: string | null;
  error: ApiError;
};

export type ApiResult<TPayload> = ApiSuccess<TPayload> | ApiFailure;

type ParsedErrorEnvelope = {
  code: ApiErrorCode;
  message: string;
  traceId: string | null;
  policyReason: string | null;
};

type ApiClientOptions = {
  apiBaseUrl: string;
  bearerToken?: string | null;
};

const DEFAULT_ERROR_MESSAGE = "Unable to complete the request. Please try again.";
const REQUEST_ACCEPT_HEADERS: Record<string, string> = {
  accept: "application/json"
};
const REQUEST_HEADERS: Record<string, string> = {
  ...REQUEST_ACCEPT_HEADERS,
  "content-type": "application/json"
};
const PDF_ACCEPT_HEADER = "application/pdf, application/json";
const NETWORK_RETRY_DELAY_MS = 150;
const NETWORK_RETRY_ATTEMPTS = 2;

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

  if (typeof payload.error === "string") {
    const message =
      typeof payload.message === "string"
        ? payload.message
        : DEFAULT_ERROR_MESSAGE;
    return {
      code: toApiErrorCode(payload.error),
      message,
      traceId: normalizeTraceId(
        typeof payload.trace_id === "string" ? payload.trace_id : null
      ),
      policyReason:
        typeof payload.policy_reason === "string"
          ? normalizeTraceId(payload.policy_reason)
          : null,
    };
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
    policyReason:
      typeof errorField.policy_reason === "string"
        ? normalizeTraceId(errorField.policy_reason)
        : null,
  };
}

function getResponseTraceId(headers: Headers): string | null {
  return normalizeTraceId(
    headers.get("x-trace-id") ?? headers.get("x-immcad-trace-id")
  );
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

function buildRequestHeadersWithoutContentType(
  bearerToken?: string | null,
  overrides?: Record<string, string>
): Record<string, string> {
  const headers: Record<string, string> = {
    ...REQUEST_ACCEPT_HEADERS,
    ...overrides,
  };
  if (bearerToken) {
    headers.authorization = `Bearer ${bearerToken}`;
  }
  return headers;
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

function delay(milliseconds: number): Promise<void> {
  return new Promise((resolve) => {
    setTimeout(resolve, milliseconds);
  });
}

function buildClientTraceId(): string {
  if (
    typeof globalThis.crypto !== "undefined" &&
    typeof globalThis.crypto.randomUUID === "function"
  ) {
    return `client-${globalThis.crypto.randomUUID()}`;
  }
  return `client-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
}

async function postJsonWithRetry(
  requestUrl: string,
  headers: Record<string, string>,
  payload: unknown
): Promise<Response> {
  let lastError: unknown = null;
  for (let attempt = 1; attempt <= NETWORK_RETRY_ATTEMPTS; attempt += 1) {
    try {
      return await fetch(requestUrl, {
        method: "POST",
        headers,
        body: JSON.stringify(payload),
        cache: "no-store",
      });
    } catch (error) {
      lastError = error;
      if (attempt < NETWORK_RETRY_ATTEMPTS) {
        await delay(NETWORK_RETRY_DELAY_MS);
        continue;
      }
      throw lastError;
    }
  }
  throw lastError;
}

async function postBinaryWithRetry(
  requestUrl: string,
  headers: Record<string, string>,
  payload: unknown
): Promise<Response> {
  let lastError: unknown = null;
  for (let attempt = 1; attempt <= NETWORK_RETRY_ATTEMPTS; attempt += 1) {
    try {
      return await fetch(requestUrl, {
        method: "POST",
        headers,
        body: JSON.stringify(payload),
        cache: "no-store",
      });
    } catch (error) {
      lastError = error;
      if (attempt < NETWORK_RETRY_ATTEMPTS) {
        await delay(NETWORK_RETRY_DELAY_MS);
        continue;
      }
      throw lastError;
    }
  }
  throw lastError;
}

async function postFormDataWithRetry(
  requestUrl: string,
  headers: Record<string, string>,
  payload: FormData
): Promise<Response> {
  let lastError: unknown = null;
  for (let attempt = 1; attempt <= NETWORK_RETRY_ATTEMPTS; attempt += 1) {
    try {
      return await fetch(requestUrl, {
        method: "POST",
        headers,
        body: payload,
        cache: "no-store",
      });
    } catch (error) {
      lastError = error;
      if (attempt < NETWORK_RETRY_ATTEMPTS) {
        await delay(NETWORK_RETRY_DELAY_MS);
        continue;
      }
      throw lastError;
    }
  }
  throw lastError;
}

async function getJsonWithRetry(
  requestUrl: string,
  headers: Record<string, string>
): Promise<Response> {
  let lastError: unknown = null;
  for (let attempt = 1; attempt <= NETWORK_RETRY_ATTEMPTS; attempt += 1) {
    try {
      return await fetch(requestUrl, {
        method: "GET",
        headers,
        cache: "no-store",
      });
    } catch (error) {
      lastError = error;
      if (attempt < NETWORK_RETRY_ATTEMPTS) {
        await delay(NETWORK_RETRY_DELAY_MS);
        continue;
      }
      throw lastError;
    }
  }
  throw lastError;
}

async function postWithoutBodyWithRetry(
  requestUrl: string,
  headers: Record<string, string>
): Promise<Response> {
  let lastError: unknown = null;
  for (let attempt = 1; attempt <= NETWORK_RETRY_ATTEMPTS; attempt += 1) {
    try {
      return await fetch(requestUrl, {
        method: "POST",
        headers,
        cache: "no-store",
      });
    } catch (error) {
      lastError = error;
      if (attempt < NETWORK_RETRY_ATTEMPTS) {
        await delay(NETWORK_RETRY_DELAY_MS);
        continue;
      }
      throw lastError;
    }
  }
  throw lastError;
}

async function postJson<TPayload>(
  options: ApiClientOptions,
  path: string,
  payload: unknown
): Promise<ApiResult<TPayload>> {
  const requestUrl = buildApiUrl(options.apiBaseUrl, path);

  try {
    const response = await postJsonWithRetry(
      requestUrl,
      buildRequestHeaders(options.bearerToken),
      payload
    );
    const headerTraceId = getResponseTraceId(response.headers);
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
    const traceId = headerTraceId ?? bodyTraceId ?? buildClientTraceId();

    return {
      ok: false,
      status: response.status,
      traceId,
      traceIdMismatch,
      policyReason: parsedError?.policyReason ?? null,
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
      traceId: buildClientTraceId(),
      traceIdMismatch: false,
      policyReason: null,
      error: {
        code: "PROVIDER_ERROR",
        message: "Unable to reach the IMMCAD API endpoint.",
      },
    };
  }
}

async function postMultipart<TPayload>(
  options: ApiClientOptions,
  path: string,
  payload: FormData
): Promise<ApiResult<TPayload>> {
  const requestUrl = buildApiUrl(options.apiBaseUrl, path);

  try {
    const response = await postFormDataWithRetry(
      requestUrl,
      buildRequestHeadersWithoutContentType(options.bearerToken),
      payload
    );
    const headerTraceId = getResponseTraceId(response.headers);
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
    const traceId = headerTraceId ?? bodyTraceId ?? buildClientTraceId();

    return {
      ok: false,
      status: response.status,
      traceId,
      traceIdMismatch,
      policyReason: parsedError?.policyReason ?? null,
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
      traceId: buildClientTraceId(),
      traceIdMismatch: false,
      policyReason: null,
      error: {
        code: "PROVIDER_ERROR",
        message: "Unable to reach the IMMCAD API endpoint.",
      },
    };
  }
}

async function getJson<TPayload>(
  options: ApiClientOptions,
  path: string
): Promise<ApiResult<TPayload>> {
  const requestUrl = buildApiUrl(options.apiBaseUrl, path);

  try {
    const response = await getJsonWithRetry(
      requestUrl,
      buildRequestHeadersWithoutContentType(options.bearerToken)
    );
    const headerTraceId = getResponseTraceId(response.headers);
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
    const traceId = headerTraceId ?? bodyTraceId ?? buildClientTraceId();

    return {
      ok: false,
      status: response.status,
      traceId,
      traceIdMismatch,
      policyReason: parsedError?.policyReason ?? null,
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
      traceId: buildClientTraceId(),
      traceIdMismatch: false,
      policyReason: null,
      error: {
        code: "PROVIDER_ERROR",
        message: "Unable to reach the IMMCAD API endpoint.",
      },
    };
  }
}

async function postWithoutBody<TPayload>(
  options: ApiClientOptions,
  path: string
): Promise<ApiResult<TPayload>> {
  const requestUrl = buildApiUrl(options.apiBaseUrl, path);

  try {
    const response = await postWithoutBodyWithRetry(
      requestUrl,
      buildRequestHeadersWithoutContentType(options.bearerToken)
    );
    const headerTraceId = getResponseTraceId(response.headers);
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
    const traceId = headerTraceId ?? bodyTraceId ?? buildClientTraceId();

    return {
      ok: false,
      status: response.status,
      traceId,
      traceIdMismatch,
      policyReason: parsedError?.policyReason ?? null,
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
      traceId: buildClientTraceId(),
      traceIdMismatch: false,
      policyReason: null,
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
      policyReason: "source_export_user_approval_required",
      error: {
        code: "VALIDATION_ERROR",
        message: "Case export requires explicit user approval before download.",
      },
    };
  }

  const requestUrl = buildApiUrl(options.apiBaseUrl, "/export/cases");
  try {
    const response = await postBinaryWithRetry(
      requestUrl,
      buildRequestHeadersWithOverrides(options.bearerToken, {
        accept: PDF_ACCEPT_HEADER,
      }),
      payload
    );
    const headerTraceId = getResponseTraceId(response.headers);

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
    const traceId = headerTraceId ?? bodyTraceId ?? buildClientTraceId();

    return {
      ok: false,
      status: response.status,
      traceId,
      traceIdMismatch,
      policyReason: parsedError?.policyReason ?? null,
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
      traceId: buildClientTraceId(),
      traceIdMismatch: false,
      policyReason: null,
      error: {
        code: "PROVIDER_ERROR",
        message: "Unable to reach the IMMCAD API endpoint.",
      },
    };
  }
}

function postCaseExportApproval(
  options: ApiClientOptions,
  payload: CaseExportApprovalRequestPayload
): Promise<ApiResult<CaseExportApprovalResponsePayload>> {
  if (payload.user_approved !== true) {
    return Promise.resolve({
      ok: false,
      status: 422,
      traceId: null,
      traceIdMismatch: false,
      policyReason: "source_export_user_approval_required",
      error: {
        code: "VALIDATION_ERROR",
        message: "Case export requires explicit user approval before download.",
      },
    });
  }
  return postJson<CaseExportApprovalResponsePayload>(
    options,
    "/export/cases/approval",
    payload
  );
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
    researchLawyerCases(
      payload: LawyerCaseResearchRequestPayload
    ): Promise<ApiResult<LawyerCaseResearchResponsePayload>> {
      return postJson<LawyerCaseResearchResponsePayload>(
        options,
        "/research/lawyer-cases",
        payload
      );
    },
    exportCasePdf(
      payload: CaseExportRequestPayload
    ): Promise<ApiResult<CaseExportResponsePayload>> {
      return postCaseExport(options, payload);
    },
    requestCaseExportApproval(
      payload: CaseExportApprovalRequestPayload
    ): Promise<ApiResult<CaseExportApprovalResponsePayload>> {
      return postCaseExportApproval(options, payload);
    },
    uploadMatterDocuments(
      payload: DocumentIntakeRequestPayload
    ): Promise<ApiResult<DocumentIntakeResponsePayload>> {
      const files = payload.files ?? [];
      if (files.length === 0) {
        return Promise.resolve({
          ok: false,
          status: 422,
          traceId: null,
          traceIdMismatch: false,
          policyReason: null,
          error: {
            code: "VALIDATION_ERROR",
            message: "Select at least one file before uploading.",
          },
        });
      }
      const formData = new FormData();
      formData.append("forum", payload.forum);
      if (payload.matter_id?.trim()) {
        formData.append("matter_id", payload.matter_id.trim());
      }
      for (const file of files) {
        formData.append("files", file, file.name);
      }
      return postMultipart<DocumentIntakeResponsePayload>(
        options,
        "/documents/intake",
        formData
      );
    },
    getMatterReadiness(
      matterId: string
    ): Promise<ApiResult<MatterReadinessResponsePayload>> {
      const normalizedMatterId = matterId.trim();
      if (!normalizedMatterId) {
        return Promise.resolve({
          ok: false,
          status: 422,
          traceId: null,
          traceIdMismatch: false,
          policyReason: null,
          error: {
            code: "VALIDATION_ERROR",
            message: "Matter ID is required.",
          },
        });
      }
      return getJson<MatterReadinessResponsePayload>(
        options,
        `/documents/matters/${encodeURIComponent(normalizedMatterId)}/readiness`
      );
    },
    buildMatterPackage(
      matterId: string
    ): Promise<ApiResult<MatterPackageResponsePayload>> {
      const normalizedMatterId = matterId.trim();
      if (!normalizedMatterId) {
        return Promise.resolve({
          ok: false,
          status: 422,
          traceId: null,
          traceIdMismatch: false,
          policyReason: null,
          error: {
            code: "VALIDATION_ERROR",
            message: "Matter ID is required.",
          },
        });
      }
      return postWithoutBody<MatterPackageResponsePayload>(
        options,
        `/documents/matters/${encodeURIComponent(normalizedMatterId)}/package`
      );
    },
  };
}
