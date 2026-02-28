import {
  CASE_SEARCH_RESPONSE,
  EXPORT_APPROVAL_RESPONSE,
  EXPORT_PDF_BYTES,
  EXPORT_PDF_FILENAME,
  SAMPLE_PROMPT,
} from "../fixtures/chat-data";
import { ChatShellPage } from "../pages/chat-shell.page";
import { installChatApiStubs } from "../support/network-stubs";
import { expect, test } from "@playwright/test";

test("exports a related case after explicit user approval", async ({ page }) => {
  const chatApi = await installChatApiStubs(page);
  const chatShell = new ChatShellPage(page);

  let approvalRequestCount = 0;
  let exportRequestCount = 0;
  let lastApprovalToken: string | null = null;

  await page.route("**/api/export/cases/approval", async (route) => {
    approvalRequestCount += 1;
    await route.fulfill({
      status: 200,
      headers: {
        "content-type": "application/json",
        "x-trace-id": "trace-approval-e2e",
      },
      body: JSON.stringify(EXPORT_APPROVAL_RESPONSE),
    });
  });

  await page.route("**/api/export/cases", async (route) => {
    exportRequestCount += 1;
    const body = route.request().postDataJSON() as Record<string, unknown>;
    const token = body.approval_token;
    lastApprovalToken = typeof token === "string" ? token : null;

    await route.fulfill({
      status: 200,
      headers: {
        "content-type": "application/pdf",
        "content-disposition": `attachment; filename=\"${EXPORT_PDF_FILENAME}\"`,
        "x-trace-id": "trace-export-e2e",
      },
      body: EXPORT_PDF_BYTES,
    });
  });

  await chatShell.goto();
  await chatShell.sendPrompt(SAMPLE_PROMPT);
  await chatShell.openRelatedCases();

  await expect(
    page.getByRole("link", { name: CASE_SEARCH_RESPONSE.results[0].title })
  ).toBeVisible();

  await page.getByRole("button", { name: "Export PDF" }).click();
  await expect(
    page.getByRole("heading", { name: "Export this case PDF now?" })
  ).toBeVisible();
  await page.getByRole("button", { name: "Export PDF now" }).click();

  await expect(
    page.getByText(
      new RegExp(
        `^(Download started: ${EXPORT_PDF_FILENAME}|Case export completed, but automatic download is unavailable in this browser \\(${EXPORT_PDF_FILENAME}\\)\\.)$`
      )
    )
  ).toBeVisible();

  expect(chatApi.chatRequestCount()).toBe(1);
  expect(chatApi.caseSearchRequestCount()).toBe(1);
  expect(approvalRequestCount).toBe(1);
  expect(exportRequestCount).toBe(1);
  expect(lastApprovalToken).toBe(EXPORT_APPROVAL_RESPONSE.approval_token);
});
