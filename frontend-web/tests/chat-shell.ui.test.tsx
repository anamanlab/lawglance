import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
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

function parseActivityPayload(testId: string): Array<{
  stage: string;
  status: string;
  meta?: Record<string, unknown>;
}> {
  const rawPayload = screen.getByTestId(testId).textContent ?? "[]";
  return JSON.parse(rawPayload) as Array<{
    stage: string;
    status: string;
    meta?: Record<string, unknown>;
  }>;
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
        enableAgentThinkingTimeline={false}
        showOperationalPanels
      />
    );

    expect(screen.getByText("IMMCAD Assistant")).toBeTruthy();
    expect(screen.getAllByText(LEGAL_DISCLAIMER).length).toBeGreaterThan(0);
    expect(screen.getByRole("link", { name: "Sources" })).toBeTruthy();
    expect(screen.getByText("Informational only")).toBeTruthy();
    expect(screen.getByText("Cite sources")).toBeTruthy();
    expect(
      screen.getAllByText("API target: https://api.immcad.test").length
    ).toBeGreaterThan(0);
  });

  it("hydrates draft from quick prompt and toggles send button state", async () => {
    render(
      <ChatShell
        apiBaseUrl="https://api.immcad.test"
        legalDisclaimer={LEGAL_DISCLAIMER}
        enableAgentThinkingTimeline={false}
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
        enableAgentThinkingTimeline={false}
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
          enableAgentThinkingTimeline
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
    expect(await screen.findByLabelText("Agent activity")).toBeTruthy();
    expect(screen.getByText("Understanding question")).toBeTruthy();
    expect(parseActivityPayload("agent-activity-pending")).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ stage: "intake", status: "running" }),
        expect.objectContaining({ stage: "retrieval", status: "running" }),
      ])
    );

    deferred.resolve(
      jsonResponse(CHAT_SUCCESS_RESPONSE, {
        headers: { "x-trace-id": "trace-pending" },
      })
    );

    expect(await screen.findByText(CHAT_SUCCESS_RESPONSE.answer)).toBeTruthy();
    expect(parseActivityPayload("agent-activity-latest")).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ stage: "retrieval", status: "success" }),
        expect.objectContaining({ stage: "grounding", status: "success" }),
        expect.objectContaining({ stage: "synthesis", status: "success" }),
        expect.objectContaining({ stage: "delivery", status: "success" }),
      ])
    );
    await waitFor(() => {
      expect(screen.getByRole("log").getAttribute("aria-busy")).toBe("false");
    });
  });

  it("toggles assistant thinking drawer details when timeline is enabled", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      jsonResponse(CHAT_SUCCESS_RESPONSE, {
        headers: { "x-trace-id": "trace-thinking-drawer" },
      })
    );

    render(
      <ChatShell
        apiBaseUrl="https://api.immcad.test"
        legalDisclaimer={LEGAL_DISCLAIMER}
        enableAgentThinkingTimeline
        showOperationalPanels
      />
    );

    const user = userEvent.setup();
    await user.type(
      screen.getByLabelText("Ask a Canadian immigration question"),
      "How does Express Entry work?"
    );
    await user.click(screen.getByRole("button", { name: "Send" }));

    expect(await screen.findByText(CHAT_SUCCESS_RESPONSE.answer)).toBeTruthy();
    await user.click(
      await screen.findByRole("button", { name: "Show agent thinking" })
    );
    const timelineList = screen.getByRole("list", { name: "Timeline details" });
    expect(timelineList).toBeTruthy();
    expect(within(timelineList).getByText("Evaluating sources")).toBeTruthy();
    expect(
      screen.getByRole("button", { name: "Hide details" })
    ).toBeTruthy();
  });

  it("hides timeline UI affordances when thinking timeline feature flag is disabled", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      jsonResponse(CHAT_SUCCESS_RESPONSE, {
        headers: { "x-trace-id": "trace-thinking-disabled" },
      })
    );

    render(
      <ChatShell
        apiBaseUrl="https://api.immcad.test"
        legalDisclaimer={LEGAL_DISCLAIMER}
        enableAgentThinkingTimeline={false}
      />
    );

    const user = userEvent.setup();
    await user.type(
      screen.getByLabelText("Ask a Canadian immigration question"),
      "How does Express Entry work?"
    );
    await user.click(screen.getByRole("button", { name: "Send" }));

    expect(await screen.findByText(CHAT_SUCCESS_RESPONSE.answer)).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Show agent thinking" })).toBeNull();
    expect(screen.queryByLabelText("Agent activity")).toBeNull();
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
        enableAgentThinkingTimeline={false}
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

  it("shows low-specificity query guidance and applies refinement suggestion chips", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      jsonResponse(CHAT_SUCCESS_RESPONSE, {
        headers: { "x-trace-id": "trace-chat-success" },
      })
    );

    render(
      <ChatShell
        apiBaseUrl="https://api.immcad.test"
        legalDisclaimer={LEGAL_DISCLAIMER}
        enableAgentThinkingTimeline={false}
      />
    );

    const user = userEvent.setup();
    await user.type(
      screen.getByLabelText("Ask a Canadian immigration question"),
      "Find case law"
    );
    await user.click(screen.getByRole("button", { name: "Send" }));
    expect(await screen.findByText(CHAT_SUCCESS_RESPONSE.answer)).toBeTruthy();

    const caseQueryInput = screen.getByLabelText(
      "Case search query"
    ) as HTMLInputElement;
    expect(caseQueryInput.value).toBe("Find case law");
    expect(
      screen.getByText(
        "Query may be too broad. Add at least two anchors: program/issue and court or citation."
      )
    ).toBeTruthy();

    await user.click(
      screen.getByRole("button", { name: "Find case law Federal Court" })
    );
    expect(caseQueryInput.value).toBe("Find case law Federal Court");
  });

  it("renders structured research intake controls in the case-law panel", () => {
    render(
      <ChatShell
        apiBaseUrl="https://api.immcad.test"
        legalDisclaimer={LEGAL_DISCLAIMER}
        enableAgentThinkingTimeline={false}
      />
    );

    expect(screen.getByLabelText("Research objective")).toBeTruthy();
    expect(screen.getByLabelText("Target court")).toBeTruthy();
    expect(screen.queryByLabelText("Issue tags")).toBeNull();
    expect(screen.queryByLabelText("Citation or docket anchor")).toBeNull();
    expect(screen.queryByLabelText("Decision date from")).toBeNull();
    expect(screen.queryByLabelText("Decision date to")).toBeNull();
  });

  it("renders document-intake controls in the sidebar", async () => {
    render(
      <ChatShell
        apiBaseUrl="https://api.immcad.test"
        legalDisclaimer={LEGAL_DISCLAIMER}
        enableAgentThinkingTimeline={false}
      />
    );

    const user = userEvent.setup();
    await user.click(screen.getByRole("tab", { name: "Documents" }));
    expect(screen.getByText("Document intake")).toBeTruthy();
    expect(screen.getByLabelText("Document forum")).toBeTruthy();
    expect(screen.getByLabelText("Matter ID (optional)")).toBeTruthy();
    expect(screen.getByLabelText("Upload documents")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Refresh readiness" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Generate package" })).toBeTruthy();
  });
});
