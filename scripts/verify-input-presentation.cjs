/* Run with PLAYWRIGHT_MODULE=/path/to/playwright node scripts/verify-input-presentation.cjs. */
const assert = require('node:assert/strict');
const { execFileSync } = require('node:child_process');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const root = path.resolve(__dirname, '..');
const rendered = execFileSync(path.join(root, '.venv/bin/python'), ['-c', `
import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings.test'
import django
django.setup()
from django.template.loader import render_to_string
from people.forms import PatientProfileForm
from clinics.forms import ClinicIdentityForm, ClinicOperationsForm
print(''.join(render_to_string('components/form.html', {'form': form, 'form_id': name, 'submit_label': 'Salvar'}) for name, form in [('patient', PatientProfileForm()), ('clinic', ClinicIdentityForm(prefix='clinic')), ('hours', ClinicOperationsForm(prefix='hours'))]))
`], { cwd: root, encoding: 'utf8' });
const css = ['static/duralux/css/bootstrap.min.css', 'static/duralux/vendors/css/feather.min.css', 'static/duralux/css/product-integration.css'];
(async () => {
  const browser = await chromium.launch({ executablePath: process.env.CHROME_BIN || '/usr/bin/google-chrome', headless: true, args: ['--no-sandbox'] });
  const page = await browser.newPage();
  const failures = [];
  const check = async (name, test) => { try { await test(); console.log(`PASS ${name}`); } catch (e) { failures.push(name); console.error(`FAIL ${name}: ${e.message}`); } };
  await page.setContent(`<main style="max-width:900px;padding:16px">${rendered}<form id="unguarded"><input name="cep" data-mask="cep"><input name="phone" data-mask="phone"><input name="document" data-mask="document"><input name="unknown" data-mask="custom"><button>Send</button></form></main>`);
  for (const file of css) await page.addStyleTag({ content: fs.readFileSync(path.join(root, file), 'utf8') });
  const iconFont = fs.readFileSync(path.join(root, 'static/duralux/vendors/fonts/feather.woff')).toString('base64');
  await page.addStyleTag({ content: `@font-face { font-family: feather; src: url(data:font/woff;base64,${iconFont}) format('woff'); }` });
  await page.evaluate(() => document.fonts.ready);
  await page.addScriptTag({ path: path.join(root, 'static/duralux/js/form-behaviors.js') });
  await page.evaluate(() => document.dispatchEvent(new Event('DOMContentLoaded')));
  const input = name => page.locator(`#unguarded [name="${name}"]`);
  await check('CEP formats outside guarded forms', async () => { await input('cep').fill('01310100'); assert.equal(await input('cep').inputValue(), '01310-100'); });
  await check('phone formats outside guarded forms', async () => { await input('phone').fill('11987654321'); assert.equal(await input('phone').inputValue(), '(11) 98765-4321'); });
  await check('CPF and CNPJ masks', async () => { await input('document').fill('12345678900'); assert.equal(await input('document').inputValue(), '123.456.789-00'); await input('document').fill('12345678000190'); assert.equal(await input('document').inputValue(), '12.345.678/0001-90'); });
  await check('overlong values are not silently truncated', async () => { await input('document').fill('123456789012345'); assert.equal((await input('document').inputValue()).replace(/\D/g, ''), '123456789012345'); });
  await check('international phone is preserved', async () => { await input('phone').fill('+351912345678'); assert.equal(await input('phone').inputValue(), '+351912345678'); });
  await check('unknown masks do not alter user data', async () => { await input('unknown').fill('ABC-123'); assert.equal(await input('unknown').inputValue(), 'ABC-123'); });
  await check('middle edit keeps caret near edit', async () => {
    await input('phone').fill('11987654321');
    await input('phone').evaluate(el => { el.focus(); el.setSelectionRange(6, 7); });
    await page.keyboard.type('2');
    assert.equal(await input('phone').inputValue(), '(11) 92765-4321');
    assert.equal(await input('phone').evaluate(el => el.selectionStart), 7);
  });
  await check('submit uses current data, not stale mask cache', async () => {
    const values = await page.evaluate(() => {
      const form = document.querySelector('#unguarded');
      form.elements.cep.value = '22290-140'; // autofill may not dispatch input
      form.elements.phone.value = '+351912345678';
      form.addEventListener('submit', e => e.preventDefault());
      form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
      return Object.fromEntries(new FormData(form));
    });
    assert.equal(values.cep, '22290140'); assert.equal(values.phone, '+351912345678'); assert.equal(values.unknown, 'ABC-123');
  });
  for (const width of [360, 768, 1280]) await check(`responsive layout ${width}px`, async () => {
    await page.setViewportSize({ width, height: 1000 });
    const result = await page.evaluate(() => {
      const form = document.querySelector('#patient');
      const fields = Array.from(form.querySelectorAll('.field-span')).map(el => ({ width: el.getBoundingClientRect().width, overflow: el.scrollWidth > el.clientWidth + 1 }));
      return { pageOverflow: document.documentElement.scrollWidth > innerWidth, fields, grid: form.querySelector('.product-form-grid') || form.matches('.product-form-grid'), narrow: document.querySelector('#id_address_state').getBoundingClientRect().width, long: document.querySelector('#id_address_line').getBoundingClientRect().width };
    });
    assert.equal(result.pageOverflow, false); assert.ok(result.fields.length); assert.ok(result.fields.every(f => !f.overflow));
    if (width === 360) assert.ok(Math.abs(result.narrow - result.long) < 2);
    else assert.ok(result.narrow < result.long * 0.8, 'short values must be narrower than address');
    if (width === 360) await page.screenshot({ path: '/tmp/mindcare-input-mobile.png', fullPage: true });
  });
  await page.setViewportSize({ width: 1280, height: 1100 });
  const output = process.env.SCREENSHOT_PATH || '/tmp/mindcare-input-desktop.png';
  await page.screenshot({ path: output, fullPage: true });
  console.log(`Screenshot: ${output}`);
  await browser.close();
  assert.deepEqual(failures, [], 'input browser checks failed');
})().catch(e => { console.error(e); process.exitCode = 1; });
