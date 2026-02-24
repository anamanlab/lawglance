const DEV_DEFAULT_BACKEND_BASE_URL = "http://127.0.0.1:8000";

export type ServerRuntimeConfig = {
  backendBaseUrl: string;
  backendBearerToken: string | null;
};

function normalizeValue(value: string | undefined): string | undefined {
  const trimmedValue = value?.trim();
  return trimmedValue ? trimmedValue : undefined;
}

function ensureProductionSafeBackendUrl(backendBaseUrl: string, nodeEnv: string): void {
  if (nodeEnv !== "production") {
    return;
  }
  if (!backendBaseUrl.startsWith("https://")) {
    throw new Error("IMMCAD_API_BASE_URL must start with https:// in production mode.");
  }
}

export function getServerRuntimeConfig(): ServerRuntimeConfig {
  const nodeEnv = process.env.NODE_ENV ?? "development";
  const configuredBackendBaseUrl =
    normalizeValue(process.env.IMMCAD_API_BASE_URL) ??
    normalizeValue(process.env.NEXT_PUBLIC_IMMCAD_API_BASE_URL);
  const backendBaseUrl = configuredBackendBaseUrl ?? DEV_DEFAULT_BACKEND_BASE_URL;
  ensureProductionSafeBackendUrl(backendBaseUrl, nodeEnv);

  return {
    backendBaseUrl,
    backendBearerToken: normalizeValue(process.env.IMMCAD_API_BEARER_TOKEN) ?? null,
  };
}
