/* Run only against the disposable synthetic preview with pt-br/en/es enabled. */
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const fs = require('node:fs');
const assert = require('node:assert/strict');
const base = 'http://127.0.0.1:8765';
const output = 'docs/migration/evidence/visual-clinic-onboarding';
const fixture = JSON.parse(fs.readFileSync('.migration-runtime/clinic-onboarding-preview.json'));
const languages = ['pt-br', 'en', 'es'];
const titles = {
  setup: ['Configurar clínica', 'Configure clinic', 'Configurar clínica'],
  domains: ['Domínios personalizados', 'Custom domains', 'Dominios personalizados'],
  checklist: ['Onboarding da clínica', 'Clinic onboarding', 'Incorporación de la clínica'],
  patient: ['Sua jornada', 'Your journey', 'Su recorrido'],
  switch: ['Trocar clínica ativa?', 'Switch active clinic?', '¿Cambiar la clínica activa?'],
};
const surfaces = [
  ...['identity', 'operations', 'branding', 'modules', 'review'].map(stage => ({ name: `setup-${stage}`, title: 'setup', url: `/clinics/setup/?stage=${stage}`, role: 'clinic_admin' })),
  { name: 'domains', title: 'domains', url: '/clinics/white-label/dominios/', role: 'clinic_admin' },
  { name: 'checklist', title: 'checklist', url: '/onboarding/clinic/', role: 'clinic_admin' },
  ...['goals', 'preferences', 'terms', 'complete'].map(step => ({ name: `patient-${step}`, title: 'patient', url: `/onboarding/patient/?step=${step}`, role: 'patient' })),
  { name: 'switch', title: 'switch', url: `/clinics/switch/review/?clinic_id=${fixture.target}&next=/workspace/`, role: 'clinic_admin' },
];
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
      if (response.status() >= 400 && ['script', 'stylesheet', 'image', 'font'].includes(response.request().resourceType())) {
        errors.push(`Asset ${response.status()}: ${response.url()}`);
      }
    });
    return { context, page };
  }
  async function check(page, language, width) {
    assert.equal(await page.locator('html').getAttribute('lang'), language);
    await page.evaluate(() => document.fonts.ready);
    assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), `${page.url()}/${language}/${width}: overflow`);
  }
  try {
    for (const [index, language] of languages.entries()) {
      for (const width of [320, 390, 1440]) {
        for (const theme of ['light']) { // theme pinned to light
          const contexts = {};
          for (const surface of surfaces) {
            contexts[surface.role] ??= await open(language, width, theme, surface.role);
            const { page } = contexts[surface.role];
            const response = await page.goto(base + surface.url);
            assert.equal(response.status(), 200, surface.name);
            assert.equal(response.headers()['content-language'], language);
            assert.equal(await page.locator('h1').innerText(), titles[surface.title][index]);
            assert.equal(await page.locator('html').getAttribute('data-bs-theme'), 'light');
            if (surface.name === 'setup-operations') {
              assert.equal(await page.locator('[name=timezone_name]').inputValue(), 'America/Sao_Paulo');
              assert.equal(await page.locator('[name=language_code]').inputValue(), 'pt-BR');
              assert.equal(await page.locator('label[for=id_monday_start]').innerText(), ['Segunda-feira: início', 'Monday: start', 'Lunes: inicio'][index]);
            }
            if (surface.name === 'setup-review') {
              assert(!(await page.locator('main').innerText()).includes('patient_management'));
              assert((await page.locator('main').innerText()).includes('Clínica de validação'));
            }
            if (surface.name === 'domains') {
              assert((await page.locator('main').innerText()).includes('preview.example.test'));
              assert((await page.locator('main').innerText()).includes(['Verificado', 'Verified', 'Verificado'][index]));
            }
            if (surface.name.startsWith('patient-')) {
              const steps = await page.locator('.product-stepper').innerText();
              assert(!/\b(goals|preferences|terms|complete)\b/.test(steps));
            }
            await check(page, language, width);
            await page.screenshot({ path: `${output}/${surface.name}-${language}-${width}-${theme}.png` });
            results.push({ surface: surface.name, language, width, theme, translatedHeading: true, overflow: false });
          }
          for (const { context } of Object.values(contexts)) await context.close();
        }
      }
      const { context, page } = await open(language, 320, 'dark', 'clinic_admin');
      await page.goto(base + '/clinics/setup/?stage=identity');
      await page.locator('[name=legal_name]').fill('');
      await page.locator('[name=display_name]').fill('Nome original <teste>');
      await Promise.all([page.waitForNavigation(), page.locator('[data-submit-button]').click()]);
      assert.equal(await page.locator('#clinic-setup-error-title').innerText(), ['Revise os campos informados', 'Review the fields provided', 'Revise los campos introducidos'][index]);
      assert.equal(await page.locator('[name=display_name]').inputValue(), 'Nome original <teste>');
      assert.equal(await page.evaluate(() => document.activeElement.name), 'legal_name');
      await check(page, language, 320);
      await page.screenshot({ path: `${output}/setup-error-${language}-320-dark.png` });
      results.push({ surface: 'setup-error', language, width: 320, theme: 'dark', retainedData: true, focusedInvalidField: true });
      await context.close();
      const patient = await open(language, 320, 'dark', 'patient');
      await patient.page.goto(base + '/onboarding/patient/?step=preferences');
      await patient.page.locator('[name=contact_preferences][value=email]').check();
      await patient.page.locator('[name=reminder_windows][value=morning]').check();
      await patient.page.locator('main form').evaluate(form => {
        form.action = '?step=goals';
        const invalid = document.createElement('input');
        invalid.type = 'hidden';
        invalid.name = 'contact_preferences';
        invalid.value = 'invalid-channel';
        form.append(invalid);
      });
      await Promise.all([patient.page.waitForNavigation(), patient.page.locator('main form button[type=submit]').click()]);
      assert.equal(await patient.page.locator('main form input[name=step]').inputValue(), 'preferences');
      assert(await patient.page.locator('[name=contact_preferences][value=email]').isChecked());
      assert(await patient.page.locator('[name=reminder_windows][value=morning]').isChecked());
      assert.equal(await patient.page.evaluate(() => document.activeElement.name), 'contact_preferences');
      assert(await patient.page.locator('main .invalid-feedback').count());
      await check(patient.page, language, 320);
      await patient.page.screenshot({ path: `${output}/onboarding-error-${language}-320-dark.png` });
      results.push({ surface: 'onboarding-error', language, width: 320, theme: 'dark', retainedData: true, focusedInvalidField: true, submittedStepPreserved: true });
      await patient.context.close();
      for (const role of ['patient', 'therapist', 'administrative_staff']) {
        const { context, page } = await open(language, 320, 'dark', role);
        for (const route of ['/clinics/setup/', '/clinics/white-label/dominios/', '/onboarding/clinic/']) {
          const response = await page.goto(base + route);
          assert.equal(response.status(), 403);
          await check(page, language, 320);
          results.push({ surface: route, language, role, denied: true });
        }
        await context.close();
      }
    }
    assert.deepEqual(errors, []);
    fs.writeFileSync(`${output}/results.json`, JSON.stringify({ scope: 'Clinic/onboarding UI, synthetic preview; en/es unpublished', results, errors }, null, 2) + '\n');
    console.log(`${results.length} clinic/onboarding browser scenarios passed`);
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
