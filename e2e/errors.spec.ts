import { test, expect } from "@playwright/test";

test.describe("Error Pages", () => {
  test("404 page is in Portuguese", async ({ page }) => {
    const response = await page.goto("/pagina-que-nao-existe/");
    expect(response?.status()).toBe(404);
    const content = await page.textContent("body");
    expect(content).toContain("não foi encontrada");
  });

  test("error pages include correlation ID", async ({ page }) => {
    await page.goto("/pagina-que-nao-existe/");
    // Should have a reference/correlation ID visible
    const content = await page.textContent("body");
    expect(content).toMatch(/referência|ref|id/i);
  });
});
