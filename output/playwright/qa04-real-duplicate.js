const { chromium } = require('C:/Users/hBaillie/AppData/Local/OpenAI/Codex/runtimes/cua_node/03b1cdac8af3a530/bin/node_modules/playwright');
const fs = require('fs');
const fixture = 'C:/Users/hBaillie/Desktop/Persoonal Files/budgey/TheBudget/fixtures/statements/td/td_full_matrix.pdf';

(async () => {
  const browser = await chromium.launch({ executablePath: 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe', headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 1000 }, reducedMotion: 'reduce' });
  const page = await context.newPage(); page.setDefaultTimeout(30000);
  const errors = []; page.on('pageerror', (e) => errors.push(e.message)); page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()); });
  await page.addInitScript(() => localStorage.setItem('st-current-profile', '1'));
  await page.goto('http://127.0.0.1:8791/app/transactions', { waitUntil: 'domcontentloaded' });
  await page.getByRole('heading', { name: 'Transactions' }).waitFor();
  await page.locator('.tx-table tbody tr').first().waitFor();
  const rowsBefore = await page.locator('.tx-table tbody tr').count();
  await page.screenshot({ path: 'output/playwright/qa04-real-transactions.png', fullPage: true });
  await page.getByRole('link', { name: 'Import statement' }).click();
  await page.locator('input[type=file]').setInputFiles(fixture);
  await page.getByRole('button', { name: 'Preview statement' }).click();
  await page.getByRole('heading', { name: 'Duplicate statement blocked' }).waitFor();
  const duplicateText = await page.locator('.im-preview').innerText();
  await page.screenshot({ path: 'output/playwright/qa04-real-duplicate.png', fullPage: true });
  await page.getByRole('button', { name: 'Cancel import' }).click();
  await page.getByRole('heading', { name: 'Select a PDF' }).waitFor();
  const fileCountAfterCancel = await page.locator('input[type=file]').evaluate((el) => el.files?.length ?? -1);
  const rowsAfter = await page.evaluate(async () => (await (await fetch('/profiles/1/transactions')).json()).length);
  const result = { rowsBefore, rowsAfter, fileCountAfterCancel, duplicateBlocked: duplicateText.includes('Duplicate statement blocked') && duplicateText.includes('No duplicate transactions will be created'), errors };
  await context.close(); await browser.close(); fs.writeFileSync('output/playwright/qa04-real-duplicate.json', JSON.stringify(result, null, 2)); console.log(JSON.stringify(result, null, 2));
})().catch((error) => { console.error(error); process.exit(1); });
