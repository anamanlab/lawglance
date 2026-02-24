import { afterEach, describe, expect, it, vi } from "vitest";

import { getRuntimeConfig } from "@/lib/runtime-config";

const ORIGINAL_ENV = { ...process.env };

function resetEnv(): void {
  process.env = { ...ORIGINAL_ENV };
}

describe("runtime config", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
    resetEnv();
  });

  it("uses safe defaults when variables are not set", () => {
    delete process.env.NEXT_PUBLIC_IMMCAD_API_BASE_URL;
    delete process.env.NEXT_PUBLIC_IMMCAD_FRONTEND_REDESIGN_ENABLED;
    delete process.env.NEXT_PUBLIC_IMMCAD_SHOW_OPERATIONS_PANELS;

    const config = getRuntimeConfig();

    expect(config.apiBaseUrl).toBe("/api");
    expect(config.enableRedesignedShell).toBe(true);
    expect(config.showOperationalPanels).toBe(true);
  });

  it("parses redesign feature flag values", () => {
    process.env.NEXT_PUBLIC_IMMCAD_FRONTEND_REDESIGN_ENABLED = "false";

    const disabled = getRuntimeConfig();
    expect(disabled.enableRedesignedShell).toBe(false);

    process.env.NEXT_PUBLIC_IMMCAD_FRONTEND_REDESIGN_ENABLED = "1";
    const enabled = getRuntimeConfig();
    expect(enabled.enableRedesignedShell).toBe(true);
  });

  it("falls back to default flag value for invalid input", () => {
    process.env.NEXT_PUBLIC_IMMCAD_FRONTEND_REDESIGN_ENABLED = "invalid-value";
    process.env.NEXT_PUBLIC_IMMCAD_SHOW_OPERATIONS_PANELS = "invalid-value";

    const config = getRuntimeConfig();

    expect(config.enableRedesignedShell).toBe(true);
    expect(config.showOperationalPanels).toBe(true);
  });

  it("enforces production-safe API URL", () => {
    vi.stubEnv("NODE_ENV", "production");
    process.env.NEXT_PUBLIC_IMMCAD_API_BASE_URL = "http://insecure.example.com";

    expect(() => getRuntimeConfig()).toThrow(
      "NEXT_PUBLIC_IMMCAD_API_BASE_URL must start with https:// or / in production mode."
    );
  });

  it("hides operational panels by default in production", () => {
    vi.stubEnv("NODE_ENV", "production");
    delete process.env.NEXT_PUBLIC_IMMCAD_SHOW_OPERATIONS_PANELS;

    const config = getRuntimeConfig();

    expect(config.showOperationalPanels).toBe(false);
  });
});
