/* Only for the disposable preview with synthetic fixtures and pt-br/en/es enabled. */
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const fs = require('node:fs');
const assert = require('node:assert/strict');
const base = 'http://127.0.0.1:8765';
const output = 'docs/migration/evidence/visual-people';
const fixture = JSON.parse(fs.readFileSync('.migration-runtime/people-preview.json'));
const languages = ['pt-br', 'en', 'es'];
const surfaces = [
  { name: 'patients', url: '/people/patients/', headings: ['Pacientes', 'Patients', 'Pacientes'] },
  { name: 'create', url: '/people/patients/new/', headings: ['Cadastrar paciente', 'Register patient', 'Registrar paciente'] },
  { name: 'detail', url: fixture.patient_url, headings: [fixture.patient_name, fixture.patient_name, fixture.patient_name] },
  { name: 'professionals', url: '/people/professionals/', headings: ['Profissionais', 'Professionals', 'Profesionales'] },
];
fs.mkdirSync(output, { recursive: true });
(async () => {
  const browser = await chromium.launch();
  const results = [];
  const errors = [];
  async function open(language, width, theme, role = 'clinic_admin') {
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
  async function check(page, language, theme) {
    assert.equal(await page.locator('html').getAttribute('lang'), language);
    assert.equal(await page.locator('html').getAttribute('data-bs-theme'), 'light');
    await page.evaluate(() => document.fonts.ready);
    assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), `${page.url()}/${language}: overflow`);
  }
  try {
    for (const [index, language] of languages.entries()) {
      for (const width of [320, 390, 1440]) {
        for (const theme of ['light']) { // theme pinned to light
          const { context, page } = await open(language, width, theme);
          for (const surface of surfaces) {
            const response = await page.goto(base + surface.url);
            assert.equal(response.status(), 200, surface.name);
            assert.equal(response.headers()['content-language'], language);
            const heading = await page.locator('h1').innerText();
            assert(heading.includes(surface.headings[index]), `${surface.name}: ${heading}`);
            await check(page, language, theme);
            if (surface.name === 'detail') {
              assert((await page.locator('main').innerText()).includes('Prefiro instruções por escrito <original>'));
              assert.equal(await page.locator('main cadastro, main original').count(), 0);
              assert((await page.locator('main').innerText()).includes(['Mulher', 'Woman', 'Mujer'][index]));
            }
            if (surface.name === 'patients') assert(!(await page.locator('main').innerText()).includes('Paciente de outra clínica'));
            if (surface.name === 'professionals') {
              const table = await page.locator('table').innerText();
              assert(!/\b(clinic_admin|administrative_staff|therapist|active)\b/.test(table), table);
              assert(table.includes('Bruna Profissional <original>'));
              await page.locator('[role=region][tabindex="0"]').focus();
              assert(await page.locator('[role=region][tabindex="0"]').evaluate(element => document.activeElement === element));
            }
            // Focusing the table scrolls the document; reset before a full-page
            // capture so the fixed header does not obscure the page heading.
            await page.evaluate(() => window.scrollTo(0, 0));
            await page.screenshot({ path: `${output}/${surface.name}-${language}-${width}-${theme}.png`, fullPage: true });
            results.push({ surface: surface.name, language, width, theme, overflow: false });
          }
          await context.close();
        }
      }
      const { context, page } = await open(language, 320, 'dark');
      await page.goto(base + '/people/patients/new/');
      await page.locator('[name=full_name]').fill('Nome preservado <original>');
      await page.locator('[name=email]').fill('invalid-email');
      await Promise.all([page.waitForNavigation(), page.locator('main button[type=submit]').click()]);
      assert.equal(await page.locator('[name=full_name]').inputValue(), 'Nome preservado <original>');
      assert.equal(await page.locator('[name=email]').inputValue(), 'invalid-email');
      assert(await page.locator('main [aria-invalid=true]').count());
      assert(await page.locator('main [aria-invalid=true]').first().evaluate(element => document.activeElement === element));
      await check(page, language, 'dark');
      await page.screenshot({ path: `${output}/form-error-${language}-320-dark.png`, fullPage: true });
      results.push({ surface: 'form-error', language, preservedInput: true, invalidFieldFocused: true });
      await page.goto(base + '/people/professionals/');
      await page.locator('[name=status]').selectOption('active');
      await page.locator('[name=role]').selectOption('therapist');
      await page.locator('[name=specialty]').fill('sem-resultados-sinteticos');
      await Promise.all([page.waitForNavigation(), page.locator('main form[method=get] button[type=submit]').click()]);
      assert.equal(await page.locator('[name=status]').inputValue(), 'active');
      assert.equal(await page.locator('[name=role]').inputValue(), 'therapist');
      assert.equal(await page.locator('[name=specialty]').inputValue(), 'sem-resultados-sinteticos');
      assert.equal(await page.locator('main table tbody tr').count(), 0);
      await check(page, language, 'dark');
      await page.screenshot({ path: `${output}/professional-empty-${language}-320-dark.png`, fullPage: true });
      results.push({ surface: 'professional-empty', language, filtersPreserved: true });
      const foreign = await page.goto(base + fixture.foreign_url);
      assert.equal(foreign.status(), 403);
      assert(!(await page.locator('main').innerText()).includes('Paciente de outra clínica'));
      results.push({ surface: 'foreign-patient', language, denied: true });
      await context.close();
      const denied = await open(language, 320, 'dark', 'patient');
      for (const url of ['/people/patients/', '/people/patients/new/', '/people/professionals/']) {
        const response = await denied.page.goto(base + url);
        assert.equal(response.status(), 403);
        await check(denied.page, language, 'dark');
        results.push({ surface: url, language, role: 'patient', denied: true });
      }
      await denied.context.close();
    }
    assert.deepEqual(errors, []);
    fs.writeFileSync(`${output}/results.json`, JSON.stringify({ scope: 'People UI synthetic preview; en/es unpublished', results, errors }, null, 2) + '\n');
    console.log(`${results.length} people browser scenarios passed`);
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
