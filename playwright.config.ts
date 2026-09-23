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

  /* CI and local runs both start an isolated Django test server. */
  webServer: {
    command:
      "DJANGO_SETTINGS_MODULE=config.settings.test .venv/bin/python manage.py runserver 127.0.0.1:8000 --noreload",
    url: "http://127.0.0.1:8000/health/live/",
    reuseExistingServer: !process.env.CI,
    timeout: 30_000,
  },
});
