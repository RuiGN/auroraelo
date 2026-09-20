import * as safety from "../../shared/safety";

test("gate IA fechado, sem consentimento implícito ou chamada LLM", async () => {
  const transport = jest.fn();
  global.fetch = transport;
  expect(safety.DIGITAL_SUPPORT).toEqual({ enabled: false, consent: false });
  expect(Object.isFrozen(safety.DIGITAL_SUPPORT)).toBe(true);
  await expect(safety.startDigitalSupport()).rejects.toMatchObject({
    code: "unavailable",
  });
  expect(transport).not.toHaveBeenCalled();
});
