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
    delete process.env.VERCEL_ENV;
    vi.stubEnv("NODE_ENV", "production");
    process.env.IMMCAD_API_BASE_URL = "https://api.example.com";
    delete process.env.IMMCAD_API_BEARER_TOKEN;
    delete process.env.API_BEARER_TOKEN;

    expect(() => getServerRuntimeConfig()).toThrow(
      "IMMCAD_API_BEARER_TOKEN is required in hardened environments"
    );
  });

  it("treats explicit ENVIRONMENT=development as non-hardened when NODE_ENV is production", () => {
    delete process.env.VERCEL_ENV;
    vi.stubEnv("ENVIRONMENT", "development");
    vi.stubEnv("IMMCAD_ENVIRONMENT", "development");
    vi.stubEnv("NODE_ENV", "production");
    process.env.IMMCAD_API_BASE_URL = "http://127.0.0.1:8000";
    delete process.env.IMMCAD_API_BEARER_TOKEN;
    delete process.env.API_BEARER_TOKEN;

    const config = getServerRuntimeConfig();

    expect(config.backendBaseUrl).toBe("http://127.0.0.1:8000");
    expect(config.backendBearerToken).toBeNull();
  });

  it("treats VERCEL preview as non-hardened even when NODE_ENV is production", () => {
    vi.stubEnv("VERCEL_ENV", "preview");
    vi.stubEnv("NODE_ENV", "production");
    process.env.IMMCAD_API_BASE_URL = "http://127.0.0.1:8000";
    delete process.env.IMMCAD_API_BEARER_TOKEN;
    delete process.env.API_BEARER_TOKEN;

    const config = getServerRuntimeConfig();

    expect(config.backendBaseUrl).toBe("http://127.0.0.1:8000");
    expect(config.backendBearerToken).toBeNull();
  });

  it("does not use NEXT_PUBLIC_IMMCAD_API_BASE_URL for server runtime config", () => {
    delete process.env.IMMCAD_API_BASE_URL;
    process.env.NEXT_PUBLIC_IMMCAD_API_BASE_URL = "https://public.example.com";

    const config = getServerRuntimeConfig();

    expect(config.backendBaseUrl).toBe("http://127.0.0.1:8000");
  });

  it("includes fallback backend base URL when configured", () => {
    process.env.ENVIRONMENT = "development";
    process.env.IMMCAD_ENVIRONMENT = "development";
    process.env.IMMCAD_API_BASE_URL = "https://api-primary.example.com";
    process.env.IMMCAD_API_BASE_URL_FALLBACK = "https://api-fallback.example.com";

    const config = getServerRuntimeConfig();

    expect(config.backendBaseUrl).toBe("https://api-primary.example.com");
    expect(config.backendFallbackBaseUrl).toBe(
      "https://api-fallback.example.com"
    );
  });

  it("drops fallback backend URL when it matches primary URL", () => {
    process.env.ENVIRONMENT = "development";
    process.env.IMMCAD_ENVIRONMENT = "development";
    process.env.IMMCAD_API_BASE_URL = "https://api-primary.example.com";
    process.env.IMMCAD_API_BASE_URL_FALLBACK = "https://api-primary.example.com";

    const config = getServerRuntimeConfig();

    expect(config.backendFallbackBaseUrl).toBeNull();
  });

  it("enforces https requirement for fallback backend URL in hardened environments", () => {
    process.env.ENVIRONMENT = "production";
    process.env.IMMCAD_ENVIRONMENT = "production";
    process.env.IMMCAD_API_BASE_URL = "https://api-primary.example.com";
    process.env.IMMCAD_API_BASE_URL_FALLBACK = "http://127.0.0.1:8000";
    process.env.IMMCAD_API_BEARER_TOKEN = "token";
    process.env.API_BEARER_TOKEN = "token";

    expect(() => getServerRuntimeConfig()).toThrow(
      "IMMCAD_API_BASE_URL must start with https:// in hardened environments."
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
