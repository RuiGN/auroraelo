/* Requires the disposable synthetic preview; never run against production. */
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const fs = require('node:fs');
const assert = require('node:assert/strict');
const { randomUUID } = require('node:crypto');
const base = process.env.CONSENTS_PREVIEW_URL || 'http://127.0.0.1:8766';
assert(['http://127.0.0.1:8766', 'http://localhost:8766'].includes(base));
const output = 'docs/migration/evidence/visual-consents';
const fixture = JSON.parse(fs.readFileSync('.migration-runtime/consents-preview.json'));
const languages = ['pt-br', 'en', 'es'];
const headings = {
  center: ['Termos e consentimentos', 'Terms and consents', 'Términos y consentimientos'],
};
fs.mkdirSync(output, { recursive: true });
(async () => {
  const browser = await chromium.launch();
  const results = [];
  const errors = [];
  async function open(language, width, theme, role) {
    const context = await browser.newContext({ viewport: { width, height: 900 }, colorScheme: theme, reducedMotion: 'reduce', locale: language });
    await context.addCookies([
      { name: 'django_language', value: language, url: base },
      { name: 'sessionid', value: fixture.cookies[role], url: base },
    ]);
    const page = await context.newPage();
    page.on('pageerror', error => errors.push(error.message));
    page.on('response', response => {
      if (response.status() >= 400 && ['script', 'stylesheet', 'image', 'font'].includes(response.request().resourceType())) errors.push(`Asset ${response.status()}: ${response.url()}`);
    });
    return { context, page };
  }
  async function capture(page, surface, language, width, theme) {
    assert.equal(await page.locator('html').getAttribute('lang'), language);
    assert.equal(await page.locator('html').getAttribute('data-bs-theme'), 'light');
    await page.evaluate(() => document.fonts.ready);
    assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), `${surface}/${language}/${width}: overflow`);
    await page.screenshot({ path: `${output}/${surface}-${language}-${width}-${theme}.png`, fullPage: true });
    results.push({ surface, language, width, theme, overflow: false });
  }
  async function submitInvalid(page, form, values) {
    const responsePromise = page.waitForNavigation();
    await page.locator(form).first().evaluate((element, values) => {
      for (const [name, value] of Object.entries(values)) {
        for (const input of element.querySelectorAll(`[name="${name}"]`)) {
          if (input.type === 'radio' || input.type === 'checkbox') input.checked = false;
          else input.value = value;
        }
      }
      element.submit();
    }, values);
    const response = await responsePromise;
    assert.equal(response.status(), 400);
  }
  try {
    for (const [index, language] of languages.entries()) {
      for (const width of [320, 390, 1440]) {
        for (const theme of ['light']) { // theme pinned to light
          const patient = await open(language, width, theme, 'patient');
          let response = await patient.page.goto(base + fixture.center);
          assert.equal(response.status(), 200);
          assert.equal(response.headers()['content-language'], language);
          assert.equal(await patient.page.locator('h1').innerText(), headings.center[index]);
          const content = await patient.page.locator('main').innerText();
          assert(content.includes(fixture.document_title));
          assert(content.includes('Texto clínico original <não-traduzir>.'));
          assert.equal(await patient.page.locator('main preservado, main não-traduzir').count(), 0);
          assert.equal(await patient.page.locator('main input[type=radio]:checked').count(), 0);
          await capture(patient.page, 'center', language, width, theme);
          await submitInvalid(patient.page, `form[action="${fixture.decision}"]`, { decision: '', request_id: randomUUID() });
          assert(await patient.page.locator('main [role=alert]').count());
          await capture(patient.page, 'decision-error', language, width, theme);
          await patient.page.goto(base + fixture.center);
          await submitInvalid(patient.page, `form[action="${fixture.revoke}"]`, { reason: '', confirm_scope: '', request_id: randomUUID() });
          assert(await patient.page.locator('main [role=alert]').count());
          await capture(patient.page, 'revocation-error', language, width, theme);
          await patient.context.close();

          const admin = await open(language, width, theme, 'clinic_admin');
          response = await admin.page.goto(base + fixture.queue);
          assert.equal(response.status(), 200);
          const queue = await admin.page.locator('main').innerText();
          assert(queue.includes('PAT-'));
          assert(!queue.includes(fixture.subject_id));
          assert(queue.includes(fixture.document_title));
          assert(!queue.includes('clinical_follow_up'));
          assert.equal(await admin.page.locator('nav [role=status]').innerText(), [
            '1 revogação operacional pendente',
            '1 pending operational revocation',
            '1 revocación operativa pendiente',
          ][index]);
          assert.equal(await admin.page.locator('main input.form-control[name=acknowledgement_reference]').count(), 1);
          assert.equal(await admin.page.locator('main button.btn-primary[type=submit]').count(), 1);
          await capture(admin.page, 'queue', language, width, theme);
          await submitInvalid(admin.page, `form[action="${fixture.acknowledge}"]`, { acknowledgement_reference: '' });
          assert(await admin.page.locator('main [role=alert]').count());
          await capture(admin.page, 'queue-error', language, width, theme);
          await admin.context.close();

          const empty = await open(language, width, theme, 'empty_admin');
          response = await empty.page.goto(base + fixture.center);
          assert.equal(response.status(), 200);
          assert.equal(await empty.page.locator('main input[type=radio]').count(), 0);
          await capture(empty.page, 'center-empty', language, width, theme);
          response = await empty.page.goto(base + fixture.queue);
          assert.equal(response.status(), 200);
          assert.equal(await empty.page.locator('main input[name=acknowledgement_reference]').count(), 0);
          await capture(empty.page, 'queue-empty', language, width, theme);
          await empty.context.close();
        }
      }
      for (const role of ['patient', 'therapist']) {
        const denied = await open(language, 320, 'dark', role);
        const response = await denied.page.goto(base + fixture.queue);
        assert.equal(response.status(), 403);
        assert(!(await denied.page.locator('main').innerText()).includes(fixture.document_title));
        results.push({ surface: 'queue-denied', language, role, denied: true });
        await denied.context.close();
      }
    }
    assert.deepEqual(errors, []);
    fs.writeFileSync(`${output}/results.json`, JSON.stringify({ results, errors }, null, 2));
    console.log(`${results.length} consent browser scenarios passed`);
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
