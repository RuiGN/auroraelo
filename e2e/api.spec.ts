import { test, expect } from "@playwright/test";

test.describe("API REST Endpoints", () => {
  test("unauthenticated journal request returns 401", async ({ request }) => {
    const response = await request.get("/api/v1/journal/entries/");
    expect(response.status()).toBe(401);
  });

  test("unauthenticated goals request returns 401", async ({ request }) => {
    const response = await request.get("/api/v1/goals/");
    expect(response.status()).toBe(401);
  });

  test("unauthenticated appointments request returns 401", async ({
    request,
  }) => {
    const response = await request.get("/api/v1/scheduling/appointments/");
    expect(response.status()).toBe(401);
  });

  test("unauthenticated scheduling services request returns 401", async ({
    request,
  }) => {
    const response = await request.get("/api/v1/scheduling/services/");
    expect(response.status()).toBe(401);
  });

  test("docs page renders Swagger UI", async ({ request }) => {
    const response = await request.get("/api/v1/docs/");
    expect(response.status()).toBe(200);
    const html = await response.text();
    expect(html).toContain("swagger");
  });
});
