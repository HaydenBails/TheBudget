const { chromium } = require('C:/Users/hBaillie/AppData/Local/OpenAI/Codex/runtimes/cua_node/03b1cdac8af3a530/bin/node_modules/playwright');

(async () => {
  const browser = await chromium.launch({
    headless: true,
    executablePath: 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
  });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  const errors = [];
  page.on('console', (message) => {
    if (message.type() === 'error') errors.push(`console: ${message.text()}`);
  });
  page.on('pageerror', (error) => errors.push(`page: ${error.message}`));
  await page.goto('http://127.0.0.1:8790/app/transactions', { waitUntil: 'networkidle' });
  await page.getByRole('button', { name: /MarketQA GROCERY/ }).click();
  const dialog = page.getByRole('dialog');
  console.log(JSON.stringify({
    dialogText: await dialog.innerText(),
    buttons: await dialog.getByRole('button').allTextContents(),
    inputs: await dialog.locator('input').count(),
    active: await page.evaluate(() => document.activeElement?.getAttribute('aria-label') || document.activeElement?.textContent),
    errors,
  }, null, 2));
  await page.screenshot({ path: 'output/playwright/fe07-qa/desktop.png', fullPage: true });
  await browser.close();
})().catch((error) => {
  console.error(error);
  process.exit(1);
});
