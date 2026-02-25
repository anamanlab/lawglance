import React from "react";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ChatShell } from "@/components/chat-shell";
import {
  CASE_SEARCH_TOO_BROAD_ERROR,
  CASE_SEARCH_SUCCESS_RESPONSE,
  CHAT_POLICY_REFUSAL_RESPONSE,
  CHAT_SUCCESS_RESPONSE,
  EXPORT_POLICY_BLOCKED_ERROR,
  SOURCE_UNAVAILABLE_ERROR,
  UNAUTHORIZED_ERROR,
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

function pdfResponse(
  payload: Uint8Array,
  {
    status = 200,
    headers = {},
  }: {
    status?: number;
    headers?: Record<string, string>;
  } = {}
): Response {
  return new Response(payload, {
    status,
    headers: {
      "content-type": "application/pdf",
      ...headers,
    },
  });
}

describe("chat shell contract behavior", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    cleanup();
  });

  it("renders chat response first and runs case search only on explicit action", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(
        jsonResponse(CHAT_SUCCESS_RESPONSE, {
          headers: { "x-trace-id": "trace-chat-success" },
        })
      )
      .mockResolvedValueOnce(
        jsonResponse(CASE_SEARCH_SUCCESS_RESPONSE, {
          headers: { "x-trace-id": "trace-case-success" },
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
    await user.type(
      screen.getByLabelText("Ask a Canadian immigration question"),
      "How does Express Entry work?"
    );
    await user.click(screen.getByRole("button", { name: "Send" }));

    expect(await screen.findByText(CHAT_SUCCESS_RESPONSE.answer)).toBeTruthy();
    const citationLink = await screen.findByRole("link", {
      name: "Open citation: IRCC Express Entry Overview (Eligibility)",
    });
    expect(citationLink.getAttribute("href")).toBe(
      CHAT_SUCCESS_RESPONSE.citations[0]?.url
    );
    expect(screen.getAllByText("Trace ID: trace-chat-success").length).toBeGreaterThan(0);
    expect(screen.getByText("Last endpoint: /api/chat")).toBeTruthy();
    expect(fetchMock).toHaveBeenCalledTimes(1);

    await user.click(screen.getByRole("button", { name: "Find related cases" }));

    expect(await screen.findByText("Sample Tribunal Decision")).toBeTruthy();
    expect(screen.getByText("Last endpoint: /api/search/cases")).toBeTruthy();
    expect(screen.getByText("Trace ID: trace-case-success")).toBeTruthy();
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("allows editing the case-search query before running related case lookup", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(
        jsonResponse(CHAT_SUCCESS_RESPONSE, {
          headers: { "x-trace-id": "trace-chat-success" },
        })
      )
      .mockResolvedValueOnce(
        jsonResponse(CASE_SEARCH_SUCCESS_RESPONSE, {
          headers: { "x-trace-id": "trace-case-success" },
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
    await user.type(
      screen.getByLabelText("Ask a Canadian immigration question"),
      "How does Express Entry work?"
    );
    await user.click(screen.getByRole("button", { name: "Send" }));
    expect(await screen.findByText(CHAT_SUCCESS_RESPONSE.answer)).toBeTruthy();

    const caseQueryInput = screen.getByLabelText("Case search query");
    await user.clear(caseQueryInput);
    await user.type(caseQueryInput, "Federal Court inadmissibility decision");
    await user.click(screen.getByRole("button", { name: "Find related cases" }));

    expect(fetchMock).toHaveBeenCalledTimes(2);
    const secondCall = fetchMock.mock.calls[1];
    expect(secondCall).toBeDefined();
    const secondCallInit = secondCall?.[1] as RequestInit | undefined;
    const secondCallBody =
      typeof secondCallInit?.body === "string" ? secondCallInit.body : "";
    expect(secondCallBody).toContain("Federal Court inadmissibility decision");
  });

  it("renders policy refusal UX without case-search request", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      jsonResponse(CHAT_POLICY_REFUSAL_RESPONSE, {
        headers: { "x-trace-id": "trace-policy-refusal" },
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
    await user.type(
      screen.getByLabelText("Ask a Canadian immigration question"),
      "Can you represent me in my application?"
    );
    await user.click(screen.getByRole("button", { name: "Send" }));

    expect(await screen.findByText("Policy refusal response")).toBeTruthy();
    expect(
      screen.getByText(
        "This chat request was blocked by policy. You can still run case-law search with a specific Canadian immigration query."
      )
    ).toBeTruthy();
    expect(screen.getAllByText("Trace ID: trace-policy-refusal").length).toBeGreaterThan(
      0
    );
    expect(screen.getByText("Last endpoint: /api/chat")).toBeTruthy();
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("shows actionable query guidance when case search query is too broad", async () => {
    vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(
        jsonResponse(CHAT_SUCCESS_RESPONSE, {
          headers: { "x-trace-id": "trace-chat-success" },
        })
      )
      .mockResolvedValueOnce(
        jsonResponse(CASE_SEARCH_TOO_BROAD_ERROR, {
          status: 422,
          headers: { "x-trace-id": "trace-case-broad" },
        })
      );

    render(
      <ChatShell
        apiBaseUrl="https://api.immcad.test"
        legalDisclaimer={LEGAL_DISCLAIMER}
      />
    );

    const user = userEvent.setup();
    await user.type(
      screen.getByLabelText("Ask a Canadian immigration question"),
      "Find case law"
    );
    await user.click(screen.getByRole("button", { name: "Send" }));
    await screen.findByText(CHAT_SUCCESS_RESPONSE.answer);

    const caseQueryInput = screen.getByLabelText("Case search query");
    await user.clear(caseQueryInput);
    await user.type(caseQueryInput, "to be");
    await user.click(screen.getByRole("button", { name: "Find related cases" }));

    expect(
      await screen.findByText(
        "Case-law query is too broad. Add specific terms such as program, issue, court, or citation."
      )
    ).toBeTruthy();
  });

  it("renders structured error copy and mismatch warning when traces differ", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      jsonResponse(SOURCE_UNAVAILABLE_ERROR, {
        status: 503,
        headers: { "x-trace-id": "trace-header" },
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
    await user.type(
      screen.getByLabelText("Ask a Canadian immigration question"),
      "Show me recent appeal decisions."
    );
    await user.click(screen.getByRole("button", { name: "Send" }));

    expect(await screen.findByText("Case-law source unavailable")).toBeTruthy();
    expect(
      screen.getByText("Authoritative source is unavailable.")
    ).toBeTruthy();
    expect(screen.getByRole("button", { name: "Retry last request" })).toBeTruthy();
    expect(
      screen.getByText("Trace mismatch detected between header and error body.")
    ).toBeTruthy();

    await waitFor(() => {
      expect(screen.getByText("Last outcome: error")).toBeTruthy();
      expect(screen.getByText("Last error code: SOURCE_UNAVAILABLE")).toBeTruthy();
    });
  });

  it("shows actionable auth guidance when API returns unauthorized", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      jsonResponse(UNAUTHORIZED_ERROR, {
        status: 401,
        headers: { "x-trace-id": "trace-auth" },
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
    await user.type(
      screen.getByLabelText("Ask a Canadian immigration question"),
      "How does sponsorship for a spouse work in Canada?"
    );
    await user.click(screen.getByRole("button", { name: "Send" }));

    expect(await screen.findByText("Authentication required")).toBeTruthy();
    expect(screen.getByText("Missing or invalid bearer token")).toBeTruthy();
    expect(
      screen.getByText(
        "Verify IMMCAD_API_BEARER_TOKEN (or API_BEARER_TOKEN) is configured on the frontend server, then retry."
      )
    ).toBeTruthy();
    expect(screen.getByRole("button", { name: "Retry last request" })).toBeTruthy();
  });

  it("requires explicit user approval before triggering case export", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(
        jsonResponse(CHAT_SUCCESS_RESPONSE, {
          headers: { "x-trace-id": "trace-chat-success" },
        })
      )
      .mockResolvedValueOnce(
        jsonResponse(CASE_SEARCH_SUCCESS_RESPONSE, {
          headers: { "x-trace-id": "trace-case-success" },
        })
      );
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(false);

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
      "Find Federal Court examples for study permit refusals."
    );
    await user.click(screen.getByRole("button", { name: "Send" }));
    await screen.findByText(CHAT_SUCCESS_RESPONSE.answer);

    await user.click(screen.getByRole("button", { name: "Find related cases" }));
    await screen.findByText("Sample Tribunal Decision");

    await user.click(screen.getByRole("button", { name: "Export PDF" }));

    expect(confirmSpy).toHaveBeenCalledTimes(1);
    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(
      screen.getByText("Case export cancelled. No file was downloaded.")
    ).toBeTruthy();
  });

  it("blocks export UI for non-exportable case results", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(
        jsonResponse(CHAT_SUCCESS_RESPONSE, {
          headers: { "x-trace-id": "trace-chat-success" },
        })
      )
      .mockResolvedValueOnce(
        jsonResponse(
          {
            results: [
              {
                case_id: "case-2",
                title: "Policy-limited Case",
                citation: "2025 FC 200",
                decision_date: "2025-02-12",
                url: "https://www.canlii.org/en/ca/fct/doc/2025/2025fc200/2025fc200.html",
                source_id: "CANLII_CASE_BROWSE",
                document_url:
                  "https://www.canlii.org/en/ca/fct/doc/2025/2025fc200/2025fc200.html",
                export_allowed: false,
                export_policy_reason: "source_export_blocked_by_policy",
              },
            ],
          },
          {
            headers: { "x-trace-id": "trace-case-success" },
          }
        )
      );
    const confirmSpy = vi.spyOn(window, "confirm");

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
      "Find Federal Court examples for study permit refusals."
    );
    await user.click(screen.getByRole("button", { name: "Send" }));
    await screen.findByText(CHAT_SUCCESS_RESPONSE.answer);

    await user.click(screen.getByRole("button", { name: "Find related cases" }));
    await screen.findByText("Policy-limited Case");

    const exportButton = screen.getByRole("button", { name: "Export PDF" });
    expect((exportButton as HTMLButtonElement).disabled).toBe(true);
    expect(
      screen.getByText("Export unavailable for this source under policy.")
    ).toBeTruthy();
    expect(confirmSpy).not.toHaveBeenCalled();
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("exports a case PDF after approval and updates support context", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(
        jsonResponse(CHAT_SUCCESS_RESPONSE, {
          headers: { "x-trace-id": "trace-chat-success" },
        })
      )
      .mockResolvedValueOnce(
        jsonResponse(CASE_SEARCH_SUCCESS_RESPONSE, {
          headers: { "x-trace-id": "trace-case-success" },
        })
      )
      .mockResolvedValueOnce(
        jsonResponse(
          {
            approval_token: "approval-token-123",
            expires_at_epoch: 1_900_000_000,
          },
          {
            headers: { "x-trace-id": "trace-approval-success" },
          }
        )
      )
      .mockResolvedValueOnce(
        pdfResponse(new Uint8Array([0x25, 0x50, 0x44, 0x46]), {
          headers: {
            "x-trace-id": "trace-export-success",
            "content-disposition": 'attachment; filename="case-export.pdf"',
            "x-export-policy-reason": "source_export_allowed",
          },
        })
      );
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(true);
    const createObjectURLMock = vi.fn(() => "blob:case-export");
    const revokeObjectURLMock = vi.fn();
    const linkClickSpy = vi
      .spyOn(HTMLAnchorElement.prototype, "click")
      .mockImplementation(() => {});
    Object.defineProperty(window.URL, "createObjectURL", {
      configurable: true,
      writable: true,
      value: createObjectURLMock,
    });
    Object.defineProperty(window.URL, "revokeObjectURL", {
      configurable: true,
      writable: true,
      value: revokeObjectURLMock,
    });

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
      "Find Federal Court examples for study permit refusals."
    );
    await user.click(screen.getByRole("button", { name: "Send" }));
    await screen.findByText(CHAT_SUCCESS_RESPONSE.answer);

    await user.click(screen.getByRole("button", { name: "Find related cases" }));
    await screen.findByText("Sample Tribunal Decision");

    await user.click(screen.getByRole("button", { name: "Export PDF" }));

    await screen.findByText("Download started: case-export.pdf");
    expect(confirmSpy).toHaveBeenCalledTimes(1);
    expect(fetchMock).toHaveBeenCalledTimes(4);
    expect(fetchMock.mock.calls[2]?.[0]).toBe(
      "https://api.immcad.test/api/export/cases/approval"
    );
    expect(fetchMock.mock.calls[3]?.[0]).toBe("https://api.immcad.test/api/export/cases");
    expect(fetchMock.mock.calls[3]?.[1]).toEqual(
      expect.objectContaining({
        method: "POST",
        body: expect.stringContaining('"approval_token":"approval-token-123"'),
      })
    );
    expect(createObjectURLMock).toHaveBeenCalledTimes(1);
    expect(revokeObjectURLMock).toHaveBeenCalledWith("blob:case-export");
    expect(linkClickSpy).toHaveBeenCalledTimes(1);
    expect(screen.getByText("Last endpoint: /api/export/cases")).toBeTruthy();
    expect(screen.getByText("Trace ID: trace-export-success")).toBeTruthy();
    expect(screen.getByText("Last policy reason: source_export_allowed")).toBeTruthy();
  });

  it("shows policy-blocked export message without diagnostics mode", async () => {
    vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(
        jsonResponse(CHAT_SUCCESS_RESPONSE, {
          headers: { "x-trace-id": "trace-chat-success" },
        })
      )
      .mockResolvedValueOnce(
        jsonResponse(CASE_SEARCH_SUCCESS_RESPONSE, {
          headers: { "x-trace-id": "trace-case-success" },
        })
      )
      .mockResolvedValueOnce(
        jsonResponse(
          {
            approval_token: "approval-token-123",
            expires_at_epoch: 1_900_000_000,
          },
          {
            headers: { "x-trace-id": "trace-approval-success" },
          }
        )
      )
      .mockResolvedValueOnce(
        jsonResponse(EXPORT_POLICY_BLOCKED_ERROR, {
          status: 403,
          headers: { "x-trace-id": "trace-export-policy" },
        })
      );
    vi.spyOn(window, "confirm").mockReturnValue(true);

    render(
      <ChatShell
        apiBaseUrl="https://api.immcad.test"
        legalDisclaimer={LEGAL_DISCLAIMER}
      />
    );

    const user = userEvent.setup();
    await user.type(
      screen.getByLabelText("Ask a Canadian immigration question"),
      "Find Federal Court examples for study permit refusals."
    );
    await user.click(screen.getByRole("button", { name: "Send" }));
    await screen.findByText(CHAT_SUCCESS_RESPONSE.answer);

    await user.click(screen.getByRole("button", { name: "Find related cases" }));
    await screen.findByText("Sample Tribunal Decision");
    await user.click(screen.getByRole("button", { name: "Export PDF" }));

    expect(
      await screen.findByText("Case export was blocked by source policy for this source.")
    ).toBeTruthy();
  });
});
