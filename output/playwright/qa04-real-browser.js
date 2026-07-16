const { chromium } = require('C:/Users/hBaillie/AppData/Local/OpenAI/Codex/runtimes/cua_node/03b1cdac8af3a530/bin/node_modules/playwright');
const fs = require('fs');
const fixture = 'C:/Users/hBaillie/Desktop/Persoonal Files/budgey/TheBudget/fixtures/statements/td/td_full_matrix.pdf';

(async () => {
  const browser = await chromium.launch({ executablePath: 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe', headless: true });
  const results = [];
  for (const width of [375, 768, 1440]) {
    for (const theme of ['light', 'dark']) {
      const context = await browser.newContext({ viewport: { width, height: 1000 }, colorScheme: theme, reducedMotion: 'reduce' });
      const page = await context.newPage(); page.setDefaultTimeout(15000);
      const errors = []; page.on('pageerror', (e) => errors.push(e.message)); page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()); });
      await page.addInitScript(({ theme }) => { localStorage.setItem('st-theme', theme); localStorage.setItem('st-current-profile', '1'); }, { theme });
      await page.goto('http://127.0.0.1:8791/app/dashboard', { waitUntil: 'domcontentloaded' });
      await page.getByRole('link', { name: 'Import statement' }).click();
      await page.getByRole('heading', { name: 'Import statement' }).waitFor();
      await page.screenshot({ path: `output/playwright/qa04-real-${width}-${theme}.png`, fullPage: true });
      await page.keyboard.press('Tab');
      results.push({ width, theme, route: new URL(page.url()).pathname, overflow: await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth), reducedMotion: await page.locator('.app-tab').first().evaluate((el) => getComputedStyle(el).transitionDuration), focusedOutline: await page.evaluate(() => getComputedStyle(document.activeElement).outlineStyle), errors });
      await context.close();
    }
  }

  const context = await browser.newContext({ viewport: { width: 1440, height: 1000 }, colorScheme: 'light', reducedMotion: 'reduce' });
  const page = await context.newPage(); page.setDefaultTimeout(30000);
  const errors = []; page.on('pageerror', (e) => errors.push(e.message)); page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()); });
  await page.addInitScript(() => localStorage.setItem('st-current-profile', '1'));
  await page.goto('http://127.0.0.1:8791/app/dashboard', { waitUntil: 'domcontentloaded' });
  await page.getByRole('link', { name: 'Import statement' }).click();
  await page.locator('input[type=file]').setInputFiles(fixture);
  await page.getByRole('button', { name: 'Preview statement' }).click();
  await page.getByRole('heading', { name: /Review before import|Duplicate statement blocked/ }).waitFor();
  const previewHeading = await page.getByRole('heading', { name: /Review before import|Duplicate statement blocked/ }).innerText();
  const previewFocused = await page.evaluate(() => document.activeElement?.textContent?.trim());
  await page.screenshot({ path: 'output/playwright/qa04-real-preview.png', fullPage: true });
  await page.evaluate(() => { document.documentElement.style.zoom = '2'; });
  const zoom200 = await page.evaluate(() => ({ overflow: document.documentElement.scrollWidth > document.documentElement.clientWidth, scrollWidth: document.documentElement.scrollWidth, clientWidth: document.documentElement.clientWidth }));
  await page.screenshot({ path: 'output/playwright/qa04-real-preview-200pct.png', fullPage: true });
  await page.evaluate(() => { document.documentElement.style.zoom = '1'; });
  const ack = page.getByRole('checkbox'); if (await ack.count()) await ack.check();
  const commit = page.getByRole('button', { name: /^Import \d+ transactions$/ });
  const commitEnabled = await commit.isEnabled();
  await commit.click();
  await page.getByRole('heading', { name: 'Transactions added' }).waitFor();
  const successFocused = await page.evaluate(() => document.activeElement?.textContent?.trim());
  const successText = await page.locator('.im-success').innerText();
  await page.screenshot({ path: 'output/playwright/qa04-real-success.png', fullPage: true });
  await page.getByRole('link', { name: 'View transactions' }).click();
  await page.waitForURL('**/app/transactions');
  await page.getByRole('heading', { name: 'Transactions' }).waitFor();
  const transactionsRoute = new URL(page.url()).pathname;
  const transactionRows = await page.locator('.tx-row').count();
  results.push({ realWorkflow: { previewHeading, previewFocused, zoom200, commitEnabled, successFocused, successText, transactionsRoute, transactionRows, errors } });
  await context.close(); await browser.close();
  fs.writeFileSync('output/playwright/qa04-real-browser.json', JSON.stringify(results, null, 2)); console.log(JSON.stringify(results, null, 2));
})().catch((error) => { console.error(error); process.exit(1); });
