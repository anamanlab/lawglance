import { CHAT_POLICY_REFUSAL_RESPONSE, SAMPLE_PROMPT } from "../fixtures/chat-data";
import { ChatShellPage } from "../pages/chat-shell.page";
import { installChatApiStubs } from "../support/network-stubs";
import { expect, test } from "@playwright/test";

test("shows policy refusal state and keeps case search disabled", async ({ page }) => {
  const chatApi = await installChatApiStubs(page, {
    chatResponse: CHAT_POLICY_REFUSAL_RESPONSE,
  });
  const chatShell = new ChatShellPage(page);

  await chatShell.goto();
  await chatShell.sendPrompt(SAMPLE_PROMPT);

  await expect(page.getByText("Policy refusal response")).toBeVisible();
  await expect(
    page.getByText(
      "Case-law search is unavailable for this request. Ask a general immigration question to continue."
    )
  ).toBeVisible();
  await expect(chatShell.findRelatedCasesButton).toBeDisabled();

  expect(chatApi.chatRequestCount()).toBe(1);
  expect(chatApi.caseSearchRequestCount()).toBe(0);
});
