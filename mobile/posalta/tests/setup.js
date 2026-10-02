require("@testing-library/react-native/extend-expect");
jest.mock(
  "react-native-safe-area-context",
  () => require("react-native-safe-area-context/jest/mock").default,
);

jest.mock("@react-native-async-storage/async-storage", () =>
  require("@react-native-async-storage/async-storage/jest/async-storage-mock"),
);

// Cofre seguro em memória (Keychain/Keystore não existem no Jest). `__items` expõe o
// conteúdo para os testes conferirem o que foi (ou não) gravado.
jest.mock("expo-secure-store", () => {
  const items = new Map();
  return {
    AFTER_FIRST_UNLOCK: 0,
    AFTER_FIRST_UNLOCK_THIS_DEVICE_ONLY: 1,
    ALWAYS: 2,
    WHEN_PASSCODE_SET_THIS_DEVICE_ONLY: 3,
    ALWAYS_THIS_DEVICE_ONLY: 4,
    WHEN_UNLOCKED: 5,
    WHEN_UNLOCKED_THIS_DEVICE_ONLY: 6,
    __items: items,
    getItemAsync: jest.fn(async (key) =>
      items.has(key) ? items.get(key) : null,
    ),
    setItemAsync: jest.fn(async (key, value) => {
      items.set(key, value);
    }),
    deleteItemAsync: jest.fn(async (key) => {
      items.delete(key);
    }),
  };
});

// Cada teste começa sem preferências, sem sessão guardada e sem histórico de chamadas.
beforeEach(async () => {
  const AsyncStorage = require("@react-native-async-storage/async-storage");
  await (AsyncStorage.default ?? AsyncStorage).clear();
  require("expo-secure-store").__items.clear();
  jest.clearAllMocks();
});
