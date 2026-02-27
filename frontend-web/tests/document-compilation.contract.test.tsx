import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ChatShell } from "@/components/chat-shell";

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

const DEFAULT_DOCUMENT_SUPPORT_MATRIX = {
  supported_profiles_by_forum: {
    federal_court_jr: ["federal_court_jr_leave", "federal_court_jr_hearing"],
    rpd: ["rpd"],
    rad: ["rad"],
    id: ["id"],
    iad: ["iad", "iad_sponsorship", "iad_residency", "iad_admissibility"],
    ircc_application: ["ircc_pr_card_renewal"],
  },
  unsupported_profile_families: [
    "humanitarian_and_compassionate",
    "prra",
    "work_permit",
    "study_permit",
    "citizenship_proof",
  ],
};

function supportMatrixResponse(): Response {
  return jsonResponse(DEFAULT_DOCUMENT_SUPPORT_MATRIX, {
    headers: { "x-trace-id": "trace-doc-support-matrix" },
  });
}

function requestUrl(input: RequestInfo | URL): string {
  if (typeof input === "string") {
    return input;
  }
  if (input instanceof URL) {
    return input.toString();
  }
  return input.url;
}

function mockDocumentFetchSequence(responses: Response[]) {
  const queue = [...responses];
  return vi.spyOn(globalThis, "fetch").mockImplementation(async (input: RequestInfo | URL) => {
    const url = requestUrl(input);
    if (url.endsWith("/api/documents/support-matrix")) {
      return supportMatrixResponse();
    }
    const nextResponse = queue.shift();
    if (!nextResponse) {
      throw new Error(`Unexpected fetch call for URL: ${url}`);
    }
    return nextResponse;
  });
}

describe("document compilation contract", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    cleanup();
  });

  it("renders rule violations, pagination summary, TOC page ranges, and blocked reasons", async () => {
    const fetchMock = mockDocumentFetchSequence([
      jsonResponse(
        {
          matter_id: "matter-compile-001",
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
          ],
          blocking_issues: [],
          warnings: [],
        },
        {
          headers: { "x-trace-id": "trace-doc-intake" },
        }
      ),
      jsonResponse(
        {
          matter_id: "matter-compile-001",
          forum: "federal_court_jr",
          is_ready: true,
          missing_required_items: [],
          blocking_issues: [],
          warnings: [],
        },
        {
          headers: { "x-trace-id": "trace-doc-readiness" },
        }
      ),
      jsonResponse(
        {
          matter_id: "matter-compile-001",
          forum: "federal_court_jr",
          toc_entries: [
            {
              position: 1,
              document_type: "memorandum",
              filename: "memo-normalized.pdf",
              start_page: 1,
              end_page: 12,
            },
            {
              position: 2,
              document_type: "affidavit",
              filename: "affidavit-normalized.pdf",
              start_page: 13,
              end_page: 22,
            },
          ],
          pagination_summary: "Pages 1-22 across 2 compiled documents.",
          rule_violations: [
            {
              severity: "blocking",
              violation_code: "MISSING_TRANSLATION_AFFIDAVIT",
              rule_source_url: "https://policy.example.test/rules#translation-affidavit",
              remediation: "Upload a sworn translator affidavit and regenerate package.",
            },
            {
              severity: "warning",
              code: "EXHIBIT_ORDER_WARNING",
              source_url: "https://policy.example.test/rules#exhibit-order",
              remediation: "Reorder exhibits to match citation order.",
            },
          ],
          compilation_profile: {
            id: "fcjr-default",
            version: "2026.02",
          },
          table_of_contents: [],
          disclosure_checklist: [],
          cover_letter_draft: "Draft cover letter",
          is_ready: false,
        },
        {
          headers: { "x-trace-id": "trace-doc-package" },
        }
      ),
    ]);

    render(
      <ChatShell
        apiBaseUrl="https://api.immcad.test"
        legalDisclaimer={LEGAL_DISCLAIMER}
      />
    );

    const user = userEvent.setup();
    const uploadInput = screen.getByLabelText("Upload documents");
    const file = new File(["memo"], "memo.pdf", { type: "application/pdf" });

    await user.upload(uploadInput, file);
    expect(await screen.findByText("Matter ID: matter-compile-001")).toBeTruthy();

    await user.click(screen.getByRole("button", { name: "Generate package" }));

    expect(await screen.findByText("Rule violations")).toBeTruthy();
    expect(screen.getByText("MISSING_TRANSLATION_AFFIDAVIT")).toBeTruthy();
    expect(screen.getByText("EXHIBIT_ORDER_WARNING")).toBeTruthy();
    expect(
      screen.getByRole("link", {
        name: "Source reference: MISSING_TRANSLATION_AFFIDAVIT",
      }).getAttribute("href")
    ).toBe("https://policy.example.test/rules#translation-affidavit");
    expect(
      screen.getByRole("link", {
        name: "Source reference: EXHIBIT_ORDER_WARNING",
      }).getAttribute("href")
    ).toBe("https://policy.example.test/rules#exhibit-order");
    expect(
      screen.getByText("Upload a sworn translator affidavit and regenerate package.")
    ).toBeTruthy();

    expect(screen.getByText("Compilation TOC")).toBeTruthy();
    expect(screen.getByText(/Pages 1-12/)).toBeTruthy();
    expect(screen.getByText(/Pages 13-22/)).toBeTruthy();
    expect(screen.getByText("Pages 1-22 across 2 compiled documents.")).toBeTruthy();
    expect(screen.getByText("Compilation profile: fcjr-default v2026.02")).toBeTruthy();

    expect(screen.getByText("Why blocked")).toBeTruthy();
    expect(
      screen.getByText(
        "Resolve blocking rule MISSING_TRANSLATION_AFFIDAVIT: Upload a sworn translator affidavit and regenerate package."
      )
    ).toBeTruthy();

    const calledEndpoints = fetchMock.mock.calls.map((call) =>
      requestUrl(call[0] as RequestInfo | URL)
    );
    expect(calledEndpoints.length).toBeGreaterThanOrEqual(4);
    expect(calledEndpoints).toContain("https://api.immcad.test/api/documents/intake");
    expect(calledEndpoints).toContain("https://api.immcad.test/api/documents/support-matrix");
    expect(calledEndpoints).toContain(
      "https://api.immcad.test/api/documents/matters/matter-compile-001/readiness"
    );
    expect(calledEndpoints).toContain(
      "https://api.immcad.test/api/documents/matters/matter-compile-001/package"
    );
  });

  it("renders TOC details from legacy table_of_contents payloads", async () => {
    mockDocumentFetchSequence([
      jsonResponse(
        {
          matter_id: "matter-legacy-002",
          forum: "federal_court_jr",
          results: [
            {
              file_id: "file-legacy-001",
              original_filename: "record.pdf",
              normalized_filename: "record-normalized.pdf",
              classification: "record",
              quality_status: "ready",
              issues: [],
            },
          ],
          blocking_issues: [],
          warnings: [],
        },
        {
          headers: { "x-trace-id": "trace-doc-intake-legacy" },
        }
      ),
      jsonResponse(
        {
          matter_id: "matter-legacy-002",
          forum: "federal_court_jr",
          is_ready: true,
          missing_required_items: [],
          blocking_issues: [],
          warnings: [],
        },
        {
          headers: { "x-trace-id": "trace-doc-readiness-legacy" },
        }
      ),
      jsonResponse(
        {
          matter_id: "matter-legacy-002",
          forum: "federal_court_jr",
          table_of_contents: [
            {
              position: 1,
              document_type: "record",
              filename: "record-normalized.pdf",
            },
          ],
          disclosure_checklist: [
            {
              item: "record",
              status: "present",
            },
          ],
          cover_letter_draft: "Draft cover letter",
          is_ready: true,
        },
        {
          headers: { "x-trace-id": "trace-doc-package-legacy" },
        }
      ),
    ]);

    render(
      <ChatShell
        apiBaseUrl="https://api.immcad.test"
        legalDisclaimer={LEGAL_DISCLAIMER}
      />
    );

    const user = userEvent.setup();
    const uploadInput = screen.getByLabelText("Upload documents");
    const file = new File(["record"], "record.pdf", { type: "application/pdf" });

    await user.upload(uploadInput, file);
    expect(await screen.findByText("Matter ID: matter-legacy-002")).toBeTruthy();

    await user.click(screen.getByRole("button", { name: "Generate package" }));

    expect(await screen.findByText("Compilation TOC")).toBeTruthy();
    expect(screen.getByText(/record-normalized\.pdf/)).toBeTruthy();
    expect(screen.getByText(/Page range unavailable/)).toBeTruthy();
  });

  it("renders record section completeness with missing-slot remediation guidance", async () => {
    mockDocumentFetchSequence([
      jsonResponse(
        {
          matter_id: "matter-sections-004",
          forum: "rpd",
          results: [
            {
              file_id: "file-sections-001",
              original_filename: "translation.pdf",
              normalized_filename: "translation-normalized.pdf",
              classification: "translation",
              quality_status: "ready",
              issues: [],
            },
          ],
          blocking_issues: [],
          warnings: [],
        },
        {
          headers: { "x-trace-id": "trace-doc-intake-sections" },
        }
      ),
      jsonResponse(
        {
          matter_id: "matter-sections-004",
          forum: "rpd",
          is_ready: true,
          missing_required_items: [],
          blocking_issues: [],
          warnings: [],
        },
        {
          headers: { "x-trace-id": "trace-doc-readiness-sections" },
        }
      ),
      jsonResponse(
        {
          matter_id: "matter-sections-004",
          forum: "rpd",
          toc_entries: [
            {
              position: 1,
              document_type: "translation",
              filename: "translation-normalized.pdf",
              start_page: 1,
              end_page: 2,
            },
          ],
          pagination_summary: "Pages 1-2 across 1 compiled document.",
          record_sections: [
            {
              section_id: "rpd_supporting_materials",
              title: "Supporting Materials",
              instructions:
                "Append witness list material and any translation package items after core RPD records.",
              document_types: [
                "witness_list",
                "translation",
                "translator_declaration",
              ],
              section_status: "missing",
              missing_document_types: ["translator_declaration"],
              missing_reasons: [
                "Add a translator declaration when translations are filed.",
              ],
              slot_statuses: [
                {
                  document_type: "translator_declaration",
                  status: "missing",
                  rule_scope: "conditional",
                  reason:
                    "Add a translator declaration when translations are filed.",
                },
              ],
            },
          ],
          disclosure_checklist: [],
          cover_letter_draft: "Draft cover letter",
          is_ready: false,
        },
        {
          headers: { "x-trace-id": "trace-doc-package-sections" },
        }
      ),
    ]);

    render(
      <ChatShell
        apiBaseUrl="https://api.immcad.test"
        legalDisclaimer={LEGAL_DISCLAIMER}
      />
    );

    const user = userEvent.setup();
    const uploadInput = screen.getByLabelText("Upload documents");
    const file = new File(["translation"], "translation.pdf", {
      type: "application/pdf",
    });

    await user.upload(uploadInput, file);
    expect(await screen.findByText("Matter ID: matter-sections-004")).toBeTruthy();

    await user.click(screen.getByRole("button", { name: "Generate package" }));

    expect(await screen.findByText("Record section completeness")).toBeTruthy();
    expect(screen.getByText("Supporting Materials")).toBeTruthy();
    expect(screen.getByText("Missing: translator declaration")).toBeTruthy();
    expect(
      screen.getByText("Add a translator declaration when translations are filed.")
    ).toBeTruthy();
  });

  it("formats object pagination_summary payloads without crashing", async () => {
    mockDocumentFetchSequence([
      jsonResponse(
        {
          matter_id: "matter-object-summary-003",
          forum: "federal_court_jr",
          results: [
            {
              file_id: "file-object-001",
              original_filename: "record.pdf",
              normalized_filename: "record-normalized.pdf",
              classification: "record",
              quality_status: "ready",
              issues: [],
            },
          ],
          blocking_issues: [],
          warnings: [],
        },
        {
          headers: { "x-trace-id": "trace-doc-intake-object-summary" },
        }
      ),
      jsonResponse(
        {
          matter_id: "matter-object-summary-003",
          forum: "federal_court_jr",
          is_ready: true,
          missing_required_items: [],
          blocking_issues: [],
          warnings: [],
        },
        {
          headers: { "x-trace-id": "trace-doc-readiness-object-summary" },
        }
      ),
      jsonResponse(
        {
          matter_id: "matter-object-summary-003",
          forum: "federal_court_jr",
          toc_entries: [
            {
              position: 1,
              document_type: "record",
              filename: "record-normalized.pdf",
              start_page: 1,
              end_page: 3,
            },
          ],
          pagination_summary: {
            total_documents: 1,
            total_pages: 3,
            last_assigned_page: 3,
          },
          disclosure_checklist: [],
          cover_letter_draft: "Draft cover letter",
          is_ready: true,
        },
        {
          headers: { "x-trace-id": "trace-doc-package-object-summary" },
        }
      ),
    ]);

    render(
      <ChatShell
        apiBaseUrl="https://api.immcad.test"
        legalDisclaimer={LEGAL_DISCLAIMER}
      />
    );

    const user = userEvent.setup();
    const uploadInput = screen.getByLabelText("Upload documents");
    const file = new File(["record"], "record.pdf", { type: "application/pdf" });

    await user.upload(uploadInput, file);
    expect(await screen.findByText("Matter ID: matter-object-summary-003")).toBeTruthy();

    await user.click(screen.getByRole("button", { name: "Generate package" }));

    expect(await screen.findByText("Compilation TOC")).toBeTruthy();
    expect(
      screen.getByText("Pagination summary: 1 compiled document, 3 pages, last assigned page 3.")
    ).toBeTruthy();
  });
});
