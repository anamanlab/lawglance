import { ChatShellPage } from "../pages/chat-shell.page";
import { expect, test } from "../fixtures/test-fixtures";

test.describe("chat shell accessibility and visual regression", () => {
  test("quick prompt group keeps accessible structure", async ({ page }) => {
    const chatShell = new ChatShellPage(page);
    await chatShell.goto();

    await expect(page.getByRole("group", { name: "Quick prompts" })).toMatchAriaSnapshot(`
      - group "Quick prompts":
        - button "What are the eligibility basics for Express Entry?"
        - button "What documents are required for a study permit?"
        - button "How does sponsorship for a spouse work in Canada?"
    `);
  });

  test("chat shell initial visual baseline", async ({ page }, testInfo) => {
    const chatShell = new ChatShellPage(page);
    await chatShell.goto();

    const shellContainer = page
      .locator("section")
      .filter({ has: page.getByText("IMMCAD Assistant") })
      .first();

    await expect(shellContainer).toHaveScreenshot(
      `chat-shell-initial-${testInfo.project.name}.png`,
      {
      animations: "disabled",
      maxDiffPixels: 120,
      }
    );
  });
});
