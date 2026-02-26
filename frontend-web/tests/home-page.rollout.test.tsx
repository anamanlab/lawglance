import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

function mockChatShell(): void {
  vi.doMock("@/components/chat-shell", () => ({
    ChatShell: ({ apiBaseUrl, legalDisclaimer }: { apiBaseUrl: string; legalDisclaimer: string }) => (
      <div
        data-testid="chat-shell-stub"
        data-api-base-url={apiBaseUrl}
        data-disclaimer={legalDisclaimer}
      >
        ChatShellStub
      </div>
    ),
  }));
}

describe("home page rollout", () => {
  afterEach(() => {
    cleanup();
  });

  it("renders redesigned page chrome when redesign flag is enabled", async () => {
    vi.resetModules();
    mockChatShell();
    vi.doMock("@/lib/runtime-config", () => ({
      getRuntimeConfig: () => ({
        apiBaseUrl: "/api",
        enableRedesignedShell: true,
        showOperationalPanels: false,
      }),
    }));

    const { default: HomePage } = await import("@/app/page");

    render(<HomePage />);

    expect(screen.getByText("Canadian Immigration Assistant")).toBeTruthy();
    expect(
      screen.getByText(
        "Understand official immigration pathways, requirements, and next steps with grounded information."
      )
    ).toBeTruthy();
    expect(screen.getByTestId("chat-shell-stub")).toBeTruthy();
  });

  it("renders classic shell-only layout when redesign flag is disabled", async () => {
    vi.resetModules();
    mockChatShell();
    vi.doMock("@/lib/runtime-config", () => ({
      getRuntimeConfig: () => ({
        apiBaseUrl: "/api",
        enableRedesignedShell: false,
        showOperationalPanels: true,
      }),
    }));

    const { default: HomePage } = await import("@/app/page");

    render(<HomePage />);

    expect(screen.queryByText("IMMCAD Assistant")).toBeNull();
    expect(screen.getByTestId("chat-shell-stub")).toBeTruthy();
  });
});
