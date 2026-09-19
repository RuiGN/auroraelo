/* Verify the actual local Compose artifact, without language setting overrides. */
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const base = process.env.MINDCARE_URL || 'http://127.0.0.1:8000';
assert(['127.0.0.1', 'localhost'].includes(new URL(base).hostname), 'Local verification only');
const path = require('node:path');
const output = path.resolve(process.env.LANGUAGE_OUTPUT || path.join(__dirname, '../docs/migration/evidence/globe-card'));
const languages = {
  'pt-br': ['Entrar na plataforma', 'Idioma da interface', 'Carregando...'],
  en: ['Sign in to the platform', 'Interface language', 'Loading...'],
  es: ['Iniciar sesión en la plataforma', 'Idioma de la interfaz', 'Cargando...'],
};
fs.mkdirSync(output, { recursive: true });
(async () => {
  const browser = await chromium.launch({
    headless: true,
    ...(process.env.CHROMIUM_PATH ? { executablePath: process.env.CHROMIUM_PATH } : {}),
  });
  const results = [];
  const errors = [];
  const persist = () => fs.writeFileSync(`${output}/results.json`, JSON.stringify({
    scope: 'Anonymous login selector on local Compose; not full-domain visual or editorial acceptance',
    base, results, errors,
  }, null, 2));
  try {
    for (const [language, [title, label, loading]] of Object.entries(languages)) {
      for (const width of [320, 390, 1440]) {
        for (const theme of ['light']) { // theme pinned to light
          const context = await browser.newContext({
            viewport: { width, height: 900 }, colorScheme: theme,
            locale: 'pt-BR', reducedMotion: 'reduce',
          });
          const page = await context.newPage();
          page.on('pageerror', error => errors.push(error.message));
          page.on('response', response => {
            if (response.status() >= 400) errors.push(`${response.status()} ${response.url()}`);
          });
          const path = '/accounts/login/?next=%2Fworkspace%2F';
          assert.equal((await page.goto(base + path)).status(), 200);
          const geometry = await page.locator('#auth-language-toggle').evaluate(button => {
            const card = button.closest('.product-auth-card');
            if (!card) return { insideCard: false };
            const b = button.getBoundingClientRect(), c = card.getBoundingClientRect();
            const brand = card.querySelector('.product-auth-brand').getBoundingClientRect();
            const emblem = card.querySelector('.product-auth-emblem').getBoundingClientRect();
            const overlapsEmblem = b.left < emblem.right && b.right > emblem.left &&
              b.top < emblem.bottom && b.bottom > emblem.top;
            return { insideCard: true, topGap: b.top - c.top, rightGap: c.right - b.right,
              contained: b.left >= c.left && b.right <= c.right && b.top >= c.top && b.bottom <= c.bottom,
              aboveBrand: b.bottom <= brand.top, overlapsEmblem, width: b.width, height: b.height };
          });
          assert(geometry.insideCard && geometry.contained, 'Language selector must be inside the login card');
          assert(geometry.topGap <= 52 && geometry.rightGap <= 52, 'Selector must be at upper right');
          assert(geometry.aboveBrand && !geometry.overlapsEmblem, 'Selector must not overlap branding');
          assert(geometry.width >= 44 && geometry.height >= 44, 'Accessible touch target');
          assert.deepEqual(await page.locator('#auth-language-choice option').evaluateAll(
            options => options.map(option => option.value)), ['pt-br', 'en', 'es']);
          await page.locator('#auth-language-toggle').focus();
          await page.keyboard.press('Enter');
          await page.locator('#auth-language-menu').waitFor({ state: 'visible' });
          assert(await page.locator('#auth-language-menu').evaluate(el => {
            const r = el.getBoundingClientRect(); return r.left >= -1 && r.right <= innerWidth + 1;
          }), 'Menu outside viewport');
          await page.locator('#auth-language-choice').selectOption(language);
          const [response] = await Promise.all([
            page.waitForNavigation(),
            page.locator('[data-language-form] button[type=submit]').click(),
          ]);
          assert.equal(response.status(), 200);
          assert.equal(response.headers()['content-language'], language);
          assert.equal(page.url(), base + path);
          assert.equal(await page.locator('html').getAttribute('lang'), language);
          assert((await page.title()).includes(title));
          const toggle = page.locator('#auth-language-toggle');
          const localName = { 'pt-br': 'Português (Brasil)', en: 'English', es: 'Español' }[language];
          const country = { 'pt-br': 'br', en: 'us', es: 'es' }[language];
          assert.equal(await toggle.locator('.feather-globe').count(), 0);
          assert.equal(await toggle.locator('i').count(), 0);
          const flag = toggle.locator('img.product-language-flag');
          assert(await flag.isVisible(), 'Flag must be visible on the closed toggle');
          assert.equal(await flag.getAttribute('alt'), localName);
          const flagSrc = await flag.getAttribute('src');
            assert(
              typeof flagSrc === 'string' && flagSrc.endsWith(`/duralux/images/flags/${country}.svg`),
              'Flag src must match the current country'
            );
          assert.equal((await toggle.innerText()).trim(), language.toUpperCase());
          assert((await toggle.getAttribute('aria-label')).includes(localName));
          assert.equal(await page.locator('[for="auth-language-choice"]').textContent(), label);
          assert.equal(await page.evaluate(() => document.activeElement.id), 'auth-language-toggle');
          assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
          assert.equal((await page.reload()).headers()['content-language'], language);
          const catalog = await context.request.get(base + '/jsi18n/');
          assert.equal(catalog.status(), 200);
          assert.equal(catalog.headers()['content-language'], language);
          assert((await catalog.text()).includes(loading));
          await page.locator('#auth-language-toggle').click();
          await page.screenshot({ path: `${output}/login-${language}-${width}-${theme}.png` });
          results.push({ language, width, theme, title: await page.title(),
            geometry, flag: country, cookiePersistence: true, focusRestored: true, returnPathPreserved: true,
            jsCatalog: true, overflow: false });
          persist();
          await context.close();
        }
      }
    }
    assert.equal(results.length, 18);
    assert.deepEqual(errors, []);
    console.log(`${results.length} actual-runtime language scenarios passed`);
  } catch (error) {
    errors.push(error.message); persist(); throw error;
  } finally {
    persist(); await browser.close();
  }
})().catch(error => { console.error(error); process.exit(1); });
