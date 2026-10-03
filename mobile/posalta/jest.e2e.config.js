// Roteiro ponta a ponta contra um servidor Django de verdade (ver tests/e2e/README.md).
// Sem relógio falso: as chamadas são reais.
module.exports = {
  preset: "jest-expo",
  testTimeout: 180000,
  modulePaths: ["<rootDir>/node_modules"],
  testMatch: ["<rootDir>/tests/e2e/**/*.e2e.ts"],
  setupFilesAfterEnv: ["<rootDir>/tests/setup.js"],
};
