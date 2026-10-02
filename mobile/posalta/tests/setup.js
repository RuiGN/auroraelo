require("@testing-library/react-native/extend-expect");
jest.mock(
  "react-native-safe-area-context",
  () => require("react-native-safe-area-context/jest/mock").default,
);

jest.mock("@react-native-async-storage/async-storage", () =>
  require("@react-native-async-storage/async-storage/jest/async-storage-mock"),
);

// Cada teste começa sem preferências gravadas e sem histórico de chamadas.
beforeEach(async () => {
  const AsyncStorage = require("@react-native-async-storage/async-storage");
  await (AsyncStorage.default ?? AsyncStorage).clear();
  jest.clearAllMocks();
});
