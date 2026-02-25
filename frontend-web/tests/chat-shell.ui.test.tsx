import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ChatShell } from "@/components/chat-shell";
import {
  CHAT_SUCCESS_RESPONSE,
  LAWYER_RESEARCH_SUCCESS_RESPONSE,
} from "@/tests/fixtures/chat-contract-fixtures";

const LEGAL_DISCLAIMER =
  "IMMCAD provides Canadian immigration information only and does not provide legal advice or representation.";

function jsonResponse(
  body: unknown,
  {
    status = 200,
    headers = {},
  }: {
    status?: number;
    headers?: Record<string, string>;
  } = {}
): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: {
      "content-type": "application/json",
      ...headers,
    },
  });
}

function createDeferred<T>(): {
  promise: Promise<T>;
  resolve: (value: T) => void;
  reject: (reason?: unknown) => void;
} {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((resolvePromise, rejectPromise) => {
    resolve = resolvePromise;
    reject = rejectPromise;
  });
  return { promise, resolve, reject };
}

describe("chat shell ui", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    cleanup();
  });

  it("renders redesigned shell chrome and normalizes API target display", () => {
    render(
      <ChatShell
        apiBaseUrl="https://api.immcad.test/"
        legalDisclaimer={LEGAL_DISCLAIMER}
        showOperationalPanels
      />
    );

    expect(screen.getByText("Canada immigration scope notice")).toBeTruthy();
    expect(screen.getByText("IMMCAD Assistant")).toBeTruthy();
    expect(
      screen.getAllByText("API target: https://api.immcad.test").length
    ).toBeGreaterThan(0);
  });

  it("hydrates draft from quick prompt and toggles send button state", async () => {
    render(
      <ChatShell
        apiBaseUrl="https://api.immcad.test"
        legalDisclaimer={LEGAL_DISCLAIMER}
        showOperationalPanels
      />
    );

    const user = userEvent.setup();
    const textarea = screen.getByLabelText("Ask a Canadian immigration question");
    const sendButton = screen.getByRole("button", { name: "Send" });
    const describedBy = textarea.getAttribute("aria-describedby") ?? "";

    expect(sendButton.hasAttribute("disabled")).toBe(true);
    expect(describedBy).toContain("chat-input-hint");
    expect(describedBy).toContain("chat-input-count");

    await user.click(
      screen.getByRole("button", {
        name: "What are the eligibility basics for Express Entry?",
      })
    );

    expect((textarea as HTMLTextAreaElement).value).toBe(
      "What are the eligibility basics for Express Entry?"
    );
    expect(sendButton.hasAttribute("disabled")).toBe(false);
    expect(document.activeElement).toBe(textarea);
  });

  it("supports Ctrl+Enter submit shortcut", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      jsonResponse(CHAT_SUCCESS_RESPONSE, {
        headers: { "x-trace-id": "trace-shortcut" },
      })
    );

    render(
      <ChatShell
        apiBaseUrl="https://api.immcad.test"
        legalDisclaimer={LEGAL_DISCLAIMER}
        showOperationalPanels
      />
    );

    const user = userEvent.setup();
    const textarea = screen.getByLabelText("Ask a Canadian immigration question");

    await user.type(textarea, "How does Express Entry work?");
    await user.keyboard("{Control>}{Enter}{/Control}");

    expect(await screen.findByText(CHAT_SUCCESS_RESPONSE.answer)).toBeTruthy();
  });

  it("updates live-region and aria-busy while request is pending", async () => {
    const deferred = createDeferred<Response>();
    vi.spyOn(globalThis, "fetch").mockReturnValueOnce(deferred.promise);

    render(
      <ChatShell
        apiBaseUrl="https://api.immcad.test"
        legalDisclaimer={LEGAL_DISCLAIMER}
        showOperationalPanels
      />
    );

    const user = userEvent.setup();
    await user.type(
      screen.getByLabelText("Ask a Canadian immigration question"),
      "Give me a study permit eligibility summary."
    );
    await user.click(screen.getByRole("button", { name: "Send" }));

    expect(await screen.findByText("Sending request...")).toBeTruthy();
    expect(await screen.findByText("Submitting your question...")).toBeTruthy();
    expect(screen.getByRole("log").getAttribute("aria-busy")).toBe("true");

    deferred.resolve(
      jsonResponse(CHAT_SUCCESS_RESPONSE, {
        headers: { "x-trace-id": "trace-pending" },
      })
    );

    expect(await screen.findByText(CHAT_SUCCESS_RESPONSE.answer)).toBeTruthy();
    await waitFor(() => {
      expect(screen.getByRole("log").getAttribute("aria-busy")).toBe("false");
    });
  });

  it("exposes accessibility landmarks and enables case search after chat success", async () => {
    vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(
        jsonResponse(CHAT_SUCCESS_RESPONSE, {
          headers: { "x-trace-id": "trace-chat-success" },
        })
      )
      .mockResolvedValueOnce(
        jsonResponse(LAWYER_RESEARCH_SUCCESS_RESPONSE, {
          headers: { "x-trace-id": "trace-cases-success" },
        })
      );

    render(
      <ChatShell
        apiBaseUrl="https://api.immcad.test"
        legalDisclaimer={LEGAL_DISCLAIMER}
        showOperationalPanels
      />
    );

    const user = userEvent.setup();
    const searchCasesButton = screen.getByRole("button", { name: "Find related cases" });
    expect(searchCasesButton.hasAttribute("disabled")).toBe(true);
    expect(screen.getByRole("log")).toBeTruthy();
    expect(screen.getByRole("group", { name: "Quick prompts" })).toBeTruthy();

    await user.type(
      screen.getByLabelText("Ask a Canadian immigration question"),
      "Show me guidance on study permit documents."
    );
    await user.click(screen.getByRole("button", { name: "Send" }));

    expect(await screen.findByText(CHAT_SUCCESS_RESPONSE.answer)).toBeTruthy();
    expect(searchCasesButton.hasAttribute("disabled")).toBe(false);

    await user.click(searchCasesButton);
    expect(await screen.findByText("Sample Tribunal Decision")).toBeTruthy();
    const searchCasesButtonAfterResults = screen.getByRole("button", {
      name: "Find related cases",
    });
    expect(searchCasesButtonAfterResults.getAttribute("aria-controls")).toBe(
      "related-case-results"
    );
    expect(searchCasesButtonAfterResults.getAttribute("aria-expanded")).toBe("true");
    expect(screen.getByRole("link", { name: "Sample Tribunal Decision" })).toBeTruthy();
  });
});
