const { chromium } = require('C:/Users/hBaillie/AppData/Local/OpenAI/Codex/runtimes/cua_node/03b1cdac8af3a530/bin/node_modules/playwright');
const fs = require('fs');

(async () => {
  const browser = await chromium.launch({
    executablePath: 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
    headless: true,
  });
  const results = [];
  for (const width of [375, 768, 1440]) {
    for (const colorScheme of ['light', 'dark']) {
      const context = await browser.newContext({ viewport: { width, height: 900 }, colorScheme, reducedMotion: 'reduce' });
      const page = await context.newPage();
      await page.addInitScript((scheme) => localStorage.setItem('st-theme', scheme), colorScheme);
      await page.goto('http://127.0.0.1:4173/app/dashboard', { waitUntil: 'networkidle' });
      await page.screenshot({ path: `output/playwright/meridian-${width}-${colorScheme}.png`, fullPage: true });
      const audit = await page.evaluate(() => {
        const root = document.documentElement;
        const controls = [...document.querySelectorAll('button, a, input, select')].filter((el) => {
          const style = getComputedStyle(el);
          const rect = el.getBoundingClientRect();
          return style.display !== 'none' && style.visibility !== 'hidden' && rect.width > 0 && rect.height > 0;
        });
        return {
          title: document.title,
          brand: document.querySelector('.app-brand')?.textContent?.trim(),
          overflow: root.scrollWidth > root.clientWidth,
          undersized: controls.map((el) => ({ text: el.getAttribute('aria-label') || el.textContent.trim(), h: el.getBoundingClientRect().height, w: el.getBoundingClientRect().width })).filter((x) => x.h < 44 && x.w < 44),
          reducedMotion: getComputedStyle(document.querySelector('.app-tab')).transitionDuration,
        };
      });
      await page.keyboard.press('Tab');
      const focus = await page.evaluate(() => ({ tag: document.activeElement?.tagName, text: document.activeElement?.textContent?.trim(), outline: getComputedStyle(document.activeElement).outlineStyle }));
      const action = page.getByRole('link', { name: 'View transactions' });
      await action.click();
      await page.waitForURL('**/app/transactions');
      const route = new URL(page.url()).pathname;
      await page.screenshot({ path: `output/playwright/meridian-transactions-${width}-${colorScheme}.png`, fullPage: true });
      results.push({ width, colorScheme, audit, focus, route });
      await context.close();
    }
  }
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 }, colorScheme: 'light', reducedMotion: 'reduce' });
  const page = await context.newPage();
  await page.goto('http://127.0.0.1:4173/app/dashboard', { waitUntil: 'networkidle' });
  await page.evaluate(() => { document.documentElement.style.zoom = '2'; });
  const zoom = await page.evaluate(() => ({ overflow: document.documentElement.scrollWidth > document.documentElement.clientWidth, scrollWidth: document.documentElement.scrollWidth, clientWidth: document.documentElement.clientWidth }));
  await page.screenshot({ path: 'output/playwright/meridian-200pct.png', fullPage: true });
  results.push({ zoom200: zoom });
  await context.close();
  await browser.close();
  fs.writeFileSync('output/playwright/meridian-qa.json', JSON.stringify(results, null, 2));
  console.log(JSON.stringify(results, null, 2));
})().catch((error) => { console.error(error); process.exit(1); });
