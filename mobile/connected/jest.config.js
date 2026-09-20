module.exports = {
  preset: "jest-expo",
  testTimeout: 30000,
  modulePaths: ["<rootDir>/node_modules"],
  testMatch: ["<rootDir>/tests/**/*.test.[jt]s?(x)"],
  setupFilesAfterEnv: ["<rootDir>/tests/setup.js"],
};
