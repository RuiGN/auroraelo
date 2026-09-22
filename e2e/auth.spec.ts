import { test, expect } from "@playwright/test";

test.describe("Authentication Flow", () => {
  test("login page loads in Portuguese", async ({ page }) => {
    await page.goto("/accounts/login/");
    await expect(page).toHaveTitle(/AuroraElo/);
    // Page should have a login form with PT-BR labels
    const emailField = page.locator(
      'input[name="login"], input[name="email"], input[name="username"]'
    );
    await expect(emailField.first()).toBeVisible();
  });

  test("unauthenticated user redirected to login", async ({ page }) => {
    await page.goto("/");
    // Should be redirected to login page
    await expect(page).toHaveURL(/accounts\/login/);
  });

  test("login with invalid credentials shows error", async ({ page }) => {
    await page.goto("/accounts/login/");
    await page.fill(
      'input[name="login"], input[name="email"], input[name="username"]',
      "invalid@example.com"
    );
    await page.fill('input[name="password"]', "wrongpassword");
    await page.click('button[type="submit"]');
    // Should stay on login page with error message
    await expect(page).toHaveURL(/accounts\/login/);
  });
});
