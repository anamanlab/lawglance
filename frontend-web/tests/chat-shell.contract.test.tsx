import React from "react";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ChatShell } from "@/components/chat-shell";
import {
  CASE_SEARCH_SUCCESS_RESPONSE,
  CHAT_POLICY_REFUSAL_RESPONSE,
  CHAT_SUCCESS_RESPONSE,
  SOURCE_UNAVAILABLE_ERROR,
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

describe("chat shell contract behavior", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    cleanup();
  });

  it("renders success response citations and trace IDs", async () => {
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
        apiBearerToken={null}
        legalDisclaimer={LEGAL_DISCLAIMER}
      />
    );

    const user = userEvent.setup();
    await user.type(
      screen.getByLabelText("Ask a Canada immigration question"),
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
    expect(screen.getByText("Sample Tribunal Decision")).toBeTruthy();
    expect(screen.getByText("Trace ID: trace-chat-success")).toBeTruthy();
    expect(screen.getByText("Last endpoint: /api/search/cases")).toBeTruthy();
    expect(screen.getByText("Trace ID: trace-case-success")).toBeTruthy();
    expect(fetchMock).toHaveBeenCalledTimes(2);
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
        apiBearerToken={null}
        legalDisclaimer={LEGAL_DISCLAIMER}
      />
    );

    const user = userEvent.setup();
    await user.type(
      screen.getByLabelText("Ask a Canada immigration question"),
      "Can you represent me in my application?"
    );
    await user.click(screen.getByRole("button", { name: "Send" }));

    expect(await screen.findByText("Policy refusal response")).toBeTruthy();
    expect(
      screen.getByText(
        "Policy refusal response returned. Ask a general informational question to continue."
      )
    ).toBeTruthy();
    expect(screen.getAllByText("Trace ID: trace-policy-refusal").length).toBeGreaterThan(
      0
    );
    expect(screen.getByText("Last endpoint: /api/chat")).toBeTruthy();
    expect(fetchMock).toHaveBeenCalledTimes(1);
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
        apiBearerToken={null}
        legalDisclaimer={LEGAL_DISCLAIMER}
      />
    );

    const user = userEvent.setup();
    await user.type(
      screen.getByLabelText("Ask a Canada immigration question"),
      "Show me recent appeal decisions."
    );
    await user.click(screen.getByRole("button", { name: "Send" }));

    expect(await screen.findByText("Source unavailable")).toBeTruthy();
    expect(screen.getByText("Authoritative source is unavailable.")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Retry last request" })).toBeTruthy();
    expect(
      screen.getByText("Trace mismatch detected between header and error body.")
    ).toBeTruthy();

    await waitFor(() => {
      expect(screen.getByText("Last outcome: error")).toBeTruthy();
      expect(screen.getByText("Last error code: SOURCE_UNAVAILABLE")).toBeTruthy();
    });
  });
});
