import { test, expect } from "@playwright/test";

test.describe("Health & Smoke", () => {
  test("liveness probe returns 200", async ({ request }) => {
    const response = await request.get("/health/alive/");
    expect(response.status()).toBe(200);
    const body = await response.json();
    expect(body.status).toBe("ok");
  });

  test("readiness probe returns 200", async ({ request }) => {
    const response = await request.get("/health/ready/");
    expect(response.status()).toBe(200);
    const body = await response.json();
    expect(body.status).toBe("ok");
  });

  test("API ping returns version", async ({ request }) => {
    const response = await request.get("/api/v1/ping/");
    expect(response.status()).toBe(200);
    const body = await response.json();
    expect(body.status).toBe("ok");
    expect(body.version).toBe("1.0.0");
  });

  test("OpenAPI spec is accessible", async ({ request }) => {
    const response = await request.get("/api/v1/openapi.json");
    expect(response.status()).toBe(200);
    const spec = await response.json();
    expect(spec.info.title).toBe("AuroraElo API");
  });
});
