/* Run only against a disposable local preview with synthetic session cookies.
 * PLAYWRIGHT_MODULE=<module path> node scripts/verify-duralux-shell.cjs
 * The preview fixture and cookie file are ignored and never production settings.
 */
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const base = 'http://127.0.0.1:8765';
const cookies = JSON.parse(fs.readFileSync('.migration-runtime/preview-cookies.json'));
const output = 'docs/migration/evidence/visual-foundation';
fs.mkdirSync(output, { recursive: true });

(async () => {
  const browser = await chromium.launch({ headless: true });
  const results = [];
  const errors = [];
  try {
    for (const layout of ['', 'detached/']) {
      for (const width of [1440, 390]) {
        for (const theme of ['light', 'dark']) {
          const context = await browser.newContext({ viewport: { width, height: 900 }, colorScheme: theme, reducedMotion: 'reduce' });
          await context.addCookies([{ name: 'sessionid', value: cookies.clinic_admin, url: base }]);
          const page = await context.newPage();
          page.on('pageerror', e => errors.push(e.message));
          page.on('response', r => { if (r.status() >= 400) errors.push(`${r.status()} ${r.url()}`); });
          await page.goto(`${base}/workspace/${layout}`);
          await page.evaluate(() => document.fonts.ready);
          assert.equal(await page.title(), 'Área de trabalho · Mindcare');
          assert.equal(await page.locator('html').getAttribute('data-bs-theme'), theme);
          assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), 'Horizontal overflow');
          const sidebar = page.locator('[data-mobile-sidebar]');
          if (width < 1200) {
            assert(await sidebar.evaluate(e => e.inert));
            await page.locator('[data-sidebar-open]').focus();
            await page.keyboard.press('Space');
            assert.equal(await sidebar.getAttribute('aria-modal'), 'true');
            assert(await page.locator('.nxl-container').evaluate(e => e.inert));
            assert(await page.locator('[data-sidebar-close]').evaluate(e => e === document.activeElement));
          } else {
            assert.equal(await sidebar.getAttribute('aria-modal'), null);
            assert(!(await sidebar.evaluate(e => e.inert)));
          }
          const accordion = page.getByRole('button', { name: 'Administração', exact: true });
          await accordion.focus();
          await page.keyboard.press('Space');
          assert.equal(await accordion.getAttribute('aria-expanded'), 'true');
          const setup = sidebar.getByRole('link', { name: 'Configurar clínica', exact: true });
          assert(await setup.isVisible());
          await page.screenshot({ path: `${output}/${layout ? 'detached' : 'vertical'}-${width}-${theme}.png`, animations: 'disabled', fullPage: true });
          if (width < 1200) {
            // Tab must wrap within the dialog, including backwards from its first link.
            await sidebar.locator('.b-brand').focus();
            await page.keyboard.press('Shift+Tab');
            assert(await sidebar.getByRole('button', { name: 'Atendimento', exact: true }).evaluate(e => e === document.activeElement));
            await page.keyboard.press('Tab');
            assert(await sidebar.locator('.b-brand').evaluate(e => e === document.activeElement));
            await page.keyboard.press('Escape');
            assert.equal(await sidebar.getAttribute('aria-modal'), null);
            assert(await page.locator('[data-sidebar-open]').evaluate(e => e === document.activeElement));
            assert(!(await page.locator('.nxl-container').evaluate(e => e.inert)));
            await page.screenshot({ path: `${output}/${layout ? 'detached' : 'vertical'}-${width}-${theme}-content.png`, animations: 'disabled', fullPage: true });
            await page.keyboard.press('Escape');
            await page.locator('[data-sidebar-open]').click();
            await page.setViewportSize({ width: 1440, height: 900 });
            await page.waitForFunction(() => !document.querySelector('[data-mobile-sidebar]').hasAttribute('aria-modal'));
            assert(!(await sidebar.evaluate(e => e.inert)));
          } else {
            await page.locator('[data-sidebar-mini]').click();
            assert(await page.locator('html').evaluate(e => e.classList.contains('minimenu')));
            assert(await sidebar.getByRole('button', { name: 'Administração', exact: true }).isVisible());
            assert.equal(await sidebar.getByRole('button', { name: 'Administração', exact: true }).getAttribute('aria-expanded'), 'false');
            await page.setViewportSize({ width: 390, height: 900 });
            await page.waitForFunction(() => !document.documentElement.classList.contains('minimenu'));
            await page.locator('[data-sidebar-open]').click();
            assert(await sidebar.getByText('Administração', { exact: true }).isVisible());
            await page.keyboard.press('Escape');
          }
          // The theme is pinned to light: no toggle may appear and the
          // attribute must survive a reload even in a dark colorScheme.
          assert.equal(await page.locator('[data-theme-toggle]').count(), 0);
          assert.equal(await page.locator('html').getAttribute('data-bs-theme'), 'light');
          await page.reload();
          assert.equal(await page.locator('html').getAttribute('data-bs-theme'), 'light');
          results.push({ layout: layout || 'vertical', width, theme, result: 'passed' });
          await context.close();
        }
      }
    }
    for (const width of [1440, 390]) {
      for (const theme of ['light', 'dark']) {
        const context = await browser.newContext({ viewport: { width, height: 900 }, colorScheme: theme, reducedMotion: 'reduce' });
        const page = await context.newPage();
        page.on('pageerror', e => errors.push(e.message));
        await page.goto(`${base}/accounts/login/`);
        assert(await page.getByRole('heading', { level: 1 }).isVisible());
        assert.equal(await page.locator('.card .card').count(), 0);
        assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
        await page.getByRole('button', { name: 'Entrar', exact: true }).click();
        await page.waitForLoadState();
        assert(await page.locator('[aria-invalid="true"]').count() > 0);
        assert(await page.locator('[aria-invalid="true"]').first().evaluate(e => e === document.activeElement));
        await page.screenshot({ path: `${output}/login-error-${width}-${theme}.png`, fullPage: true, animations: 'disabled' });
        results.push({ page: 'login-validation', width, theme, result: 'passed' });
        await context.close();
      }
    }
    assert.deepEqual(errors, []);
    fs.writeFileSync(`${output}/results.json`, JSON.stringify({ results, errors }, null, 2) + '\n');
    console.log(`${results.length} browser scenarios passed; no page errors or failed workspace assets.`);
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
