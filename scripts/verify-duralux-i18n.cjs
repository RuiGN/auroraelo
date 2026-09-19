/* Run only against the disposable preview with three languages explicitly enabled. */
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const base = 'http://127.0.0.1:8765';
const output = 'docs/migration/evidence/visual-i18n';
const cookies = JSON.parse(fs.readFileSync('.migration-runtime/preview-cookies.json'));
const labels = { 'pt-br': 'Idioma da interface', en: 'Interface language', es: 'Idioma de la interfaz' };
fs.mkdirSync(output, { recursive: true });

(async () => {
  const browser = await chromium.launch({ headless: true });
  const results = [];
  const errors = [];
  try {
    for (const surface of ['auth', 'header']) {
      for (const language of Object.keys(labels)) {
        for (const width of [320, 390, 1440]) {
          for (const theme of ['light']) { // theme pinned to light
            const context = await browser.newContext({ viewport: { width, height: 900 }, colorScheme: theme, locale: 'pt-BR', reducedMotion: 'reduce' });
            if (surface === 'header') await context.addCookies([{ name: 'sessionid', value: cookies.clinic_admin, url: base }]);
            const page = await context.newPage();
            page.on('pageerror', error => errors.push(error.message));
            page.on('response', response => { if (response.status() >= 400) errors.push(`${response.status()} ${response.url()}`); });
            const path = surface === 'auth' ? '/accounts/login/?next=%2Fworkspace%2F' : '/workspace/?language-check=1';
            assert.equal((await page.goto(base + path)).status(), 200);
            const toggle = page.locator(`#${surface}-language-toggle`);
            await toggle.focus();
            await page.keyboard.press('Enter');
            const menu = page.locator(`#${surface}-language-menu`);
            await menu.waitFor({ state: 'visible' });
            assert(await menu.evaluate(el => { const r = el.getBoundingClientRect(); return r.left >= -1 && r.right <= innerWidth + 1; }), 'Menu outside viewport');
            await page.locator(`#${surface}-language-choice`).selectOption(language);
            const [response] = await Promise.all([page.waitForNavigation(), page.locator('[data-language-form] button[type=submit]').click()]);
            assert.equal(response.status(), 200);
            assert.equal(response.headers()['content-language'], language);
            assert.equal(page.url(), base + path);
            assert.equal(await page.locator('html').getAttribute('lang'), language);
            assert.equal(await page.locator('html').getAttribute('dir'), 'ltr');
            assert.equal(await page.locator(`#${surface}-language-choice`).inputValue(), language);
            assert.equal(await page.evaluate(() => document.activeElement.id), `${surface}-language-toggle`);
            assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), 'Horizontal overflow');
            await toggle.click();
            assert.equal(await page.locator(`[for="${surface}-language-choice"]`).innerText(), labels[language]);
            await page.evaluate(() => document.fonts.ready);
            await page.evaluate(() => scrollTo(0, 0));
            await page.screenshot({ path: `${output}/${surface}-${language}-${width}-${theme}.png` });
            const reloaded = await page.reload();
            assert.equal(reloaded.headers()['content-language'], language);
            if (surface === 'header') {
              await context.clearCookies({ name: 'django_language' });
              assert.equal((await page.reload()).headers()['content-language'], language, 'Profile must survive missing language cookie');
            }
            results.push({ surface, language, width, theme, keyboard: true, focusRestored: true, returnPathPreserved: true, persisted: true, overflow: false });
            await context.close();
          }
        }
      }
    }
    const context = await browser.newContext();
    await context.addCookies([{ name: 'sessionid', value: cookies.clinic_admin, url: base }]);
    const page = await context.newPage();
    page.on('pageerror', error => errors.push(error.message));
    await page.goto(`${base}/design-system/`);
    await page.locator('input[name=display_name]').fill('Alteração não salva');
    await page.locator('#reference-language-toggle').click();
    await page.locator('#reference-language-choice').selectOption('en');
    let posts = 0;
    let dialogs = 0;
    page.on('request', request => { if (request.method() === 'POST' && request.url().endsWith('/accounts/language/')) posts += 1; });
    const dismiss = async dialog => { dialogs += 1; await dialog.dismiss(); };
    page.on('dialog', dismiss);
    await page.locator('[data-language-form] button[type=submit]').click();
    assert.equal(posts, 0);
    assert.equal(dialogs, 1);
    assert.equal(await page.locator('input[name=display_name]').inputValue(), 'Alteração não salva');
    page.off('dialog', dismiss);
    page.on('dialog', async dialog => { dialogs += 1; assert.equal(dialog.type(), 'confirm'); await dialog.accept(); });
    await Promise.all([page.waitForNavigation(), page.locator('[data-language-form] button[type=submit]').click()]);
    assert.equal(posts, 1);
    assert.equal(dialogs, 2, 'Exactly one confirmation per attempt, no second beforeunload prompt');
    assert.equal(await page.evaluate(() => document.activeElement.id), 'reference-language-toggle');
    results.push({ dirtyForm: true, cancelPreservesInput: true, acceptSinglePost: true, noDoublePrompt: true });
    await context.close();
    const blocked = await browser.newContext();
    await blocked.addInitScript(() => Object.defineProperty(window, 'sessionStorage', { get() { throw new DOMException('Blocked', 'SecurityError'); } }));
    const blockedPage = await blocked.newPage();
    blockedPage.on('pageerror', error => errors.push(error.message));
    await blockedPage.goto(`${base}/accounts/login/`);
    await blockedPage.locator('#auth-language-toggle').click();
    await blockedPage.locator('#auth-language-choice').selectOption('es');
    const [changed] = await Promise.all([blockedPage.waitForNavigation(), blockedPage.locator('[data-language-form] button[type=submit]').click()]);
    assert.equal(changed.headers()['content-language'], 'es');
    results.push({ blockedBrowserStorage: true, languageChangeWorks: true });
    await blocked.close();
    assert.deepEqual(errors, []);
    fs.writeFileSync(`${output}/results.json`, JSON.stringify({ scope: 'Selector foundation only; en/es enabled exclusively in disposable preview, not full UI translations', results, errors }, null, 2));
    console.log(`${results.length} i18n scenarios passed`);
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
