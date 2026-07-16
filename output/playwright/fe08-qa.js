const { chromium } = require('C:/Users/hBaillie/AppData/Local/OpenAI/Codex/runtimes/cua_node/03b1cdac8af3a530/bin/node_modules/playwright');
const fs = require('fs');

const now = '2026-07-16T12:00:00Z';
const profile = { id: 1, name: 'Household', base_currency: 'CAD', is_archived: false, created_at: now, updated_at: now };
const account = { id: 7, profile_id: 1, issuer: 'TD', display_name: 'TD Visa', color: '#4f5fe7', last4: '4242', currency: 'CAD', account_fingerprint: null, is_archived: false, created_at: now, updated_at: now };
const preview = {
  id: 41, profile_id: 1, account_id: 7, issuer: 'TD', source_filename: 'td-statement.pdf', parser_name: 'td_credit_card', parser_version: '1.0.0',
  statement_start_date: '2026-06-01', statement_end_date: '2026-06-30', currency: 'CAD', status: 'ready', validation_status: 'needs_review', duplicate_decision: 'potential_overlap', duplicate_of_import_id: null,
  transaction_count: 3, purchase_count: 2, credit_count: 0, payment_count: 1, fee_interest_count: 0, unresolved_count: 1,
  expected_total_cents: 5899, parsed_total_cents: 5899, reconciliation_delta_cents: 0, purchase_total_cents: 15899, credit_total_cents: 0, payment_total_cents: -10000, fee_interest_total_cents: 0,
  suggested_account_id: 7,
  warnings: [{ id: 1, code: 'potential_transaction_overlap', severity: 'warning', message: 'One row may overlap an existing transaction.', source_row_reference: 'row-2' }],
  staged_transactions: [
    { id: 1, source_row_reference: 'row-1', date: '2026-06-04', posted_date: '2026-06-05', raw_description: 'GROCERY MARKET', merchant: 'Grocery Market', amount_cents: 7299, currency: 'CAD', direction: 'debit', type: 'purchase', included_in_spending: true, exclusion_reason: null, original_foreign_amount_cents: null, original_foreign_currency: null, exchange_rate: null, occurrence_index: 0, duplicate_decision: 'new', status: 'accepted' },
    { id: 2, source_row_reference: 'row-2', date: '2026-06-10', posted_date: '2026-06-11', raw_description: 'TRANSIT PASS', merchant: 'Transit Pass', amount_cents: 8600, currency: 'CAD', direction: 'debit', type: 'purchase', included_in_spending: true, exclusion_reason: null, original_foreign_amount_cents: null, original_foreign_currency: null, exchange_rate: null, occurrence_index: 0, duplicate_decision: 'potential_overlap', status: 'needs_review' },
    { id: 3, source_row_reference: 'row-3', date: '2026-06-20', posted_date: '2026-06-20', raw_description: 'PAYMENT', merchant: 'Payment', amount_cents: -10000, currency: 'CAD', direction: 'credit', type: 'payment', included_in_spending: false, exclusion_reason: 'payment', original_foreign_amount_cents: null, original_foreign_currency: null, exchange_rate: null, occurrence_index: 0, duplicate_decision: 'new', status: 'accepted' },
  ],
};

async function mockApi(page) {
  await page.route('**/*', async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const path = url.pathname;
    if (path === '/health') return route.fulfill({ json: { status: 'ok', version: '0.0.1' } });
    if (path === '/profiles' && request.method() === 'GET') return route.fulfill({ json: [profile] });
    if (path === '/profiles/1/accounts' && request.method() === 'GET') return route.fulfill({ json: [account] });
    if (path === '/profiles/1/imports/preview' && request.method() === 'POST') return route.fulfill({ status: 201, json: preview });
    if (path === '/profiles/1/imports/41/commit' && request.method() === 'POST') return route.fulfill({ json: { import_id: 41, status: 'committed', created_count: 3, linked_duplicate_count: 0, transaction_ids: [101, 102, 103] } });
    return route.continue();
  });
}

(async () => {
  const browser = await chromium.launch({ executablePath: 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe', headless: true });
  const results = [];
  for (const width of [375, 768, 1440]) {
    for (const colorScheme of ['light', 'dark']) {
      const context = await browser.newContext({ viewport: { width, height: 1000 }, colorScheme, reducedMotion: 'reduce' });
      const page = await context.newPage();
      page.setDefaultTimeout(8000);
      await mockApi(page);
      await page.addInitScript(({ colorScheme }) => { localStorage.setItem('st-theme', colorScheme); localStorage.setItem('st-current-profile', '1'); }, { colorScheme });
      await page.goto('http://127.0.0.1:4173/app/dashboard', { waitUntil: 'domcontentloaded' });
      await page.getByRole('link', { name: 'Import statement' }).click();
      await page.getByRole('heading', { name: 'Import statement' }).waitFor();
      await page.screenshot({ path: `output/playwright/fe08-${width}-${colorScheme}.png`, fullPage: true });
      const audit = await page.evaluate(() => {
        const visible = [...document.querySelectorAll('button, a, input, select')].filter((el) => { const r = el.getBoundingClientRect(); const s = getComputedStyle(el); return r.width > 0 && r.height > 0 && s.visibility !== 'hidden'; });
        return {
          route: location.pathname,
          overflow: document.documentElement.scrollWidth > document.documentElement.clientWidth,
          undersized: visible.map((el) => ({ text: el.getAttribute('aria-label') || el.textContent.trim(), w: el.getBoundingClientRect().width, h: el.getBoundingClientRect().height })).filter((x) => x.w < 44 && x.h < 44),
          reducedMotion: getComputedStyle(document.querySelector('.app-tab')).transitionDuration,
        };
      });
      await page.keyboard.press('Tab');
      const focus = await page.evaluate(() => ({ text: document.activeElement?.textContent?.trim(), outline: getComputedStyle(document.activeElement).outlineStyle }));
      results.push({ width, colorScheme, audit, focus });
      await context.close();
    }
  }

  const context = await browser.newContext({ viewport: { width: 1440, height: 1000 }, colorScheme: 'light', reducedMotion: 'reduce' });
  const page = await context.newPage();
  page.setDefaultTimeout(8000);
  await mockApi(page);
  await page.addInitScript(() => localStorage.setItem('st-current-profile', '1'));
  await page.goto('http://127.0.0.1:4173/app/imports', { waitUntil: 'domcontentloaded' });
  await page.getByRole('heading', { name: 'Import statement' }).waitFor();
  await page.locator('input[type=file]').setInputFiles({ name: 'td-statement.pdf', mimeType: 'application/pdf', buffer: Buffer.from('%PDF-1.7 synthetic') });
  await page.getByRole('button', { name: 'Preview statement' }).click();
  await page.getByRole('heading', { name: 'Review before import' }).waitFor();
  const previewFocused = await page.evaluate(() => document.activeElement?.textContent?.trim());
  await page.screenshot({ path: 'output/playwright/fe08-preview.png', fullPage: true });
  const commit = page.getByRole('button', { name: /Import 3 transactions/ });
  const disabledBeforeAck = await commit.isDisabled();
  await page.getByRole('checkbox').check();
  const disabledAfterAck = await commit.isDisabled();
  await commit.click();
  await page.getByRole('heading', { name: 'Transactions added' }).waitFor();
  const successFocused = await page.evaluate(() => document.activeElement?.textContent?.trim());
  await page.screenshot({ path: 'output/playwright/fe08-success.png', fullPage: true });
  results.push({ workflow: { previewFocused, disabledBeforeAck, disabledAfterAck, successFocused, successText: await page.locator('.im-success').innerText() } });

  await page.goto('http://127.0.0.1:4173/app/imports', { waitUntil: 'domcontentloaded' });
  await page.getByRole('heading', { name: 'Import statement' }).waitFor();
  await page.evaluate(() => { document.documentElement.style.zoom = '2'; });
  const zoom = await page.evaluate(() => ({ overflow: document.documentElement.scrollWidth > document.documentElement.clientWidth, scrollWidth: document.documentElement.scrollWidth, clientWidth: document.documentElement.clientWidth }));
  await page.screenshot({ path: 'output/playwright/fe08-200pct.png', fullPage: true });
  results.push({ zoom200: zoom });
  await context.close();
  await browser.close();
  fs.writeFileSync('output/playwright/fe08-qa.json', JSON.stringify(results, null, 2));
  console.log(JSON.stringify(results, null, 2));
})().catch((error) => { console.error(error); process.exit(1); });
