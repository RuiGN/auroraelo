import { defineConfig, devices } from "@playwright/test";

/**
 * AuroraElo E2E — Playwright configuration.
 *
 * @see https://playwright.dev/docs/test-configuration
 */
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: [["html", { open: "never" }], ["list"]],

  use: {
    baseURL: process.env.BASE_URL || "http://localhost:8000",
    trace: "on-first-retry",
    screenshot: "only-on-failure",
    locale: "pt-BR",
    timezoneId: "America/Sao_Paulo",
  },

  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],

  /* Run the Django dev server before tests if not in CI. */
  webServer: process.env.CI
    ? undefined
    : {
        command: "python manage.py runserver --noreload",
        url: "http://localhost:8000/health/alive/",
        reuseExistingServer: !process.env.CI,
        timeout: 30_000,
      },
});
