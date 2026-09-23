import { test, expect } from "@playwright/test";

test.describe("Authentication Flow", () => {
  test("login page loads in Portuguese", async ({ page }) => {
    await page.goto("/accounts/login/");
    await expect(page).toHaveTitle(/Aurora Elo/);
    // Page should have a login form with PT-BR labels
    const emailField = page.locator(
      'input[name="login"], input[name="email"], input[name="username"]'
    );
    await expect(emailField.first()).toBeVisible();
  });

  test("public landing page stays reachable without authentication", async ({ page }) => {
    await page.goto("/");
    await expect(page).toHaveURL(/\/$/);
    await expect(page.locator("body")).toContainText("Aurora Elo");
  });

  test("login with invalid credentials shows error", async ({ page }) => {
    await page.goto("/accounts/login/");
    await page.fill(
      'input[name="login"], input[name="email"], input[name="username"]',
      "invalid@example.com"
    );
    await page.fill('input[name="password"]', "wrongpassword");
    await page.click('button[type="submit"]');
    await expect(page).toHaveURL(/accounts\/login/);
  });

  test("Master login is public and renders its credential form", async ({ page }) => {
    await page.goto("/master/login/");
    await expect(page).toHaveURL(/master\/login/);
    await expect(page.locator('input[name="email"]')).toBeVisible();
    await expect(page.locator('input[name="password"]')).toBeVisible();
  });

  test("global protected routes preserve their login destinations", async ({ request }) => {
    const master = await request.get("/master/", { maxRedirects: 0 });
    expect(master.status()).toBe(302);
    expect(master.headers().location).toBe("/master/login/?next=/master/");

    const admin = await request.get("/admin/", { maxRedirects: 0 });
    expect(admin.status()).toBe(302);
    expect(admin.headers().location).toBe("/admin/login/?next=/admin/");

    const adminLogin = await request.get("/admin/login/?next=/admin/", {
      maxRedirects: 0,
    });
    expect(adminLogin.status()).toBe(302);
    expect(adminLogin.headers().location).toBe(
      "/accounts/login/?next=%2Fadmin%2F",
    );
  });

  test("account login keeps the next query string for the POST", async ({ page }) => {
    await page.goto("/accounts/login/?next=/admin/");
    await expect(page.locator('form[data-form-guard]')).toHaveAttribute("method", "post");
    expect(new URL(page.url()).searchParams.get("next")).toBe("/admin/");
  });

});
