import { SAMPLE_PROMPT, CHAT_SUCCESS_RESPONSE } from "../fixtures/chat-data";
import { ChatShellPage } from "../pages/chat-shell.page";
import { expect, test } from "../fixtures/test-fixtures";

test.describe("chat shell e2e", () => {
  test("sends a user question and renders the assistant response", async ({
    page,
    chatApi,
  }) => {
    const chatShell = new ChatShellPage(page);

    await chatShell.goto();
    await expect(chatShell.sendButton).toBeDisabled();

    await chatShell.chooseQuickPrompt(SAMPLE_PROMPT);
    await expect(chatShell.promptInput).toHaveValue(SAMPLE_PROMPT);
    await expect(chatShell.sendButton).toBeEnabled();

    await chatShell.sendButton.click();

    await expect(page.getByText(CHAT_SUCCESS_RESPONSE.answer)).toBeVisible();
    await expect(
      page.getByRole("link", { name: /Open citation: IRCC Express Entry Overview/i })
    ).toBeVisible();

    expect(chatApi.chatRequestCount()).toBe(1);
    expect(chatApi.lastChatMessage()).toBe(SAMPLE_PROMPT);
  });

  test("loads related cases only after explicit user action", async ({ page, chatApi }) => {
    const chatShell = new ChatShellPage(page);

    await chatShell.goto();
    await expect(chatShell.findRelatedCasesButton).toBeDisabled();

    await chatShell.sendPrompt(SAMPLE_PROMPT);
    await expect(page.getByText(CHAT_SUCCESS_RESPONSE.answer)).toBeVisible();
    await expect(
      page.getByText("Ready to find related Canadian case law.")
    ).toBeVisible();
    await expect(chatShell.findRelatedCasesButton).toBeEnabled();

    expect(chatApi.caseSearchRequestCount()).toBe(0);

    await chatShell.openRelatedCases();

    await expect(page.getByRole("link", { name: "Sample Tribunal Decision" })).toBeVisible();
    expect(chatApi.caseSearchRequestCount()).toBe(1);
    expect(chatApi.lastCaseSearchQuery()).toBe(SAMPLE_PROMPT);
  });
});
