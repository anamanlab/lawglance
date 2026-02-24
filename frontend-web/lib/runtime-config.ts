const DEV_DEFAULT_API_BASE_URL = "http://127.0.0.1:8000";

export type RuntimeConfig = {
  apiBaseUrl: string;
};

function normalizeValue(value: string | undefined): string | undefined {
  const trimmedValue = value?.trim();
  return trimmedValue ? trimmedValue : undefined;
}

function ensureProductionSafeApiUrl(apiBaseUrl: string, nodeEnv: string): void {
  if (nodeEnv !== "production") {
    return;
  }

  if (!apiBaseUrl.startsWith("https://")) {
    throw new Error(
      "NEXT_PUBLIC_IMMCAD_API_BASE_URL must start with https:// in production mode."
    );
  }
}

export function getRuntimeConfig(): RuntimeConfig {
  const nodeEnv = process.env.NODE_ENV ?? "development";
  const configuredBaseUrl = normalizeValue(process.env.NEXT_PUBLIC_IMMCAD_API_BASE_URL);
  const apiBaseUrl = configuredBaseUrl ?? DEV_DEFAULT_API_BASE_URL;

  ensureProductionSafeApiUrl(apiBaseUrl, nodeEnv);

  return { apiBaseUrl };
}
