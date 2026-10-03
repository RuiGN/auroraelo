import AsyncStorage from "@react-native-async-storage/async-storage";
import { Platform } from "react-native";
import * as SecureStore from "expo-secure-store";
import {
  createDefaultTokenStore,
  createMemoryTokenStore,
  createSecureTokenStore,
  PROFILE_KEY,
  TOKENS_KEY,
} from "../src/api/tokenStore";
import { storedSession } from "./fakeApi";

// O mock de tests/setup.js guarda os itens em memória e expõe `__items`.
const vault = (SecureStore as unknown as { __items: Map<string, string> })
  .__items;

describe("armazenamento em memória (web e testes)", () => {
  it("guarda, devolve uma cópia e apaga", async () => {
    const store = createMemoryTokenStore();
    expect(await store.load()).toBeNull();
    await store.save(storedSession(1));
    const loaded = await store.load();
    expect(loaded).toEqual(storedSession(1));
    await store.clear();
    expect(await store.load()).toBeNull();
    await store.clear(); // idempotente
  });
});

describe("cofre seguro (iOS/Android)", () => {
  it("grava tokens e perfil em duas chaves, só neste aparelho", async () => {
    const store = createSecureTokenStore();
    await store.save(storedSession(1));
    expect([...vault.keys()].sort()).toEqual([PROFILE_KEY, TOKENS_KEY].sort());
    for (const call of (SecureStore.setItemAsync as jest.Mock).mock.calls) {
      expect(call[2]).toEqual({
        keychainAccessible: SecureStore.WHEN_UNLOCKED_THIS_DEVICE_ONLY,
      });
    }
    // Os tokens não vazam para o registro de perfil nem vice-versa.
    expect(vault.get(PROFILE_KEY)).not.toMatch(/aem_|aer_/);
    expect(vault.get(TOKENS_KEY)).not.toMatch(/Clínica|Alex/);
  });

  it("devolve a sessão guardada e apaga tudo no clear", async () => {
    const store = createSecureTokenStore();
    await store.save(storedSession(2));
    expect(await store.load()).toEqual(storedSession(2));
    await store.clear();
    expect(vault.size).toBe(0);
    expect(await store.load()).toBeNull();
  });

  it("sem nada guardado devolve null sem apagar nada", async () => {
    const store = createSecureTokenStore();
    expect(await store.load()).toBeNull();
    expect(SecureStore.deleteItemAsync).not.toHaveBeenCalled();
  });

  it.each([
    ["só os tokens", () => vault.delete(PROFILE_KEY)],
    ["só o perfil", () => vault.delete(TOKENS_KEY)],
    ["JSON inválido", () => vault.set(TOKENS_KEY, "{não é json")],
    ["campo ausente", () => vault.set(TOKENS_KEY, JSON.stringify({ a: 1 }))],
    [
      "expiração inválida",
      () =>
        vault.set(
          TOKENS_KEY,
          JSON.stringify({
            ...JSON.parse(vault.get(TOKENS_KEY) ?? "{}"),
            refreshExpiresAt: "ontem",
          }),
        ),
    ],
    ["tipo errado", () => vault.set(PROFILE_KEY, JSON.stringify([1, 2]))],
  ])(
    "leitura incompleta ou corrompida (%s) vira 'sem sessão' e é apagada",
    async (_name, corrupt) => {
      const store = createSecureTokenStore();
      await store.save(storedSession(1));
      corrupt();
      expect(await store.load()).toBeNull();
      expect(vault.size).toBe(0);
    },
  );

  it("falha de leitura do cofre vira 'sem sessão' (nunca rejeita)", async () => {
    (SecureStore.getItemAsync as jest.Mock).mockRejectedValueOnce(
      new Error("keystore"),
    );
    expect(await createSecureTokenStore().load()).toBeNull();
  });

  it("falha de gravação rejeita com erro genérico, sem eco do valor", async () => {
    (SecureStore.setItemAsync as jest.Mock).mockRejectedValueOnce(
      new Error("falhou ao gravar aer_refresh_1"),
    );
    const error = await createSecureTokenStore()
      .save(storedSession(1))
      .catch((caught: Error) => caught);
    expect(error).toBeInstanceOf(Error);
    expect((error as Error).message).toBe("token_store_write_failed");
  });

  it("uma falha ao apagar não impede apagar o outro item nem rejeita", async () => {
    const store = createSecureTokenStore();
    await store.save(storedSession(1));
    (SecureStore.deleteItemAsync as jest.Mock).mockRejectedValueOnce(
      new Error("x"),
    );
    await expect(store.clear()).resolves.toBeUndefined();
    expect(SecureStore.deleteItemAsync).toHaveBeenCalledTimes(2);
  });
});

describe("escolha do armazenamento por plataforma", () => {
  it("na web usa só memória: o cofre nem é tocado", async () => {
    const replaced = jest.replaceProperty(Platform, "OS", "web");
    try {
      const store = createDefaultTokenStore();
      await store.save(storedSession(1));
      expect(await store.load()).toEqual(storedSession(1));
      expect(SecureStore.setItemAsync).not.toHaveBeenCalled();
      expect(SecureStore.getItemAsync).not.toHaveBeenCalled();
      expect(vault.size).toBe(0);
    } finally {
      replaced.restore();
    }
  });

  it("no celular usa o cofre seguro", async () => {
    const store = createDefaultTokenStore();
    await store.save(storedSession(1));
    expect(SecureStore.setItemAsync).toHaveBeenCalledTimes(2);
  });
});

describe("AsyncStorage não guarda sessão", () => {
  it("depois de gravar a sessão não há nenhuma chave nele", async () => {
    await createSecureTokenStore().save(storedSession(1));
    await createMemoryTokenStore().save(storedSession(1));
    expect(await AsyncStorage.getAllKeys()).toEqual([]);
  });
});
