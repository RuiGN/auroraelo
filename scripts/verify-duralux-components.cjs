/* Disposable local preview only; cookies contain synthetic test identities. */
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const base = 'http://127.0.0.1:8765';
const output = 'docs/migration/evidence/visual-components';
const cookies = JSON.parse(fs.readFileSync('.migration-runtime/preview-cookies.json'));
fs.mkdirSync(output, { recursive: true });

(async () => {
  const browser = await chromium.launch({ headless: true });
  const results = [];
  const errors = [];
  try {
    for (const width of [1440, 390]) {
      for (const theme of ['light']) { // theme pinned to light
        const context = await browser.newContext({ viewport: { width, height: 900 }, colorScheme: theme, reducedMotion: 'reduce' });
        await context.addCookies([{ name: 'sessionid', value: cookies.clinic_admin, url: base }]);
        const page = await context.newPage();
        page.on('dialog', dialog => dialog.accept());
        page.on('pageerror', error => errors.push(error.message));
        page.on('response', response => { if (response.status() >= 400) errors.push(`${response.status()} ${response.url()}`); });
        assert.equal((await page.goto(`${base}/design-system/`)).status(), 200);
        await page.evaluate(() => document.fonts.ready);
        assert.equal(await page.locator('html').getAttribute('data-bs-theme'), 'light');
        assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), 'Horizontal overflow');
        assert(await page.getByRole('button', { name: 'Ação indisponível' }).isDisabled());
        for (const kind of ['restricted', 'error', 'empty', 'loading']) {
          assert(await page.locator(`[data-state-kind="${kind}"]`).isVisible());
        }
        const list = page.locator(width < 768 ? '.product-mobile-row-list' : '.product-table-desktop');
        assert(await list.isVisible());
        assert(await list.getByRole('link', { name: /Ordenar por/ }).count() > 0);
        if (width < 768) {
          assert(await list.getByRole('link', { name: /ordem decrescente.*ordem atual crescente/ }).isVisible());
          assert.equal(await list.locator('[aria-current=true]').count(), 1);
        }
        await page.locator('.product-pagination').evaluate(element => element.closest('section').classList.add('nxl-container'));
        for (const link of await page.locator('.product-pagination .page-link').all()) {
          assert(await link.evaluate(element => element.scrollWidth <= element.clientWidth && element.getBoundingClientRect().height >= 44), 'Pagination label clipped or target too small');
        }
        await page.locator('.product-pagination').screenshot({ path: `${output}/pagination-${width}-${theme}.png` });
        for (const [name, selector] of [['Abrir modal', '#modal-exemplo'], ['Abrir painel lateral', '#painel-exemplo']]) {
          await page.getByRole('button', { name, exact: true }).click();
          await page.locator(`${selector}.show`).waitFor();
          await page.keyboard.press('Escape');
          await page.locator(`${selector}.show`).waitFor({ state: 'hidden' });
        }
        await Promise.all([page.waitForNavigation(), page.getByRole('button', { name: 'Salvar exemplo' }).click()]);
        assert.equal(await page.locator('input[name="display_name"]').getAttribute('aria-invalid'), 'true');
        assert.equal(await page.evaluate(() => document.activeElement.id), 'id_display_name');
        for (const control of await page.locator('#formularios input[type=checkbox], #formularios input[type=radio]').all()) {
          assert(await control.evaluate(element => element.offsetHeight <= 24 && (element.closest('label') || element.parentElement).getBoundingClientRect().height >= 44), 'Choice control distorted or target too small');
        }
        await page.locator('#formularios').evaluate(element => element.scrollIntoView({ block: 'start' }));
        await page.screenshot({ path: `${output}/form-errors-${width}-${theme}.png` });
        await page.locator('fieldset').first().evaluate(element => element.scrollIntoView({ block: 'center' }));
        await page.screenshot({ path: `${output}/choice-controls-${width}-${theme}.png` });
        await page.getByLabel('Nome de exibição', { exact: false }).fill('Unidade de validação');
        await page.getByLabel('Data de início', { exact: false }).fill('2026-09-08');
        await page.getByRole('radio', { name: 'E-mail', exact: true }).check();
        await Promise.all([page.waitForNavigation(), page.getByRole('button', { name: 'Salvar exemplo' }).click()]);
        assert(await page.getByText('Exemplo validado pelo servidor.', { exact: false }).isVisible());
        await page.goto(`${base}/design-system/?q=sem-correspondencia-xyz`);
        assert(await page.locator(width < 768 ? '.product-mobile-row-list' : '.product-table-desktop').getByText('Nenhum registro disponível.').isVisible());
        results.push({ width, theme, csrfPost: true, fieldErrorFocus: true, emptyTable: true, mobileSort: true, overlays: true });
        await context.close();
        const restricted = await browser.newContext({ viewport: { width, height: 900 }, colorScheme: theme });
        await restricted.addCookies([{ name: 'sessionid', value: cookies.patient, url: base }]);
        const denied = await restricted.newPage();
        denied.on('pageerror', error => errors.push(error.message));
        assert.equal((await denied.goto(`${base}/design-system/`)).status(), 403);
        assert(await denied.getByRole('heading', { level: 1 }).isVisible());
        assert(await denied.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
        results.push({ width, theme, unprivilegedCatalogDenied: true });
        await restricted.close();
      }
    }
    // Exercise bfcache restoration and non-field focus independently of backend fixtures.
    const page = await browser.newPage();
    await page.setContent('<div data-focus-error-summary tabindex="-1">Erro geral</div><form data-form-guard><button data-submit-button disabled>Indisponível</button></form><form data-form-guard><button data-submit-button>Salvar</button></form>');
    await page.addScriptTag({ path: 'static/duralux/js/form-behaviors.js' });
    await page.evaluate(() => document.dispatchEvent(new Event('DOMContentLoaded')));
    assert(await page.locator('[data-focus-error-summary]').evaluate(element => element === document.activeElement));
    await page.evaluate(() => {
      document.querySelectorAll('[data-submit-button]').forEach(button => { button.disabled = true; });
      window.dispatchEvent(new Event('pageshow'));
    });
    assert(await page.locator('[data-submit-button]').nth(0).isDisabled());
    assert(await page.locator('[data-submit-button]').nth(1).isEnabled());
    results.push({ isolatedFormBehavior: 'passed', generalErrorFocus: true, originalDisabledStateRestored: true });
    assert.deepEqual(errors, []);
    fs.writeFileSync(`${output}/results.json`, JSON.stringify({ results, errors }, null, 2));
    console.log(`${results.length} component scenarios passed`);
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
