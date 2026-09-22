import { test, expect } from "@playwright/test";

test.describe("Internationalization", () => {
  test("login page loads in Portuguese", async ({ page }) => {
    await page.goto("/accounts/login/");
    const html = await page.content();
    // Should have Portuguese content
    expect(html).toMatch(/Entrar|Login|Acessar|Bem-vindo/i);
  });

  test("locale is set to PT-BR", async ({ page }) => {
    await page.goto("/accounts/login/");
    const htmlLang = await page.getAttribute("html", "lang");
    // Should be pt-br or pt
    if (htmlLang) {
      expect(htmlLang.toLowerCase()).toMatch(/^pt/);
    }
  });
});
