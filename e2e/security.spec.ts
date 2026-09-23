import { test, expect } from "@playwright/test";

test.describe("Security Headers", () => {
  test("X-Content-Type-Options is nosniff", async ({ request }) => {
    const response = await request.get("/health/live/");
    expect(response.headers()["x-content-type-options"]).toBe("nosniff");
  });

  test("X-Frame-Options is set", async ({ request }) => {
    const response = await request.get("/health/live/");
    const header = response.headers()["x-frame-options"];
    expect(header).toBeTruthy();
  });

  test("response includes correlation ID header", async ({ request }) => {
    const response = await request.get("/health/live/");
    const requestId = response.headers()["x-request-id"];
    expect(requestId).toBeTruthy();
    expect(requestId.length).toBeGreaterThan(0);
  });
});
