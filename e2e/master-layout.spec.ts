import { test, expect } from "@playwright/test";
import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";
import path from "node:path";

// Somente templates/dados sintéticos. Autorização e persistência são testadas no pytest.
const snapshots: Record<string, string> = JSON.parse(execFileSync(
  ".venv/bin/python", ["-m", "tests.render_master_layout"],
  { encoding: "utf8", env: { ...process.env, DJANGO_SETTINGS_MODULE: "config.settings.test", TEST_DATABASE: "sqlite" } },
));

for (const width of [320, 390, 768, 1024, 1440]) {
  for (const route of ["/master/login/", "/master/", "/administracao/"]) {
    test(`${route} geometria ${width}px`, async ({ page }) => {
      await page.setViewportSize({ width, height: 800 });
      const errors: string[] = [];
      page.on("pageerror", error => errors.push(error.message));
      page.on("console", message => { if (message.type() === "error") errors.push(message.text()); });
      await page.route("**/*", async request => {
        const pathname = new URL(request.request().url()).pathname;
        if (snapshots[pathname]) {
          await request.fulfill({ contentType: "text/html", body: snapshots[pathname], headers: {
            "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self' data:",
          } });
        } else if (pathname.startsWith("/static/")) {
          const file = path.resolve("static", pathname.slice(8));
          expect(file.startsWith(path.resolve("static") + path.sep)).toBeTruthy();
          const mime = { ".css": "text/css", ".js": "application/javascript", ".svg": "image/svg+xml", ".png": "image/png", ".woff": "font/woff", ".ttf": "font/ttf" };
          await request.fulfill({ body: readFileSync(file), contentType: mime[path.extname(file)] || "application/octet-stream" });
        } else {
          errors.push(`Recurso inesperado: ${pathname}`);
          await request.abort();
        }
      });
      await page.goto(route);
      await page.evaluate(() => document.fonts.ready);
      const geometry = await page.evaluate(() => ({
        viewport: innerWidth,
        document: document.documentElement.scrollWidth,
        body: document.body.scrollWidth,
      }));

      const overflow = await page.locator(".master-content, .master-panel-card, .master-table-scroll").evaluateAll(elements => elements.map(e => ({class: e.className, width: e.getBoundingClientRect().width, overflow: getComputedStyle(e).overflowX, display: getComputedStyle(e).display})));
      expect(geometry.document, JSON.stringify({ overflow, errors })).toBeLessThanOrEqual(width);
      expect(geometry.body).toBeLessThanOrEqual(width);
      if (route.includes("login")) {
        for (const name of ["email", "password"]) {
          const input = page.locator(`input[name="${name}"]`);
          await input.fill(name === "email" ? "teste@example.test" : "synthetic-ui-only");
          const spacing = await input.evaluate(element => {
            const rect = element.getBoundingClientRect();
            const icon = element.parentElement!.querySelector(".field-control-icon")!.getBoundingClientRect();
            const padding = parseFloat(getComputedStyle(element).paddingLeft);
            return { gap: rect.left + padding - icon.right, right: rect.right };
          });
          expect(spacing.gap).toBeGreaterThanOrEqual(8);
          expect(spacing.right).toBeLessThanOrEqual(width);
        }
      } else {
        const toggle = page.locator("[data-master-menu-toggle]");
        if (await toggle.isVisible()) {
          await toggle.click();
          await expect(toggle).toHaveAttribute("aria-expanded", "true");
          await page.keyboard.press("Escape");
          await expect(toggle).toHaveAttribute("aria-expanded", "false");
        }
      }
      expect(errors).toEqual([]);
    });
  }
}
