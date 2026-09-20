import { AuroraApiService } from "../src/services/api";

beforeEach(() => {
  global.fetch = jest.fn();
});

test.each(["getPatientSummary", "logMedication", "triggerSOS"] as const)(
  "%s falha fechado sem rede",
  async (method) => {
    await expect(AuroraApiService[method]()).rejects.toMatchObject({
      code: "unavailable",
    });
    expect(global.fetch).not.toHaveBeenCalled();
  },
);
