const DEV_DEFAULT_API_BASE_URL = "/api";
const DEV_DEFAULT_REDESIGN_ENABLED = true;
const DEV_DEFAULT_AGENT_THINKING_TIMELINE_ENABLED = true;

export type RuntimeConfig = {
  apiBaseUrl: string;
  enableRedesignedShell: boolean;
  showOperationalPanels: boolean;
  enableAgentThinkingTimeline: boolean;
};

function normalizeValue(value: string | undefined): string | undefined {
  const trimmedValue = value?.trim();
  return trimmedValue ? trimmedValue : undefined;
}

function ensureProductionSafeApiUrl(apiBaseUrl: string, nodeEnv: string): void {
  if (nodeEnv !== "production") {
    return;
  }

  if (!apiBaseUrl.startsWith("https://") && !apiBaseUrl.startsWith("/")) {
    throw new Error(
      "NEXT_PUBLIC_IMMCAD_API_BASE_URL must start with https:// or / in production mode."
    );
  }
}

function parseBooleanFlag(
  value: string | undefined,
  defaultValue: boolean
): boolean {
  const normalizedValue = normalizeValue(value)?.toLowerCase();
  if (!normalizedValue) {
    return defaultValue;
  }
  if (["1", "true", "yes", "on"].includes(normalizedValue)) {
    return true;
  }
  if (["0", "false", "no", "off"].includes(normalizedValue)) {
    return false;
  }
  return defaultValue;
}

export function getRuntimeConfig(): RuntimeConfig {
  const nodeEnv = process.env.NODE_ENV ?? "development";
  const configuredBaseUrl = normalizeValue(process.env.NEXT_PUBLIC_IMMCAD_API_BASE_URL);
  const apiBaseUrl = configuredBaseUrl ?? DEV_DEFAULT_API_BASE_URL;
  const enableRedesignedShell = parseBooleanFlag(
    process.env.NEXT_PUBLIC_IMMCAD_FRONTEND_REDESIGN_ENABLED,
    DEV_DEFAULT_REDESIGN_ENABLED
  );
  const showOperationalPanelsConfig = parseBooleanFlag(
    process.env.NEXT_PUBLIC_IMMCAD_SHOW_OPERATIONS_PANELS,
    nodeEnv !== "production"
  );
  const enableAgentThinkingTimeline = parseBooleanFlag(
    process.env.NEXT_PUBLIC_IMMCAD_ENABLE_AGENT_THINKING_TIMELINE,
    nodeEnv === "production" ? false : DEV_DEFAULT_AGENT_THINKING_TIMELINE_ENABLED
  );
  const showOperationalPanels =
    nodeEnv === "production" ? false : showOperationalPanelsConfig;

  ensureProductionSafeApiUrl(apiBaseUrl, nodeEnv);

  return {
    apiBaseUrl,
    enableRedesignedShell,
    showOperationalPanels,
    enableAgentThinkingTimeline,
  };
}
