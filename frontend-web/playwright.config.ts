import { defineConfig, devices, type PlaywrightTestConfig } from "@playwright/test";

type ProjectConfig = NonNullable<PlaywrightTestConfig["projects"]>[number];

const PLAYWRIGHT_PORT = Number(process.env.PLAYWRIGHT_PORT ?? "3100");
const BASE_URL =
  process.env.PLAYWRIGHT_BASE_URL ?? `http://127.0.0.1:${PLAYWRIGHT_PORT}`;
const SHOULD_START_WEBSERVER = process.env.PLAYWRIGHT_SKIP_WEBSERVER !== "true";
const DEFAULT_WEBSERVER_COMMAND =
  process.env.PLAYWRIGHT_WEB_SERVER_COMMAND ??
  `npm run dev -- --hostname 127.0.0.1 --port ${PLAYWRIGHT_PORT}`;

const PROJECT_MATRIX: ProjectConfig[] = [
  {
    name: "chromium",
    use: {
      ...devices["Desktop Chrome"],
    },
  },
  {
    name: "firefox",
    use: {
      ...devices["Desktop Firefox"],
    },
  },
  {
    name: "webkit",
    use: {
      ...devices["Desktop Safari"],
    },
  },
  {
    name: "Mobile Chrome",
    use: {
      ...devices["Pixel 5"],
    },
  },
  {
    name: "Mobile Safari",
    use: {
      ...devices["iPhone 12"],
    },
  },
];

const DEFAULT_LOCAL_PROJECT_NAMES = ["chromium", "firefox", "Mobile Chrome"];
const DEFAULT_CI_PROJECT_NAMES = [
  "chromium",
  "firefox",
  "webkit",
  "Mobile Chrome",
  "Mobile Safari",
];

function projectName(project: ProjectConfig): string {
  if (!project.name) {
    throw new Error("Playwright project is missing a required name.");
  }
  return project.name;
}

function selectProjectsByName(projectNames: string[]): ProjectConfig[] {
  const requestedSet = new Set(projectNames);
  const selectedProjects = PROJECT_MATRIX.filter((project) =>
    requestedSet.has(projectName(project))
  );

  if (selectedProjects.length === 0) {
    throw new Error(
      `No Playwright projects were selected from: ${projectNames.join(", ")}`
    );
  }

  return selectedProjects;
}

function resolveProjects(): ProjectConfig[] {
  const requestedProjects = process.env.PLAYWRIGHT_PROJECTS?.split(",")
    .map((projectName) => projectName.trim())
    .filter(Boolean);

  if (requestedProjects && requestedProjects.length > 0) {
    const selectedProjects = selectProjectsByName(requestedProjects);
    return selectedProjects;
  }

  const defaultProjectNames = process.env.CI
    ? DEFAULT_CI_PROJECT_NAMES
    : DEFAULT_LOCAL_PROJECT_NAMES;
  const selectedProjects = selectProjectsByName(defaultProjectNames);

  // Headless Linux hosts often do not have WebKit/Safari runtime libraries.
  // Keep defaults stable for local server environments; opt into WebKit explicitly.
  if (!process.env.CI) {
    return selectedProjects;
  }

  return selectedProjects.filter((project) =>
    process.env.PLAYWRIGHT_INCLUDE_SAFARI === "true"
      ? true
      : projectName(project) !== "Mobile Safari"
  );
}

const config: PlaywrightTestConfig = {
  testDir: "./e2e/specs",
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 2 : 4,
  timeout: 30_000,
  expect: {
    timeout: 10_000,
  },
  reporter: process.env.CI
    ? [
        ["dot"],
        ["html", { open: "never" }],
        ["junit", { outputFile: "test-results/e2e-junit.xml" }],
      ]
    : [["list"], ["html", { open: "never" }]],
  use: {
    baseURL: BASE_URL,
    trace: "on-first-retry",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
    actionTimeout: 10_000,
    navigationTimeout: 15_000,
  },
  outputDir: "test-results/playwright",
  projects: resolveProjects(),
  webServer: SHOULD_START_WEBSERVER
    ? {
        command: DEFAULT_WEBSERVER_COMMAND,
        url: BASE_URL,
        reuseExistingServer: !process.env.CI,
        timeout: 180_000,
        stdout: "pipe",
        stderr: "pipe",
        env: {
          ...process.env,
          NODE_ENV: "development",
          ENVIRONMENT: "development",
          IMMCAD_ENVIRONMENT: "development",
          NEXT_PUBLIC_IMMCAD_API_BASE_URL: "/api",
        },
      }
    : undefined,
};

export default defineConfig(config);
