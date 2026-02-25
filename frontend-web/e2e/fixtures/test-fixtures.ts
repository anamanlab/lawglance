import { test as base } from "@playwright/test";

import { installChatApiStubs, type ChatApiRecorder } from "../support/network-stubs";

type E2EFixtures = {
  chatApi: ChatApiRecorder;
};

export const test = base.extend<E2EFixtures>({
  chatApi: async ({ page }, use) => {
    const chatApi = await installChatApiStubs(page);
    await use(chatApi);
  },
});

export { expect } from "@playwright/test";
