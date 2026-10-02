module.exports = {
  preset: "jest-expo",
  testTimeout: 30000,
  modulePaths: ["<rootDir>/node_modules"],
  testMatch: ["<rootDir>/tests/**/*.test.[jt]s?(x)"],
  setupFilesAfterEnv: ["<rootDir>/tests/setup.js"],
  // Temporizadores falsos: a barra de abas agenda atualizações internas com setTimeout.
  fakeTimers: { enableGlobally: true },
};
