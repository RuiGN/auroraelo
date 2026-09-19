/* Synthetic preview only, with pt-br/en/es explicitly enabled. */
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const fs = require('node:fs');
const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const base = 'http://127.0.0.1:8765';
const output = 'docs/migration/evidence/visual-shared-translations';
const sessions = JSON.parse(fs.readFileSync('.migration-runtime/preview-cookies.json'));
const auth = JSON.parse(fs.readFileSync('.migration-runtime/auth-preview-fixtures.json'));
const languages = ['pt-br', 'en', 'es'];
const titles = {
  login: ['Entrar na plataforma', 'Sign in to the platform', 'Iniciar sesión en la plataforma'],
  workspace: ['Olá, Ana.', 'Hello, Ana.', 'Hola, Ana.'],
  reference: ['Referência do sistema visual', 'Visual system reference', 'Referencia del sistema visual'],
  error: ['Página não encontrada', 'Page not found', 'Página no encontrada'],
};
const routes = { login: '/accounts/login/', workspace: '/workspace/', reference: '/design-system/', error: '/missing-shared-ui/' };
fs.mkdirSync(output, { recursive: true });

function totp(secret) {
  const alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567';
  const bits = [...secret.replace(/=+$/, '').toUpperCase()].map(c => alphabet.indexOf(c).toString(2).padStart(5, '0')).join('');
  const bytes = [];
  for (let i = 0; i + 8 <= bits.length; i += 8) bytes.push(parseInt(bits.slice(i, i + 8), 2));
  const counter = Buffer.alloc(8);
  counter.writeBigUInt64BE(BigInt(Math.floor(Date.now() / 30000)));
  const digest = crypto.createHmac('sha1', Buffer.from(bytes)).update(counter).digest();
  return ((digest.readUInt32BE(digest.at(-1) & 15) & 0x7fffffff) % 1000000).toString().padStart(6, '0');
}

(async () => {
  const browser = await chromium.launch();
  const results = [];
  const errors = [];
  async function contextFor(language, width, theme, session) {
    const context = await browser.newContext({ viewport: { width, height: 900 }, colorScheme: theme, reducedMotion: 'reduce', locale: language });
    const cookies = [{ name: 'django_language', value: language, url: base }];
    if (session) cookies.push({ name: 'sessionid', value: session, url: base });
    await context.addCookies(cookies);
    return context;
  }
  try {
    for (const [index, language] of languages.entries()) {
      for (const width of [320, 390, 1440]) {
        for (const theme of ['light', 'dark']) {
          for (const surface of Object.keys(routes)) {
            const context = await contextFor(language, width, theme, ['workspace', 'reference'].includes(surface) ? sessions.clinic_admin : null);
            const page = await context.newPage();
            page.on('pageerror', e => errors.push(e.message));
            const response = await page.goto(base + routes[surface]);
            assert.equal(response.status(), surface === 'error' ? 404 : 200);
            assert.equal(response.headers()['content-language'], language);
            assert.equal(await page.locator('html').getAttribute('lang'), language);
            assert.equal(await page.locator('h1').innerText(), titles[surface][index]);
            assert.equal(await page.locator('html').getAttribute('data-bs-theme'), 'light');
            assert.equal(await page.locator('[data-theme-toggle]').count(), 0);
            if (surface === 'workspace') {
              assert(await page.getByText(/Clínica de validação/).count(), 'Clinic name must remain unchanged');
            }
            if (surface === 'reference') {
              await page.locator('.apexcharts-canvas').waitFor();
              const categories = await page.locator('.apexcharts-xaxis-texts-g').textContent();
              assert(categories.includes(['Semana 1', 'Week 1', 'Semana 1'][index]));
              await Promise.all([page.waitForNavigation(), page.locator('#reference-form [data-submit-button]').click()]);
              assert.equal(await page.locator('#reference-form-error-title').innerText(), ['Revise os campos indicados', 'Review the highlighted fields', 'Revise los campos indicados'][index]);
              assert.equal(await page.evaluate(() => document.activeElement.id), 'id_display_name');
            }
            assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), `${surface}/${language}/${width}: overflow`);
            await page.evaluate(() => document.fonts.ready);
            await page.evaluate(() => scrollTo(0, 0));
            await page.screenshot({ path: `${output}/${surface}-${language}-${width}-${theme}.png` });
            results.push({ surface, language, width, theme, screenshotTheme: surface === 'workspace' ? (theme === 'light' ? 'dark' : 'light') : theme, translatedHeading: true, overflow: false });
            await context.close();
          }
        }
      }
      for (const state of ['enroll', 'sessions', 'challenge', 'recovery', 'reset', 'invalid-reset', 'invite']) {
        const context = await contextFor(language, 320, 'dark', auth.cookies[state]);
        const page = await context.newPage();
        page.on('pageerror', e => errors.push(e.message));
        const response = await page.goto(base + auth.urls[state]);
        assert.equal(response.status(), state === 'invalid-reset' ? 400 : 200);
        assert.equal(response.headers()['content-language'], language);
        assert(await page.locator('h1').innerText());
        if (state === 'enroll') {
          await context.grantPermissions(['clipboard-read', 'clipboard-write']);
          await page.locator('[data-copy-target]').click();
          await page.waitForFunction(() => document.querySelector('[data-copy-status]').textContent.length > 0);
          assert.equal(await page.locator('[data-copy-status]').innerText(), ['Chave copiada.', 'Key copied.', 'Clave copiada.'][index]);
          await page.evaluate(() => { navigator.clipboard.writeText = async () => { throw new DOMException('Denied', 'NotAllowedError'); }; });
          await page.locator('[data-copy-target]').click();
          await page.waitForFunction(() => document.querySelector('[data-copy-status]').textContent === document.querySelector('[data-copy-target]').dataset.copyFailure);
          assert.equal(await page.locator('[data-copy-status]').innerText(), await page.locator('[data-copy-target]').getAttribute('data-copy-failure'));
        }
        assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), `${state}/${language}: overflow`);
        await page.screenshot({ path: `${output}/${state}-${language}-320-dark.png` });
        results.push({ surface: state, language, width: 320, theme: 'dark', overflow: false });
        await context.close();
      }
      const fixture = auth.recovery[index];
      const context = await contextFor(language, 320, 'dark', fixture.cookie);
      const page = await context.newPage();
      page.on('pageerror', e => errors.push(e.message));
      await page.goto(base + auth.urls.enroll);
      await page.locator('input[name=code]').fill(totp(fixture.secret));
      await Promise.all([page.waitForNavigation(), page.locator('form[data-form-guard] button[type=submit]').click()]);
      assert.equal(await page.locator('.product-recovery-codes li').count(), 8);
      assert.equal(await page.locator('html').getAttribute('lang'), language);
      assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
      // Synthetic recovery values are not needed in the visual evidence.
      await page.screenshot({ path: `${output}/recovery-codes-${language}-320-dark.png`, mask: [page.locator('.product-recovery-codes')] });
      results.push({ surface: 'recovery-codes', language, realMfaPost: true, overflow: false });
      await context.close();
    }
    assert.deepEqual(errors, []);
    fs.writeFileSync(`${output}/results.json`, JSON.stringify({ scope: 'Shared UI only, preview languages unpublished', results, errors }, null, 2));
    console.log(`${results.length} shared translation browser scenarios passed`);
  } finally { await browser.close(); }
})().catch(e => { console.error(e); process.exitCode = 1; });
