#!/usr/bin/env node
"use strict";

const fs = require("node:fs");
const path = require("node:path");
const crypto = require("node:crypto");
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || "playwright");

const root = path.resolve(__dirname, "..");
const fixtures = JSON.parse(
  fs.readFileSync(path.join(root, ".migration-runtime/auth-preview-fixtures.json"), "utf8"),
);
const outputDir = path.join(root, "docs/migration/evidence/visual-auth");
fs.mkdirSync(outputDir, { recursive: true });

function decodeBase32(value) {
  const alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567";
  let bits = "";
  for (const character of value.replace(/=+$/, "").toUpperCase()) {
    bits += alphabet.indexOf(character).toString(2).padStart(5, "0");
  }
  const bytes = [];
  for (let index = 0; index + 8 <= bits.length; index += 8) {
    bytes.push(Number.parseInt(bits.slice(index, index + 8), 2));
  }
  return Buffer.from(bytes);
}

function currentTotp(secret) {
  const counter = Math.floor(Date.now() / 1000 / 30);
  const buffer = Buffer.alloc(8);
  buffer.writeBigUInt64BE(BigInt(counter));
  const digest = crypto.createHmac("sha1", decodeBase32(secret)).update(buffer).digest();
  const offset = digest[digest.length - 1] & 0x0f;
  const binary = (digest.readUInt32BE(offset) & 0x7fffffff) % 1_000_000;
  return binary.toString().padStart(6, "0");
}

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

async function setSessionCookie(context, value) {
  await context.addCookies([
    {
      name: "sessionid",
      value,
      url: fixtures.base_url,
      httpOnly: true,
      sameSite: "Lax",
    },
  ]);
}

(async () => {
  const browser = await chromium.launch({ headless: true });
  const results = [];
  const viewports = [
    { name: "mobile", width: 320, height: 800 },
    { name: "desktop", width: 1440, height: 1000 },
  ];
  const themes = ["light", "dark"];
  const states = [
    "auth",
    "recovery",
    "reset",
    "invalid-reset",
    "invite",
    "enroll",
    "challenge",
    "sessions",
  ];
  let recoveryIndex = 0;

  try {
    for (const viewport of viewports) {
      for (const theme of themes) {
        for (const state of states) {
          const context = await browser.newContext({
            viewport: { width: viewport.width, height: viewport.height },
            colorScheme: theme,
          });
          if (fixtures.cookies[state]) {
            await setSessionCookie(context, fixtures.cookies[state]);
          }
          const page = await context.newPage();
          const pageErrors = [];
          page.on("pageerror", (error) => pageErrors.push(error.message));
          page.on("requestfailed", (request) => {
            if (
              request.resourceType() !== "favicon" &&
              request.failure()?.errorText !== "net::ERR_ABORTED"
            ) {
              pageErrors.push(`${request.method()} ${request.url()}: ${request.failure()?.errorText}`);
            }
          });

          const response = await page.goto(`${fixtures.base_url}${fixtures.urls[state]}`, {
            waitUntil: "networkidle",
          });
          const expectedStatus = state === "invalid-reset" ? 400 : 200;
          assert(response?.status() === expectedStatus, `${state}: HTTP ${response?.status()}`);
          assert(
            (await page.locator("html").getAttribute("data-bs-theme")) === theme,
            `${state}: theme ${theme} was not applied`,
          );

          if (state === "auth") {
            await page.locator('input[name="email"]').fill("endereco-invalido");
            await page.locator('button[type="submit"]').click();
            await page.waitForLoadState("networkidle");
            assert(await page.locator("#id_email_error_0").isVisible(), "login error missing");
            assert(
              (await page.evaluate(() => document.activeElement?.id)) === "id_email",
              "invalid login did not focus the first invalid field",
            );
          }
          if (state === "recovery") {
            await page.locator('input[name="email"]').fill(`preview-${viewport.name}-${theme}@example.test`);
            await page.getByRole("button", { name: "Enviar instruções" }).click();
            await page.waitForLoadState("networkidle");
            assert(await page.locator('[role="status"]').isVisible(), "generic recovery status missing");
            assert(await page.locator(".feather-info").isVisible(), "recovery message icon is not neutral");
          }
          if (state === "invalid-reset") {
            assert(await page.locator('[role="status"]').isVisible(), "invalid reset guidance missing");
            assert(await page.locator(".feather-info").isVisible(), "invalid reset icon is not neutral");
            assert((await page.locator(".feather-check-circle").count()) === 0, "invalid reset implies success");
          }
          if (state === "enroll") {
            await page.locator('input[name="code"]').fill("not-a-code");
            await page.getByRole("button", { name: "Ativar proteção" }).click();
            await page.waitForLoadState("networkidle");
            assert(await page.locator("#id_code_error_0").isVisible(), "enrollment error missing");
            assert(
              (await page.evaluate(() => document.activeElement?.id)) === "id_code",
              "invalid enrollment did not focus the code field",
            );
            const qr = page.locator('.product-auth-qr img[src^="data:image/svg+xml;base64,"]');
            assert(await qr.isVisible(), "enrollment QR is not visible");
            assert(await qr.evaluate((image) => image.naturalWidth > 0), "enrollment QR did not load");
            assert(
              (await qr.evaluate((image) => getComputedStyle(image).backgroundColor)) ===
                "rgb(255, 255, 255)",
              "enrollment QR does not retain a white scanning background",
            );
            assert(await page.locator("#mfa-manual-secret").isVisible(), "manual secret missing");
          }
          if (state === "challenge") {
            assert(await page.locator('input[name="code"]').isVisible(), "challenge input missing");
            assert((await page.locator(".product-auth-qr").count()) === 0, "challenge exposed QR");
          }
          if (state === "sessions") {
            assert(await page.getByText("Firefox em computador").isVisible(), "active session missing");
            assert(await page.getByText("Safari em celular").isVisible(), "revoked session missing");
            assert(await page.getByText("Encerrada").isVisible(), "revoked status missing");
            await page.locator('input[name="password"]').fill("senha-incorreta");
            await page.getByRole("button", { name: "Encerrar todas as outras sessões" }).click();
            await page.waitForLoadState("networkidle");
            assert(await page.locator("#id_password_error_0").isVisible(), "session password error missing");
            assert(
              (await page.locator('input[name="password"]').getAttribute("aria-describedby")) ===
                "id_password_error_0",
              "session password error is not associated",
            );
            assert(
              (await page.evaluate(() => document.activeElement?.id)) === "id_password",
              "session password error did not receive focus",
            );
          }

          const overflow = await page.evaluate(
            () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
          );
          assert(overflow <= 1, `${state}: horizontal overflow of ${overflow}px`);
          assert(pageErrors.length === 0, `${state}: ${pageErrors.join("; ")}`);
          const name = `${state}-${viewport.name}-${theme}.png`;
          await page.evaluate(() => window.scrollTo(0, 0));
          await page.screenshot({ path: path.join(outputDir, name), fullPage: true });
          results.push({ state, viewport: viewport.name, theme, ok: true, screenshot: name });
          await context.close();
        }

        const recoveryFixture = fixtures.recovery[recoveryIndex++];
        const context = await browser.newContext({
          viewport: { width: viewport.width, height: viewport.height },
          colorScheme: theme,
        });
        await setSessionCookie(context, recoveryFixture.cookie);
        await context.addInitScript((selectedTheme) => {
          localStorage.setItem("product-theme", selectedTheme);
        }, theme);
        const page = await context.newPage();
        const pageErrors = [];
        page.on("pageerror", (error) => pageErrors.push(error.message));
        await page.goto(`${fixtures.base_url}${fixtures.urls.enroll}`, { waitUntil: "networkidle" });
        await page.locator('input[name="code"]').fill(currentTotp(recoveryFixture.secret));
        await page.getByRole("button", { name: "Ativar proteção" }).click();
        await page.waitForLoadState("networkidle");
        assert((await page.locator('[aria-label="Códigos de recuperação"] li').count()) === 8, "recovery code count differs from 8");
        const overflow = await page.evaluate(
          () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
        );
        assert(overflow <= 1, `recovery codes: horizontal overflow of ${overflow}px`);
        assert(pageErrors.length === 0, `recovery codes: ${pageErrors.join("; ")}`);
        const name = `recovery-codes-${viewport.name}-${theme}.png`;
        await page.evaluate(() => window.scrollTo(0, 0));
        await page.screenshot({ path: path.join(outputDir, name), fullPage: true });
        results.push({ state: "recovery-codes", viewport: viewport.name, theme, ok: true, screenshot: name });
        await context.close();
      }
    }
  } finally {
    await browser.close();
  }

  const report = {
    generated_at: new Date().toISOString(),
    base_url: fixtures.base_url,
    cases: results.length,
    results,
  };
  fs.writeFileSync(
    path.join(outputDir, "results.json"),
    `${JSON.stringify(report, null, 2)}\n`,
    "utf8",
  );
  process.stdout.write(`${results.length} visual auth cases passed\n`);
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
