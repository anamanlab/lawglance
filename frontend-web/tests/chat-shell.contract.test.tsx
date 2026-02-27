import React from "react";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ChatShell } from "@/components/chat-shell";
import {
  CASE_SEARCH_TOO_BROAD_ERROR,
  CHAT_POLICY_REFUSAL_RESPONSE,
  CHAT_SUCCESS_RESPONSE,
  CHAT_SUCCESS_WITH_RESEARCH_PREVIEW,
  EXPORT_POLICY_BLOCKED_ERROR,
  LAWYER_RESEARCH_SUCCESS_RESPONSE,
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
        jsonResponse(LAWYER_RESEARCH_SUCCESS_RESPONSE, {
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
    expect(screen.getByText("Manual case search")).toBeTruthy();
    expect(screen.getByText("Source transparency")).toBeTruthy();
    expect(
      screen.getByText("Official courts: available | CanLII: not used")
    ).toBeTruthy();
    expect(
      screen.getByText("Results by source: Official 1, CanLII 0, Other 0")
    ).toBeTruthy();
    expect(screen.getByText("PDF available")).toBeTruthy();
    expect(screen.getByText("Intake quality: MEDIUM")).toBeTruthy();
    expect(
      screen.getByText("Add target court to narrow precedents (FC/FCA/SCC).")
    ).toBeTruthy();
    expect(
      screen.getByText(/appears relevant for FC precedent support/i)
    ).toBeTruthy();
    expect(
      screen.getByText("Last endpoint: /api/research/lawyer-cases")
    ).toBeTruthy();
    expect(screen.getByText("Trace ID: trace-case-success")).toBeTruthy();
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("hydrates case-law panel from chat auto research preview before manual search", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      jsonResponse(CHAT_SUCCESS_WITH_RESEARCH_PREVIEW, {
        headers: { "x-trace-id": "trace-chat-preview" },
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
      "Need precedent on inadmissibility findings in Federal Court"
    );
    await user.click(screen.getByRole("button", { name: "Send" }));

    expect(await screen.findByText(CHAT_SUCCESS_WITH_RESEARCH_PREVIEW.answer)).toBeTruthy();
    expect(await screen.findByText("Auto Preview Decision")).toBeTruthy();
    expect(screen.getByText("Auto-retrieved for this answer")).toBeTruthy();
    expect(
      screen.getByText("Official courts: available | CanLII: not used")
    ).toBeTruthy();
    expect(
      screen.getByText(
        'Showing 1 related case for: "Need precedent on inadmissibility findings in Federal Court"'
      )
    ).toBeTruthy();
    expect(fetchMock).toHaveBeenCalledTimes(1);
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
        jsonResponse(LAWYER_RESEARCH_SUCCESS_RESPONSE, {
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

  it("collects structured intake fields and renders research confidence details", async () => {
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
            matter_profile: {
              issue_tags: ["procedural_fairness", "inadmissibility"],
              target_court: "fca",
              procedural_posture: "appeal",
            },
            cases: [
              {
                case_id: "fca-77",
                title: "Example FCA Appeal Decision",
                citation: "2024 FCA 77",
                source_id: "FCA_DECISIONS",
                court: "FCA",
                decision_date: "2024-06-10",
                url: "https://example.test/cases/fca-77",
                document_url: "https://example.test/cases/fca-77/document.pdf",
                pdf_status: "available",
                pdf_reason: "document_url_trusted",
                export_allowed: true,
                export_policy_reason: "source_export_allowed",
                relevance_reason: "Anchored to the provided citation and appeal posture.",
              },
            ],
            source_status: {
              official: "ok",
              canlii: "not_used",
            },
            research_confidence: "high",
            confidence_reasons: [
              "Official court sources returned aligned precedent results.",
              "At least one top result matches a citation/docket anchor.",
            ],
            intake_completeness: "high",
            intake_hints: [],
          },
          {
            headers: { "x-trace-id": "trace-case-success" },
          }
        )
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
      "Need precedents for procedural fairness appeals"
    );
    await user.click(screen.getByRole("button", { name: "Send" }));
    await screen.findByText(CHAT_SUCCESS_RESPONSE.answer);

    await user.selectOptions(screen.getByLabelText("Research objective"), "support_precedent");
    await user.selectOptions(screen.getByLabelText("Target court"), "fca");
    await user.type(
      screen.getByLabelText("Issue tags"),
      "procedural_fairness, inadmissibility"
    );
    await user.type(screen.getByLabelText("Citation or docket anchor"), "2024 FCA 77");
    await user.type(screen.getByLabelText("Decision date from"), "2024-01-01");
    await user.type(screen.getByLabelText("Decision date to"), "2025-12-31");
    await user.click(screen.getByRole("button", { name: "Find related cases" }));

    expect(fetchMock).toHaveBeenCalledTimes(2);
    const secondCall = fetchMock.mock.calls[1];
    const secondCallInit = secondCall?.[1] as RequestInit | undefined;
    const secondCallBody =
      typeof secondCallInit?.body === "string" ? secondCallInit.body : "";
    expect(secondCallBody).toContain('"objective":"support_precedent"');
    expect(secondCallBody).toContain('"target_court":"fca"');
    expect(secondCallBody).toContain('"issue_tags":["procedural_fairness","inadmissibility"]');
    expect(secondCallBody).toContain('"anchor_citations":["2024 FCA 77"]');
    expect(secondCallBody).toContain('"date_from":"2024-01-01"');
    expect(secondCallBody).toContain('"date_to":"2025-12-31"');
    expect(await screen.findByText("Research confidence: HIGH")).toBeTruthy();
    expect(screen.getByText("Intake quality: HIGH")).toBeTruthy();
    expect(
      screen.getByText("Official court sources returned aligned precedent results.")
    ).toBeTruthy();
  });

  it("blocks manual case-law search when intake decision-date range is invalid", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(
        jsonResponse(CHAT_SUCCESS_RESPONSE, {
          headers: { "x-trace-id": "trace-chat-success" },
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
      "Need precedent support for inadmissibility in Federal Court"
    );
    await user.click(screen.getByRole("button", { name: "Send" }));
    await screen.findByText(CHAT_SUCCESS_RESPONSE.answer);

    await user.type(screen.getByLabelText("Decision date from"), "2025-12-31");
    await user.type(screen.getByLabelText("Decision date to"), "2024-01-01");
    await user.click(screen.getByRole("button", { name: "Find related cases" }));

    expect(
      await screen.findByText(
        "Decision date range is invalid. 'From' date must be earlier than or equal to 'to' date."
      )
    ).toBeTruthy();
    expect(fetchMock).toHaveBeenCalledTimes(1);
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

  it("requires structured intake details before broad manual case-law search", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(
        jsonResponse(CHAT_SUCCESS_RESPONSE, {
          headers: { "x-trace-id": "trace-chat-success" },
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
        "Add at least two intake details (objective, target court, issue tags, or citation/docket anchor) before running broad case-law research queries."
      )
    ).toBeTruthy();
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("shows actionable backend query guidance when broad query includes intake", async () => {
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
    await user.selectOptions(screen.getByLabelText("Research objective"), "support_precedent");
    await user.selectOptions(screen.getByLabelText("Target court"), "fc");
    await user.click(screen.getByRole("button", { name: "Find related cases" }));

    expect(
      (
        await screen.findAllByText(
          "Case-law query is too broad. Add specific terms such as program, issue, court, or citation."
        )
      ).length
    ).toBeGreaterThan(0);
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

  it("shows unified workflow error banner for related case-law search failures", async () => {
    vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(
        jsonResponse(CHAT_SUCCESS_RESPONSE, {
          headers: { "x-trace-id": "trace-chat-success" },
        })
      )
      .mockResolvedValueOnce(
        jsonResponse(SOURCE_UNAVAILABLE_ERROR, {
          status: 503,
          headers: { "x-trace-id": "trace-case-search-error" },
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
      "Find Federal Court precedent for procedural fairness."
    );
    await user.click(screen.getByRole("button", { name: "Send" }));
    await screen.findByText(CHAT_SUCCESS_RESPONSE.answer);

    await user.click(screen.getByRole("button", { name: "Find related cases" }));

    expect(await screen.findByText("Workflow Notice")).toBeTruthy();
    expect(await screen.findByText("Related case-law search unavailable")).toBeTruthy();
    expect(
      (
        await screen.findAllByText(
          /Unable to search related case law: Authoritative source is unavailable\./
        )
      ).length
    ).toBeGreaterThan(0);
    expect((await screen.findAllByText("Trace ID: trace-case-search-error")).length).toBeGreaterThan(0);
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
        jsonResponse(LAWYER_RESEARCH_SUCCESS_RESPONSE, {
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
            matter_profile: {
              issue_tags: ["inadmissibility"],
              target_court: "fc",
            },
            cases: [
              {
                case_id: "case-2",
                title: "Policy-limited Case",
                citation: "2025 FC 200",
                court: "FC",
                decision_date: "2025-02-12",
                url: "https://www.canlii.org/en/ca/fct/doc/2025/2025fc200/2025fc200.html",
                source_id: "CANLII_CASE_BROWSE",
                document_url:
                  "https://www.canlii.org/en/ca/fct/doc/2025/2025fc200/2025fc200.html",
                pdf_status: "available",
                export_allowed: false,
                export_policy_reason: "source_export_blocked_by_policy",
                relevance_reason: "Relevant to the current matter.",
              },
            ],
            source_status: {
              official: "no_match",
              canlii: "used",
            },
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
      screen.getByText(
        "Online case review is still available. Direct PDF export is unavailable for this source under policy."
      )
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
        jsonResponse(LAWYER_RESEARCH_SUCCESS_RESPONSE, {
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
        jsonResponse(LAWYER_RESEARCH_SUCCESS_RESPONSE, {
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

    const policyBlockedMessages = await screen.findAllByText(
      "Case export was blocked by source policy for this source."
    );
    expect(policyBlockedMessages.length).toBeGreaterThan(0);
  });

  it("shows unified workflow error banner for export failures when diagnostics are enabled", async () => {
    vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(
        jsonResponse(CHAT_SUCCESS_RESPONSE, {
          headers: { "x-trace-id": "trace-chat-success" },
        })
      )
      .mockResolvedValueOnce(
        jsonResponse(LAWYER_RESEARCH_SUCCESS_RESPONSE, {
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

    expect(await screen.findByText("Workflow Notice")).toBeTruthy();
    expect(await screen.findByText("Case export unavailable")).toBeTruthy();
    expect(
      (
        await screen.findAllByText(
          /Case export blocked by source policy/
        )
      ).length
    ).toBeGreaterThan(0);
    expect((await screen.findAllByText("Trace ID: trace-export-policy")).length).toBeGreaterThan(0);
  });

  it("uploads intake documents, fetches readiness, and builds a package when ready", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(
        jsonResponse(
          {
            matter_id: "matter-abc123",
            forum: "federal_court_jr",
            results: [
              {
                file_id: "file-001",
                original_filename: "memo.pdf",
                normalized_filename: "memo-normalized.pdf",
                classification: "memorandum",
                quality_status: "ready",
                issues: [],
              },
              {
                file_id: "file-002",
                original_filename: "affidavit.pdf",
                normalized_filename: "affidavit-normalized.pdf",
                classification: "affidavit",
                quality_status: "needs_review",
                issues: ["ocr_low_confidence"],
              },
            ],
            blocking_issues: [],
            warnings: ["translation_declaration_missing"],
          },
          {
            headers: { "x-trace-id": "trace-doc-intake" },
          }
        )
      )
      .mockResolvedValueOnce(
        jsonResponse(
          {
            matter_id: "matter-abc123",
            forum: "federal_court_jr",
            is_ready: true,
            missing_required_items: [],
            blocking_issues: [],
            warnings: [],
          },
          {
            headers: { "x-trace-id": "trace-doc-readiness" },
          }
        )
      )
      .mockResolvedValueOnce(
        jsonResponse(
          {
            matter_id: "matter-abc123",
            forum: "federal_court_jr",
            table_of_contents: [
              {
                position: 1,
                document_type: "memorandum",
                filename: "memo-normalized.pdf",
              },
            ],
            disclosure_checklist: [
              {
                item: "memorandum",
                status: "present",
              },
            ],
            cover_letter_draft: "Draft cover letter content",
            is_ready: true,
          },
          {
            headers: { "x-trace-id": "trace-doc-package" },
          }
        )
      );

    render(
      <ChatShell
        apiBaseUrl="https://api.immcad.test"
        legalDisclaimer={LEGAL_DISCLAIMER}
      />
    );

    const user = userEvent.setup();
    const uploadInput = screen.getByLabelText("Upload documents");
    const fileA = new File(["memo"], "memo.pdf", { type: "application/pdf" });
    const fileB = new File(["affidavit"], "affidavit.pdf", { type: "application/pdf" });

    await user.upload(uploadInput, [fileA, fileB]);

    expect(await screen.findByText("Matter ID: matter-abc123")).toBeTruthy();
    expect(await screen.findByText("memo.pdf")).toBeTruthy();
    expect(await screen.findByText("affidavit.pdf")).toBeTruthy();
    expect(await screen.findByText(/Ready for filing package:/i)).toBeTruthy();
    expect(screen.getAllByText("Ready").length).toBeGreaterThan(0);
    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(fetchMock.mock.calls[0]?.[0]).toBe("https://api.immcad.test/api/documents/intake");
    expect(fetchMock.mock.calls[1]?.[0]).toBe(
      "https://api.immcad.test/api/documents/matters/matter-abc123/readiness"
    );
    const intakeInit = fetchMock.mock.calls[0]?.[1] as RequestInit | undefined;
    expect(intakeInit).toEqual(
      expect.objectContaining({
        method: "POST",
      })
    );
    expect(intakeInit?.body instanceof FormData).toBe(true);

    await user.click(screen.getByRole("button", { name: "Generate package" }));
    expect(await screen.findByText("Package generated. TOC items: 1.")).toBeTruthy();
    expect(fetchMock).toHaveBeenCalledTimes(3);
    expect(fetchMock.mock.calls[2]?.[0]).toBe(
      "https://api.immcad.test/api/documents/matters/matter-abc123/package"
    );
  });

  it("shows upload failure status when document intake request fails", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      jsonResponse(
        {
          error: {
            code: "VALIDATION_ERROR",
            message: "Unsupported file type.",
            trace_id: "trace-doc-error",
          },
        },
        {
          status: 422,
          headers: { "x-trace-id": "trace-doc-error" },
        }
      )
    );

    render(
      <ChatShell
        apiBaseUrl="https://api.immcad.test"
        legalDisclaimer={LEGAL_DISCLAIMER}
      />
    );

    const user = userEvent.setup();
    const uploadInput = screen.getByLabelText("Upload documents");
    const file = new File(["exe"], "payload.exe", { type: "application/octet-stream" });

    await user.upload(uploadInput, file);

    expect(
      await screen.findByText("Upload failed. Unsupported file type.")
    ).toBeTruthy();
  });
});
