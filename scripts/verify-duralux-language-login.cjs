/* Disposable synthetic login fixture only; never pass operational credentials. */
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const base = 'http://127.0.0.1:8765';
const fixture = JSON.parse(fs.readFileSync('.migration-runtime/language-login-fixture.json'));

(async () => {
  const browser = await chromium.launch();
  const errors = [];
  try {
    for (const round of ['choose', 'new-device']) {
      const context = await browser.newContext({ locale: 'en-US' });
      const page = await context.newPage();
      page.on('pageerror', error => errors.push(error.message));
      await page.goto(`${base}/accounts/login/`);
      await page.locator('input[name=email]').fill(fixture.email);
      await page.locator('input[name=password]').fill(fixture.password);
      await Promise.all([page.waitForNavigation(), page.locator('form[data-form-guard] button[type=submit]').click()]);
      assert(!new URL(page.url()).pathname.startsWith('/accounts/'), 'Real login must reach authorized workspace');
      if (round === 'choose') {
        await page.locator('#header-language-toggle').click();
        await page.locator('#header-language-choice').selectOption('es');
        const [response] = await Promise.all([page.waitForNavigation(), page.locator('[data-language-form] button[type=submit]').click()]);
        assert.equal(response.headers()['content-language'], 'es');
      } else {
        assert.equal(await page.locator('html').getAttribute('lang'), 'es');
        assert.equal(await page.locator('#header-language-choice').inputValue(), 'es');
        assert(!(await context.cookies()).some(cookie => cookie.name === 'django_language'), 'New browser must recover profile without a language cookie');
      }
      await context.close();
    }
    assert.deepEqual(errors, []);
    fs.writeFileSync('docs/migration/evidence/visual-i18n/real-login-result.json', JSON.stringify({ realCredentialLogin: true, manualChoice: 'es', freshBrowserLocale: 'en-US', preferenceRestoredWithoutLanguageCookie: true, errors }, null, 2));
    console.log('Real login and new-device language persistence passed');
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
