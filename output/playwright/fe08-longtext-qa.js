const { chromium } = require('C:/Users/hBaillie/AppData/Local/OpenAI/Codex/runtimes/cua_node/03b1cdac8af3a530/bin/node_modules/playwright');
const fs = require('fs');

const now = '2026-07-16T12:00:00Z';
const longAccount = `TD ${'VeryLongAccountName'.repeat(6)}`.slice(0, 100);
const longFilename = `${'verylongstatementfilename'.repeat(12)}`.slice(0, 251) + '.pdf';
const profile = { id: 1, name: 'Household', base_currency: 'CAD', is_archived: false, created_at: now, updated_at: now };
const account = { id: 7, profile_id: 1, issuer: 'TD', display_name: longAccount, color: '#4f5fe7', last4: '4242', currency: 'CAD', account_fingerprint: null, is_archived: false, created_at: now, updated_at: now };
const preview = {
  id: 41, profile_id: 1, account_id: 7, issuer: 'TD', source_filename: longFilename, parser_name: 'td_credit_card', parser_version: '1.0.0', statement_start_date: '2026-06-01', statement_end_date: '2026-06-30', currency: 'CAD', status: 'ready', validation_status: 'needs_review', duplicate_decision: 'potential_overlap', duplicate_of_import_id: null, transaction_count: 1, purchase_count: 1, credit_count: 0, payment_count: 0, fee_interest_count: 0, unresolved_count: 1, expected_total_cents: 7299, parsed_total_cents: 7299, reconciliation_delta_cents: 0, purchase_total_cents: 7299, credit_total_cents: 0, payment_total_cents: 0, fee_interest_total_cents: 0, suggested_account_id: 7,
  warnings: [{ id: 1, code: 'potential_transaction_overlap', severity: 'warning', message: 'One row may overlap an existing transaction.', source_row_reference: 'row-1' }],
  staged_transactions: [{ id: 1, source_row_reference: 'row-1', date: '2026-06-04', posted_date: '2026-06-05', raw_description: 'GROCERY MARKET', merchant: 'Grocery Market', amount_cents: 7299, currency: 'CAD', direction: 'debit', type: 'purchase', included_in_spending: true, exclusion_reason: null, original_foreign_amount_cents: null, original_foreign_currency: null, exchange_rate: null, occurrence_index: 0, duplicate_decision: 'potential_overlap', status: 'needs_review' }],
};

async function setup(page) {
  await page.route('**/*', async (route) => {
    const request = route.request(); const path = new URL(request.url()).pathname;
    if (path === '/health') return route.fulfill({ json: { status: 'ok', version: '0.0.1' } });
    if (path === '/profiles' && request.method() === 'GET') return route.fulfill({ json: [profile] });
    if (path === '/profiles/1/accounts' && request.method() === 'GET') return route.fulfill({ json: [account] });
    if (path === '/profiles/1/imports/preview') return route.fulfill({ status: 201, json: preview });
    return route.continue();
  });
  await page.addInitScript(() => localStorage.setItem('st-current-profile', '1'));
}

async function render(browser, width, zoom, suffix) {
  const context = await browser.newContext({ viewport: { width, height: 1000 }, colorScheme: 'light', reducedMotion: 'reduce' });
  const page = await context.newPage(); page.setDefaultTimeout(8000); await setup(page);
  await page.goto('http://127.0.0.1:4173/app/imports', { waitUntil: 'domcontentloaded' });
  await page.getByRole('heading', { name: 'Import statement' }).waitFor();
  await page.locator('input[type=file]').setInputFiles({ name: longFilename, mimeType: 'application/pdf', buffer: Buffer.from('%PDF-1.7 synthetic') });
  await page.getByRole('button', { name: 'Preview statement' }).click();
  await page.getByRole('heading', { name: 'Review before import' }).waitFor();
  if (zoom) await page.evaluate(() => { document.documentElement.style.zoom = '2'; });
  const audit = await page.evaluate(() => ({ overflow: document.documentElement.scrollWidth > document.documentElement.clientWidth, scrollWidth: document.documentElement.scrollWidth, clientWidth: document.documentElement.clientWidth }));
  await page.screenshot({ path: `output/playwright/fe08-long-${suffix}.png`, fullPage: true });
  await context.close(); return audit;
}

(async () => {
  const browser = await chromium.launch({ executablePath: 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe', headless: true });
  const results = { mobile375: await render(browser, 375, false, '375'), zoom200: await render(browser, 1440, true, '200pct') };
  await browser.close(); fs.writeFileSync('output/playwright/fe08-long-qa.json', JSON.stringify(results, null, 2)); console.log(JSON.stringify(results, null, 2));
})().catch((error) => { console.error(error); process.exit(1); });
