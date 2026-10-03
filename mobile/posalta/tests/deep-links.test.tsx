import React, { ReactNode } from "react";
import { act, renderHook } from "@testing-library/react-native";
import { Linking } from "react-native";
import {
  DeepLinkProvider,
  parseDeepLink,
  useDeepLinks,
} from "../src/api/deepLinks";
import { SessionProvider } from "../src/api/session";
import { createMemoryTokenStore } from "../src/api/tokenStore";
import {
  BASE_URL,
  createFakeServer,
  storedSession,
  tokensBody,
} from "./fakeApi";

describe("parseDeepLink (função pura)", () => {
  it("lê o convite e a recuperação de senha", () => {
    expect(parseDeepLink("auroraelo-posalta://activate?code=Ab_c-123")).toEqual(
      { kind: "activate", code: "Ab_c-123" },
    );
    expect(
      parseDeepLink("auroraelo-posalta://reset?code=MQ.cg4xyz-abc123_9"),
    ).toEqual({ kind: "reset", code: "MQ.cg4xyz-abc123_9" });
  });

  it("aceita variações de forma: sem barras, barra final, maiúsculas e fragmento", () => {
    expect(parseDeepLink("auroraelo-posalta:activate?code=a1")).toEqual({
      kind: "activate",
      code: "a1",
    });
    expect(parseDeepLink("auroraelo-posalta:///reset/?code=a1#x")).toEqual({
      kind: "reset",
      code: "a1",
    });
    expect(parseDeepLink("AuroraElo-PosAlta://ACTIVATE?code=a1")).toEqual({
      kind: "activate",
      code: "a1",
    });
  });

  it("decodifica o código, ignora outros parâmetros e usa o primeiro `code`", () => {
    expect(
      parseDeepLink("auroraelo-posalta://reset?utm=x&code=MQ%2Eabc&code=zzz"),
    ).toEqual({ kind: "reset", code: "MQ.abc" });
    expect(
      parseDeepLink("auroraelo-posalta://activate?code=%20abc%20"),
    ).toEqual({ kind: "activate", code: "abc" });
  });

  it.each([
    "auroraelo-posalta://login?code=abc", // ação desconhecida
    "auroraelo-posalta://activate/extra?code=abc", // caminho extra
    "auroraelo-posalta://settings",
    "auroraelo-posalta://activate", // sem código
    "auroraelo-posalta://activate?code=",
    "auroraelo-posalta://activate?other=abc",
    "auroraelo-posalta://activate?code=a b",
    "auroraelo-posalta://activate?code=<script>",
    "auroraelo-posalta://activate?code=a/b",
    "auroraelo-posalta://activate?code=%E0%A4%A", // percent-encoding inválido
    "https://auroraelo-posalta/activate?code=abc",
    "https://api.clinica.test/activate?code=abc",
    "outro-app://activate?code=abc",
    "auroraelo-posalta-x://activate?code=abc",
    "http://activate?code=abc",
    "",
    "   ",
  ])("ignora %p", (url) => {
    expect(parseDeepLink(url)).toBeNull();
  });

  it("o código tem no máximo 256 caracteres", () => {
    const link = (size: number) =>
      `auroraelo-posalta://activate?code=${"a".repeat(size)}`;
    expect(parseDeepLink(link(256))).not.toBeNull();
    expect(parseDeepLink(link(257))).toBeNull();
  });

  it("ignora valores que não são texto ou são enormes", () => {
    expect(parseDeepLink(null)).toBeNull();
    expect(parseDeepLink(undefined)).toBeNull();
    expect(parseDeepLink(42 as unknown as string)).toBeNull();
    expect(
      parseDeepLink(
        `auroraelo-posalta://activate?code=a&x=${"b".repeat(3000)}`,
      ),
    ).toBeNull();
  });
});

type Listener = (event: { url: string }) => void;

/** Troca o Linking do RN: URL inicial configurável e eventos disparados à mão. */
function mockLinking(initial: string | null = null) {
  const listeners: Listener[] = [];
  const remove = jest.fn();
  jest.spyOn(Linking, "getInitialURL").mockResolvedValue(initial);
  jest.spyOn(Linking, "addEventListener").mockImplementation(((
    _type: string,
    listener: Listener,
  ) => {
    listeners.push(listener);
    return { remove };
  }) as never);
  return {
    emit: (url: string) => listeners.forEach((listener) => listener({ url })),
    remove,
    listeners,
  };
}

const settle = () =>
  act(async () => void (await jest.advanceTimersByTimeAsync(0)));

interface SetupOptions {
  signedIn?: boolean;
  mode?: "live" | "preview";
}

function setup({ signedIn = false, mode = "live" }: SetupOptions = {}) {
  const store = createMemoryTokenStore();
  const server = createFakeServer(() => ({ status: 200, body: tokensBody() }));
  const wrapper = ({ children }: { children: ReactNode }) => (
    <SessionProvider
      mode={mode}
      baseUrl={BASE_URL}
      transport={server.transport}
      tokenStore={store}
    >
      <DeepLinkProvider>{children}</DeepLinkProvider>
    </SessionProvider>
  );
  const prepared = signedIn ? store.save(storedSession(1)) : Promise.resolve();
  return { wrapper, store, prepared };
}

describe("DeepLinkProvider", () => {
  it("o link inicial vira pendente quando não há sessão ativa", async () => {
    mockLinking("auroraelo-posalta://activate?code=convite-123");
    const { wrapper } = setup();
    const { result } = renderHook(() => useDeepLinks(), { wrapper });
    await settle();
    expect(result.current.pending).toEqual({
      kind: "activate",
      code: "convite-123",
    });
    act(() => result.current.clear());
    expect(result.current.pending).toBeNull();
  });

  it("recebe links também com o app aberto (evento do Linking)", async () => {
    const linking = mockLinking(null);
    const { wrapper } = setup();
    const { result } = renderHook(() => useDeepLinks(), { wrapper });
    await settle();
    expect(result.current.pending).toBeNull();
    act(() => linking.emit("auroraelo-posalta://reset?code=MQ.abc-1"));
    expect(result.current.pending).toEqual({ kind: "reset", code: "MQ.abc-1" });
  });

  it("links com host/ação desconhecidos ou de outro esquema são ignorados", async () => {
    const linking = mockLinking("auroraelo-posalta://login?code=abc");
    const { wrapper } = setup();
    const { result } = renderHook(() => useDeepLinks(), { wrapper });
    await settle();
    for (const url of [
      "auroraelo-posalta://settings?code=abc",
      "https://evil.example/activate?code=abc",
      "auroraelo-posalta://activate?code=<x>",
    ]) {
      act(() => linking.emit(url));
    }
    expect(result.current.pending).toBeNull();
  });

  it("com sessão ativa um link de convite é ignorado e o pendente é descartado", async () => {
    const linking = mockLinking("auroraelo-posalta://activate?code=cedo");
    const { wrapper, prepared } = setup({ signedIn: true });
    await prepared;
    const { result } = renderHook(() => useDeepLinks(), { wrapper });
    await settle();
    // O link inicial chegou durante "restoring" e foi descartado ao ficar ativo.
    expect(result.current.pending).toBeNull();
    act(() => linking.emit("auroraelo-posalta://reset?code=tarde"));
    expect(result.current.pending).toBeNull();
  });

  it("no preview (sem sessão) nenhum link é aceito", async () => {
    const linking = mockLinking("auroraelo-posalta://activate?code=abc");
    const { wrapper } = setup({ mode: "preview" });
    const { result } = renderHook(() => useDeepLinks(), { wrapper });
    await settle();
    act(() => linking.emit("auroraelo-posalta://reset?code=abc"));
    expect(result.current.pending).toBeNull();
  });

  it("nunca escreve o código em console e remove o ouvinte ao desmontar", async () => {
    const spies = (["log", "info", "warn", "error", "debug"] as const).map(
      (method) => jest.spyOn(console, method).mockImplementation(() => {}),
    );
    const linking = mockLinking("auroraelo-posalta://activate?code=SEGREDO-1");
    const { wrapper } = setup();
    const { unmount } = renderHook(() => useDeepLinks(), { wrapper });
    await settle();
    act(() => linking.emit("auroraelo-posalta://reset?code=SEGREDO-2"));
    unmount();
    expect(linking.remove).toHaveBeenCalled();
    for (const spy of spies) {
      expect(spy).not.toHaveBeenCalled();
      spy.mockRestore();
    }
  });

  it("sem provider devolve um valor vazio (telas isoladas)", () => {
    const { result } = renderHook(() => useDeepLinks());
    expect(result.current.pending).toBeNull();
    expect(() => result.current.clear()).not.toThrow();
  });
});
