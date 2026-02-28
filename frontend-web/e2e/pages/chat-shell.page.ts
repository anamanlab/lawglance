import { expect, type Locator, type Page } from "@playwright/test";

export class ChatShellPage {
  readonly page: Page;

  constructor(page: Page) {
    this.page = page;
  }

  get promptInput(): Locator {
    return this.page.getByLabel("Ask a Canadian immigration question");
  }

  get sendButton(): Locator {
    return this.page.getByRole("button", { name: "Send" });
  }

  get findRelatedCasesButton(): Locator {
    return this.page.getByRole("button", { name: "Find related cases" });
  }

  get chatLog(): Locator {
    return this.page.getByRole("log");
  }

  async goto(): Promise<void> {
    await this.page.goto("/");
    await expect(
      this.page.getByRole("heading", { name: "IMMCAD Assistant" })
    ).toBeVisible();
    await expect(this.promptInput).toBeVisible();
  }

  async chooseQuickPrompt(prompt: string): Promise<void> {
    await this.page.getByRole("button", { name: prompt }).click();
  }

  async sendPrompt(prompt: string): Promise<void> {
    await this.promptInput.fill(prompt);
    await this.sendButton.click();
  }

  async openRelatedCases(): Promise<void> {
    await this.findRelatedCasesButton.click();
  }
}
