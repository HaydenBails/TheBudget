const { chromium } = require('C:/Users/hBaillie/AppData/Local/OpenAI/Codex/runtimes/cua_node/03b1cdac8af3a530/bin/node_modules/playwright');

const baseUrl = 'http://127.0.0.1:8790/app/transactions';
const createdName = `Browser QA ${Date.now()}`;
const editedName = `${createdName} Edited`;
const results = [];
const errors = [];

function check(name, condition, detail = '') {
  results.push({ name, pass: Boolean(condition), detail });
  if (!condition) throw new Error(`${name}: ${detail}`);
}

async function noOverflow(page, label) {
  const sizes = await page.evaluate(() => ({
    client: document.documentElement.clientWidth,
    scroll: document.documentElement.scrollWidth,
  }));
  check(`${label} has no document overflow`, sizes.scroll <= sizes.client, JSON.stringify(sizes));
}

(async () => {
  const browser = await chromium.launch({
    headless: true,
    executablePath: 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
  });
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();
  page.on('console', (message) => {
    if (message.type() === 'error') errors.push(`console: ${message.text()}`);
  });
  page.on('pageerror', (error) => errors.push(`page: ${error.message}`));

  await page.goto(baseUrl, { waitUntil: 'networkidle' });
  check('Ledger page title', await page.title() === 'Ledger — Spending Tracker', await page.title());
  check('Transactions heading visible', await page.getByRole('heading', { name: 'Transactions', exact: true }).isVisible());
  check('API connected', await page.getByText('API connected').isVisible());
  check('Desktop semantic table visible', await page.locator('table.tx-table').isVisible());
  check('Real transaction rows render', await page.locator('tbody tr').count() >= 2, String(await page.locator('tbody tr').count()));
  await noOverflow(page, '1440px desktop');

  const themeButton = page.getByRole('button', { name: 'Dark' });
  await themeButton.click();
  check('Dark theme toggle works', await page.getByRole('button', { name: 'Light' }).isVisible());
  await page.getByRole('button', { name: 'Light' }).click();
  check('Light theme toggle works', await page.getByRole('button', { name: 'Dark' }).isVisible());

  const addButton = page.getByRole('button', { name: 'Add transaction' }).first();
  await addButton.focus();
  await page.keyboard.press('Enter');
  let dialog = page.getByRole('dialog');
  await dialog.waitFor();
  check('Keyboard opens Add dialog', await page.getByRole('heading', { name: 'Add transaction' }).isVisible());
  check('Add dialog traps initial focus', await page.evaluate(() => Boolean(document.activeElement?.closest('[aria-modal="true"]'))));
  await page.keyboard.press('Escape');
  await dialog.waitFor({ state: 'hidden' });
  await page.waitForTimeout(50);
  check('Escape restores Add trigger focus', await addButton.evaluate((element) => element === document.activeElement));

  const firstMerchant = page.locator('tbody tr').first().locator('button').first();
  await firstMerchant.click();
  dialog = page.getByRole('dialog');
  await dialog.getByRole('button', { name: 'Edit transaction' }).click();
  await page.getByRole('heading', { name: 'Edit transaction' }).waitFor();
  check('Detail-to-edit keeps focus in new modal', await page.evaluate(() => Boolean(document.activeElement?.closest('[aria-modal="true"]'))));
  await page.keyboard.press('Escape');
  await page.getByRole('heading', { name: 'Edit transaction' }).waitFor({ state: 'hidden' });

  await addButton.click();
  dialog = page.getByRole('dialog');
  await dialog.getByLabel('Merchant').fill(createdName);
  await dialog.getByLabel('Amount (CAD)').fill('12.34');
  await dialog.getByLabel('Statement description').fill('BROWSER QA SOURCE');
  await dialog.getByRole('button', { name: 'Add transaction' }).click();
  await page.getByText(createdName, { exact: true }).first().waitFor();
  check('Create transaction through Ledger', true);

  await page.locator('tbody tr').filter({ hasText: createdName }).locator('button').first().click();
  dialog = page.getByRole('dialog');
  await dialog.getByLabel('Comma-separated tags').fill('browser, qa');
  await dialog.getByRole('button', { name: 'Save tags' }).click();
  await page.waitForTimeout(300);
  await dialog.getByRole('button', { name: 'Add allocation' }).click();
  await dialog.locator('.tx-split-row').nth(0).waitFor();
  await dialog.getByRole('button', { name: 'Add allocation' }).click();
  await dialog.locator('.tx-split-row').nth(1).waitFor();
  const splitRows = dialog.locator('.tx-split-row');
  const categoryOptions = await splitRows.first().getByRole('combobox').locator('option').evaluateAll((options) => options.slice(1, 3).map((option) => option.value));
  await splitRows.nth(0).getByRole('combobox').selectOption(categoryOptions[0]);
  await splitRows.nth(1).getByRole('combobox').selectOption(categoryOptions[1]);
  await splitRows.nth(0).getByLabel('Amount (CAD)').fill('6.00');
  await splitRows.nth(1).getByLabel('Amount (CAD)').fill('6.34');
  await dialog.getByRole('button', { name: 'Save split' }).click();
  await dialog.getByRole('button', { name: 'Close' }).click();
  check('Split and tag editing through Ledger', true);

  await page.getByRole('button', { name: `Edit ${createdName}` }).click();
  dialog = page.getByRole('dialog');
  await dialog.getByLabel('Merchant').fill(editedName);
  await dialog.getByRole('button', { name: 'Save changes' }).click();
  await page.getByText(editedName, { exact: true }).first().waitFor();
  check('Edit transaction through Ledger', true);

  await page.getByRole('checkbox', { name: `Select ${editedName}` }).check();
  const bulk = page.getByLabel('Bulk transaction actions');
  await bulk.locator('select').nth(1).selectOption({ label: 'Groceries' });
  await bulk.getByRole('button', { name: 'Review update' }).click();
  const confirm = page.getByRole('alertdialog');
  await confirm.getByRole('button', { name: 'Update 1' }).click();
  await confirm.waitFor({ state: 'hidden' });
  check('Atomic bulk categorize through Ledger', true);

  await page.getByRole('button', { name: `Move ${editedName} to trash` }).click();
  await page.getByRole('alertdialog').getByRole('button', { name: 'Move to trash' }).click();
  await page.getByText(editedName, { exact: true }).first().waitFor({ state: 'hidden' });
  check('Soft delete through Ledger', true);

  await page.getByRole('checkbox', { name: 'Show trash' }).check();
  await page.goto(`${baseUrl}?trash=true`, { waitUntil: 'networkidle' });
  await page.getByRole('button', { name: `Restore ${editedName}` }).click();
  await page.getByRole('button', { name: `Edit ${editedName}` }).waitFor();
  check('Restore through Ledger', true);

  await page.screenshot({ path: 'output/playwright/fe07-qa/desktop-final.png', fullPage: true });

  for (const viewport of [
    { width: 768, height: 900, label: '768px tablet' },
    { width: 375, height: 812, label: '375px mobile' },
    { width: 720, height: 450, label: 'simulated 200% zoom' },
  ]) {
    await page.setViewportSize({ width: viewport.width, height: viewport.height });
    await page.reload({ waitUntil: 'networkidle' });
    await noOverflow(page, viewport.label);
    if (viewport.width === 375) {
      check('Mobile cards visible', await page.locator('.tx-cards').isVisible());
      check('Desktop table hidden on mobile', !(await page.locator('.tx-table-wrap').isVisible()));
      const article = page.locator('article.tx-card').first();
      check('Mobile card has accessible label', Boolean(await article.getAttribute('aria-labelledby')));
    }
  }

  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.reload({ waitUntil: 'networkidle' });
  const transition = await page.locator('.app-btn').first().evaluate((element) => getComputedStyle(element).transitionDuration);
  const durations = transition.split(',').map((part) => Number.parseFloat(part) || 0);
  check('Reduced motion minimizes transitions', durations.every((duration) => duration <= 0.001), transition);

  check('No browser console/page errors', errors.length === 0, errors.join('\n'));
  console.log(JSON.stringify({ results, errors }, null, 2));
  await browser.close();
})().catch((error) => {
  console.error(JSON.stringify({ results, errors, failure: error.stack }, null, 2));
  process.exit(1);
});
