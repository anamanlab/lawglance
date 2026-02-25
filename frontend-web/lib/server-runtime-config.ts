const DEV_DEFAULT_BACKEND_BASE_URL = "http://127.0.0.1:8000";
const HARDENED_ENVIRONMENT_PATTERN = /^(production|prod|ci)(?:[-_].+)?$/;

export type ServerRuntimeConfig = {
  backendBaseUrl: string;
  backendBearerToken: string | null;
};

function normalizeValue(value: string | undefined): string | undefined {
  const trimmedValue = value?.trim();
  return trimmedValue ? trimmedValue : undefined;
}

function resolveRuntimeEnvironment(): string {
  const explicitEnvironment = normalizeValue(process.env.IMMCAD_ENVIRONMENT);
  const compatibilityEnvironment = normalizeValue(process.env.ENVIRONMENT);
  if (
    explicitEnvironment &&
    compatibilityEnvironment &&
    explicitEnvironment.toLowerCase() !== compatibilityEnvironment.toLowerCase()
  ) {
    throw new Error(
      "IMMCAD_ENVIRONMENT and ENVIRONMENT must match when both are set."
    );
  }
  const resolvedEnvironment = explicitEnvironment ?? compatibilityEnvironment;
  if (resolvedEnvironment) {
    return resolvedEnvironment.toLowerCase();
  }

  const vercelEnvironment = normalizeValue(process.env.VERCEL_ENV)?.toLowerCase();
  const nodeEnvironment = normalizeValue(process.env.NODE_ENV)?.toLowerCase();
  if (vercelEnvironment === "production" || nodeEnvironment === "production") {
    return "production";
  }
  return "development";
}

export function isHardenedRuntimeEnvironment(): boolean {
  const environment = resolveRuntimeEnvironment();
  return HARDENED_ENVIRONMENT_PATTERN.test(environment);
}

function ensureHardenedSafeBackendUrl(
  backendBaseUrl: string,
  hardenedEnvironment: boolean
): void {
  if (!hardenedEnvironment) {
    return;
  }
  if (!backendBaseUrl.startsWith("https://")) {
    throw new Error(
      "IMMCAD_API_BASE_URL must start with https:// in hardened environments."
    );
  }
}

function resolveBackendBearerToken(): string | null {
  const canonicalToken = normalizeValue(process.env.IMMCAD_API_BEARER_TOKEN);
  const compatibilityToken = normalizeValue(process.env.API_BEARER_TOKEN);
  if (
    canonicalToken &&
    compatibilityToken &&
    canonicalToken !== compatibilityToken
  ) {
    throw new Error(
      "IMMCAD_API_BEARER_TOKEN and API_BEARER_TOKEN must match when both are set."
    );
  }
  return canonicalToken ?? compatibilityToken ?? null;
}

function ensureProductionBearerTokenConfigured(
  backendBearerToken: string | null,
  hardenedEnvironment: boolean
): void {
  if (!hardenedEnvironment) {
    return;
  }
  if (!backendBearerToken) {
    throw new Error(
      "IMMCAD_API_BEARER_TOKEN is required in hardened environments (API_BEARER_TOKEN is accepted as a compatibility alias)."
    );
  }
}

export function getServerRuntimeConfig(): ServerRuntimeConfig {
  const configuredBackendBaseUrl =
    normalizeValue(process.env.IMMCAD_API_BASE_URL) ??
    normalizeValue(process.env.NEXT_PUBLIC_IMMCAD_API_BASE_URL);
  const backendBaseUrl = configuredBackendBaseUrl ?? DEV_DEFAULT_BACKEND_BASE_URL;
  const hardenedEnvironment = isHardenedRuntimeEnvironment();
  ensureHardenedSafeBackendUrl(backendBaseUrl, hardenedEnvironment);
  const backendBearerToken = resolveBackendBearerToken();
  ensureProductionBearerTokenConfigured(backendBearerToken, hardenedEnvironment);

  return {
    backendBaseUrl,
    backendBearerToken,
  };
}
