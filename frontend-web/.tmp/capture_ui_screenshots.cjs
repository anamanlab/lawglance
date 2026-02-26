const fs = require('node:fs/promises');
const path = require('node:path');
const { chromium, devices } = require('@playwright/test');

async function waitForStablePage(page, url) {
  await page.goto(url, { waitUntil: 'networkidle' });
  await page.evaluate(async () => {
    if (document.fonts && document.fonts.ready) {
      await document.fonts.ready;
    }
  });
  await page.waitForTimeout(600);
}

async function safeLocatorScreenshot(locator, outPath) {
  try {
    if ((await locator.count()) > 0) {
      await locator.first().scrollIntoViewIfNeeded();
      await locator.first().screenshot({ path: outPath });
      return true;
    }
  } catch (error) {
    console.warn(`Locator screenshot failed for ${outPath}:`, error.message);
  }
  return false;
}

async function main() {
  const [url = 'http://127.0.0.1:3005', outputDir = '/tmp/immcad-ui-screenshots'] = process.argv.slice(2);
  await fs.mkdir(outputDir, { recursive: true });

  const browser = await chromium.launch({ headless: true });

  try {
    const desktopContext = await browser.newContext({ viewport: { width: 1440, height: 1100 } });
    const desktopPage = await desktopContext.newPage();
    await waitForStablePage(desktopPage, url);

    await desktopPage.screenshot({ path: path.join(outputDir, 'desktop-full.png'), fullPage: true });
    await safeLocatorScreenshot(
      desktopPage.locator('section', { hasText: 'Editorial Legal Desk' }),
      path.join(outputDir, 'desktop-hero-card.png')
    );
    await safeLocatorScreenshot(
      desktopPage.locator('section', { hasText: 'Workspace / Research Desk' }),
      path.join(outputDir, 'desktop-workspace-shell.png')
    );

    await desktopContext.close();

    const mobileContext = await browser.newContext({ ...devices['iPhone 12'] });
    const mobilePage = await mobileContext.newPage();
    await waitForStablePage(mobilePage, url);

    await mobilePage.screenshot({ path: path.join(outputDir, 'mobile-top.png') });
    await mobilePage.screenshot({ path: path.join(outputDir, 'mobile-full.png'), fullPage: true });

    await safeLocatorScreenshot(
      mobilePage.locator('section', { hasText: 'Question Draft' }),
      path.join(outputDir, 'mobile-composer-card.png')
    );
    await safeLocatorScreenshot(
      mobilePage.locator('section', { hasText: 'Case-Law Docket' }),
      path.join(outputDir, 'mobile-case-law-panel.png')
    );

    await mobileContext.close();

    const files = await fs.readdir(outputDir);
    console.log('Saved screenshots to:', outputDir);
    for (const file of files.sort()) {
      console.log(` - ${file}`);
    }
  } finally {
    await browser.close();
  }
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
