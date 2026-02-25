import { afterEach, describe, expect, it, vi } from "vitest";

import { getServerRuntimeConfig } from "@/lib/server-runtime-config";

const ORIGINAL_ENV = { ...process.env };

function resetEnv(): void {
  process.env = { ...ORIGINAL_ENV };
}

describe("server runtime config token resolution", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
    resetEnv();
  });

  it("uses IMMCAD_API_BEARER_TOKEN when configured", () => {
    delete process.env.API_BEARER_TOKEN;
    process.env.IMMCAD_API_BEARER_TOKEN = "primary-token";

    const config = getServerRuntimeConfig();

    expect(config.backendBearerToken).toBe("primary-token");
  });

  it("falls back to API_BEARER_TOKEN compatibility alias", () => {
    delete process.env.IMMCAD_API_BEARER_TOKEN;
    process.env.API_BEARER_TOKEN = "compat-token";

    const config = getServerRuntimeConfig();

    expect(config.backendBearerToken).toBe("compat-token");
  });

  it("enforces bearer token presence in production", () => {
    vi.stubEnv("NODE_ENV", "production");
    process.env.IMMCAD_API_BASE_URL = "https://api.example.com";
    delete process.env.IMMCAD_API_BEARER_TOKEN;
    delete process.env.API_BEARER_TOKEN;

    expect(() => getServerRuntimeConfig()).toThrow(
      "IMMCAD_API_BEARER_TOKEN is required in hardened environments"
    );
  });

  it("enforces hardened requirements when ENVIRONMENT is production", () => {
    process.env.ENVIRONMENT = "production";
    process.env.IMMCAD_API_BASE_URL = "https://api.example.com";
    delete process.env.IMMCAD_API_BEARER_TOKEN;
    delete process.env.API_BEARER_TOKEN;

    expect(() => getServerRuntimeConfig()).toThrow(
      "IMMCAD_API_BEARER_TOKEN is required in hardened environments"
    );
  });

  it.each(["production-us-east", "prod_blue", "ci-smoke"])(
    "enforces hardened requirements for ENVIRONMENT alias %s",
    (environment) => {
      process.env.ENVIRONMENT = environment;
      process.env.IMMCAD_API_BASE_URL = "https://api.example.com";
      delete process.env.IMMCAD_API_BEARER_TOKEN;
      delete process.env.API_BEARER_TOKEN;

      expect(() => getServerRuntimeConfig()).toThrow(
        "IMMCAD_API_BEARER_TOKEN is required in hardened environments"
      );
    }
  );

  it.each(["production-us-east", "prod_blue", "ci-smoke"])(
    "enforces hardened requirements for IMMCAD_ENVIRONMENT alias %s",
    (environment) => {
      process.env.IMMCAD_ENVIRONMENT = environment;
      process.env.IMMCAD_API_BASE_URL = "https://api.example.com";
      delete process.env.IMMCAD_API_BEARER_TOKEN;
      delete process.env.API_BEARER_TOKEN;

      expect(() => getServerRuntimeConfig()).toThrow(
        "IMMCAD_API_BEARER_TOKEN is required in hardened environments"
      );
    }
  );

  it("rejects mismatched IMMCAD_ENVIRONMENT and ENVIRONMENT values", () => {
    process.env.IMMCAD_ENVIRONMENT = "production-us-east";
    process.env.ENVIRONMENT = "development";

    expect(() => getServerRuntimeConfig()).toThrow(
      "IMMCAD_ENVIRONMENT and ENVIRONMENT must match when both are set."
    );
  });

  it("rejects mismatched token values when both variables are set", () => {
    process.env.IMMCAD_API_BEARER_TOKEN = "token-a";
    process.env.API_BEARER_TOKEN = "token-b";

    expect(() => getServerRuntimeConfig()).toThrow(
      "IMMCAD_API_BEARER_TOKEN and API_BEARER_TOKEN must match when both are set."
    );
  });
});
