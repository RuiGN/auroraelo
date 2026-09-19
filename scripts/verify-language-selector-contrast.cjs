/* Check real post-login language controls; credentials stay in the environment. */
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const base = process.env.MINDCARE_URL || 'http://127.0.0.1:8000';
assert(['localhost', '127.0.0.1'].includes(new URL(base).hostname), 'Local verification only');
const output = process.env.CONTRAST_OUTPUT || 'docs/migration/evidence/language-selector-contrast';
const email = process.env.MINDCARE_TEST_EMAIL;
const password = process.env.MINDCARE_TEST_PASSWORD;
assert(email && password, 'Provide synthetic account credentials via environment');
fs.mkdirSync(output, { recursive: true });

const luminance = rgb => rgb.slice(0, 3).map(value => {
  const channel = value / 255;
  return channel <= 0.04045 ? channel / 12.92 : ((channel + 0.055) / 1.055) ** 2.4;
}).reduce((sum, value, i) => sum + value * [0.2126, 0.7152, 0.0722][i], 0);
const contrast = (a, b) => {
  const x = luminance(a); const y = luminance(b);
  return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05);
};
const measure = locator => locator.evaluate(el => {
  const rgba = value => (value.match(/[\d.]+/g) || []).map(Number);
  let effectiveBackground;
  for (let node = el; node; node = node.parentElement) {
    const color = rgba(getComputedStyle(node).backgroundColor);
    if (color.length === 3 || color[3] === 1) { effectiveBackground = color; break; }
  }
  const css = getComputedStyle(el);
  return {
    foreground: rgba(css.color), background: rgba(css.backgroundColor),
    effectiveBackground: effectiveBackground || [255, 255, 255],
    colorScheme: css.colorScheme, outline: css.outlineStyle,
    outlineColor: css.outlineColor, backgroundImage: css.backgroundImage,
  };
});

(async () => {
  const browser = await chromium.launch({ headless: true,
    ...(process.env.CHROMIUM_PATH ? { executablePath: process.env.CHROMIUM_PATH } : {}),
  });
  const results = []; const errors = [];
  const save = () => fs.writeFileSync(`${output}/results.json`, JSON.stringify({
    scope: 'Post-login language selector contrast only; not whole-page WCAG acceptance',
    results, errors,
  }, null, 2));
  const auth = await browser.newContext();
  try {
    const page = await auth.newPage();
    await page.goto(base + '/accounts/login/');
    await page.locator('input[name=email]').fill(email);
    await page.locator('input[name=password]').fill(password);
    await Promise.all([
      page.waitForNavigation(), page.locator('form').filter({ has: page.locator('input[name=email]') }).locator('button[type=submit]').click(),
    ]);
    assert(new URL(page.url()).pathname.startsWith('/workspace/'), 'Use a synthetic account authorized for workspace; MFA is never bypassed');
    const state = await auth.storageState();
    for (const path of ['/workspace/', '/workspace/detached/']) {
      for (const width of [320, 390, 1440]) {
        for (const language of ['pt-br', 'en', 'es']) {
          const context = await browser.newContext({ storageState: state,
            viewport: { width, height: 900 }, colorScheme: 'dark', reducedMotion: 'reduce',
          });
          await context.addCookies([{ name: 'django_language', value: language, url: base }]);
          const page = await context.newPage();
          page.on('pageerror', error => errors.push(error.message));
          const response = await page.goto(base + path);
          assert.equal(response.status(), 200);
          assert.equal(response.headers()['content-language'], language);
          for (const theme of ['light']) {
            assert.equal(await page.locator('html').getAttribute('data-bs-theme'), 'light');
            await page.locator('#header-language-toggle').focus();
            await page.keyboard.press('Enter');
            const menu = page.locator('#header-language-menu');
            await menu.waitFor({ state: 'visible' });
            const select = page.locator('#header-language-choice');
            assert.deepEqual(await select.locator('option').evaluateAll(nodes => nodes.map(node => node.value)), ['pt-br', 'en', 'es']);
            const toggle = page.locator('#header-language-toggle');
            const localName = { 'pt-br': 'Português (Brasil)', en: 'English', es: 'Español' }[language];
            const country = { 'pt-br': 'br', en: 'us', es: 'es' }[language];
            assert.equal(await toggle.locator('.feather-globe').count(), 0);
            assert.equal(await toggle.locator('img').count(), 1,
              'Toggle must carry exactly one flag image');
            assert.equal((await toggle.innerText()).trim(), language.toUpperCase());
            assert((await toggle.getAttribute('aria-label')).includes(localName));
            const sample = { path, width, language, theme, flag: country, states: {} };
            for (const controlState of ['normal', 'focus', 'hover']) {
              if (controlState === 'focus') await select.focus();
              if (controlState === 'hover') await select.hover();
              const colors = await measure(select);
              colors.contrast = contrast(colors.foreground, colors.effectiveBackground);
              sample.states[controlState] = colors;
            }
            sample.label = await measure(page.locator('[for=header-language-choice]'));
            sample.label.contrast = contrast(sample.label.foreground, sample.label.effectiveBackground);
            sample.options = [];
            for (const option of await select.locator('option').all()) {
              const colors = await measure(option);
              sample.options.push({ ...colors, contrast: contrast(colors.foreground, colors.effectiveBackground) });
            }
            await page.locator('#header-language-toggle').focus();
            await menu.screenshot({ path: `${output}/${path.includes('detached') ? 'detached' : 'vertical'}-${language}-${width}-${theme}.png` });
            results.push(sample); save();
            for (const colors of Object.values(sample.states)) {
              assert(colors.contrast >= 4.5, `Unreadable ${theme} select: ${JSON.stringify(colors)}`);
              if (theme === 'dark') {
                assert(colors.background.length === 3 || colors.background[3] === 1,
                  'Dark input needs an opaque background, not the vendor transparent override');
                assert(luminance(colors.background) < 0.2, 'Dark input has a light background');
              }
            }
            assert(sample.label.contrast >= 4.5, `Unreadable ${theme} label`);
            assert(sample.options.every(option => option.contrast >= 4.5), `Unreadable ${theme} options`);
            if (theme === 'dark') assert(sample.options.every(option =>
              (option.background.length === 3 || option.background[3] === 1) &&
              luminance(option.background) < 0.2), 'Native options need an opaque dark background');
            assert(sample.states.focus.outline !== 'none', 'Keyboard focus must remain visible');
            const original = await select.inputValue();
            await select.focus(); await page.keyboard.press('ArrowDown');
            await page.keyboard.press('Escape');
            if (!(await menu.isVisible())) await page.locator('#header-language-toggle').click();
            await select.selectOption(original);
            // No language POST: keep the account preference untouched.
            if (await menu.isVisible()) await page.locator('#header-language-toggle').click();
          }
          await context.close();
        }
      }
    }
    assert.equal(results.length, 36);
    assert.deepEqual(errors, []);
    console.log(`${results.length} post-login contrast scenarios passed`);
  } catch (error) { errors.push(error.message); save(); throw error; }
  finally {
    try {
      const cookies = await auth.cookies();
      const csrf = cookies.find(cookie => cookie.name === 'csrftoken');
      if (csrf) await auth.request.post(base + '/accounts/logout/', { headers: { 'X-CSRFToken': csrf.value } });
    } finally { save(); await browser.close(); }
  }
})().catch(error => { console.error(error.message); process.exit(1); });
