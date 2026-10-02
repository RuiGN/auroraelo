import React, { ReactNode } from "react";
import { act, renderHook } from "@testing-library/react-native";
import { Platform } from "react-native";
import { describeDevice } from "../src/api/deviceInfo";
import { Session, SessionProvider, useSession } from "../src/api/session";
import { createMemoryTokenStore, TokenStore } from "../src/api/tokenStore";
import {
  BASE_URL,
  createFakeServer,
  FakeServer,
  Handler,
  hang,
  networkFailure,
  storedSession,
  tokensBody,
} from "./fakeApi";

const DEVICE = {
  deviceLabel: "iPhone",
  platform: "ios",
  appVersion: "1.2.3",
} as const;

const settle = () =>
  act(async () => void (await jest.advanceTimersByTimeAsync(0)));

interface Setup {
  session: () => Session;
  server: FakeServer;
  store: TokenStore;
  unmount: () => void;
}

async function setup(
  handler: Handler,
  options: {
    signedIn?: boolean;
    mode?: "live" | "preview";
    baseUrl?: string | null;
  } = {},
): Promise<Setup> {
  const server = createFakeServer(handler);
  const store = createMemoryTokenStore();
  if (options.signedIn) await store.save(storedSession(1));
  const wrapper = ({ children }: { children: ReactNode }) => (
    <SessionProvider
      mode={options.mode ?? "live"}
      baseUrl={options.baseUrl === undefined ? BASE_URL : options.baseUrl}
      transport={server.transport}
      tokenStore={store}
      device={() => DEVICE}
    >
      {children}
    </SessionProvider>
  );
  const { result, unmount } = renderHook(() => useSession(), { wrapper });
  await settle();
  return { session: () => result.current, server, store, unmount };
}

/** Roteia por caminho: o teste só declara o que quer de cada rota. */
function routes(map: Record<string, Handler | ReturnType<Handler>>): Handler {
  return (call) => {
    const entry = map[call.path];
    if (entry === undefined)
      return { status: 404, body: { code: "not_found" } };
    return typeof entry === "function" ? entry(call) : entry;
  };
}

describe("estados", () => {
  it("preview não usa sessão, nem rede, nem cofre", async () => {
    const { session, server, store } = await setup(routes({}), {
      mode: "preview",
      signedIn: true,
    });
    expect(session().status).toBe("disabled");
    expect(session().api).toBeNull();
    expect(server.calls).toHaveLength(0);
    // A sessão guardada nem foi lida.
    expect(await store.load()).not.toBeNull();
  });

  it("live sem endereço válido do servidor: disabled (tela de configuração)", async () => {
    const { session, server } = await setup(routes({}), { baseUrl: null });
    expect(session().status).toBe("disabled");
    expect(session().api).toBeNull();
    expect(server.calls).toHaveLength(0);
  });

  it("sem sessão guardada: restoring → signedOut, sem chamar a rede", async () => {
    const { session, server } = await setup(routes({}));
    expect(session().status).toBe("signedOut");
    expect(session().info).toBeNull();
    expect(server.calls).toHaveLength(0);
  });

  it("com sessão guardada: restoring → active só com dados não sensíveis, sem rede", async () => {
    const { session, server } = await setup(routes({}), { signedIn: true });
    expect(session().status).toBe("active");
    expect(session().info).toEqual({
      sessionId: "11111111-1111-4111-8111-111111111111",
      clinic: {
        id: "22222222-2222-4222-8222-222222222222",
        name: "Clínica Aurora",
      },
      patient: {
        id: "33333333-3333-4333-8333-333333333333",
        displayName: "Alex Paciente",
      },
    });
    expect(server.calls).toHaveLength(0);
    // Nenhum token no que a interface enxerga.
    expect(JSON.stringify(session().info)).not.toMatch(/aem_|aer_/);
  });

  it("o `api` exposto a loaders e ações só tem get/post/put/delete", async () => {
    const { session } = await setup(routes({}), { signedIn: true });
    expect(Object.keys(session().api ?? {}).sort()).toEqual([
      "delete",
      "get",
      "post",
      "put",
    ]);
  });
});

describe("entrar", () => {
  const ok = routes({
    "/mobile/auth/login/": { status: 200, body: tokensBody(1) },
  });

  it("envia e-mail aparado, senha e dados do aparelho, sem token", async () => {
    const { session, server, store } = await setup(ok);
    let result: Awaited<ReturnType<Session["login"]>> | undefined;
    await act(async () => {
      result = await session().login({
        email: "  alex@example.com ",
        password: "senha-secreta",
      });
    });
    expect(result).toEqual({ ok: true });
    const [call] = server.callsTo("/mobile/auth/login/");
    expect(call.body).toEqual({
      email: "alex@example.com",
      password: "senha-secreta",
      device_label: "iPhone",
      platform: "ios",
      app_version: "1.2.3",
    });
    expect(call.headers.Authorization).toBeUndefined();
    expect(session().status).toBe("active");
    expect(session().info?.patient.displayName).toBe("Alex Paciente");
    // Os tokens foram para o cofre e não para o estado.
    expect((await store.load())?.refreshToken).toBe("aer_refresh_1");
    expect(JSON.stringify(session().info)).not.toMatch(/aem_|aer_|senha/);
  });

  it("credenciais inválidas: continua sem sessão e nada é guardado", async () => {
    const { session, store } = await setup(
      routes({
        "/mobile/auth/login/": {
          status: 401,
          body: {
            detail: "E-mail ou senha inválidos.",
            code: "invalid_credentials",
          },
        },
      }),
    );
    let result: Awaited<ReturnType<Session["login"]>> | undefined;
    await act(async () => {
      result = await session().login({ email: "a@b.c", password: "x" });
    });
    expect(result).toEqual({ ok: false, reason: "invalid_credentials" });
    expect(session().status).toBe("signedOut");
    expect(await store.load()).toBeNull();
  });

  it("mais de uma clínica: devolve a lista e reenvia com clinic_id", async () => {
    const clinics = [
      { id: "c1", name: "Clínica Norte" },
      { id: "c2", name: "Clínica Sul" },
    ];
    const { session, server } = await setup((call) =>
      call.body.clinic_id
        ? { status: 200, body: tokensBody(1) }
        : {
            status: 409,
            body: {
              detail: "Escolha a clínica para continuar.",
              code: "clinic_choice_required",
              clinics,
            },
          },
    );
    let first: Awaited<ReturnType<Session["login"]>> | undefined;
    await act(async () => {
      first = await session().login({ email: "a@b.c", password: "x" });
    });
    expect(first).toEqual({ ok: false, reason: "clinic_choice", clinics });
    expect(session().status).toBe("signedOut");
    await act(async () => {
      await session().login({ email: "a@b.c", password: "x", clinicId: "c2" });
    });
    expect(server.calls[1].body.clinic_id).toBe("c2");
    expect(session().status).toBe("active");
  });

  it.each([
    {
      name: "429",
      reply: { status: 429, body: { detail: "x", code: "rate_limited" } },
      reason: "rate_limited",
    },
    {
      name: "402",
      reply: { status: 402, body: { detail: "x" } },
      reason: "blocked",
    },
    {
      name: "500",
      reply: { status: 500, body: { detail: "x" } },
      reason: "unexpected",
    },
    {
      name: "200 com corpo inválido",
      reply: { status: 200, body: { access_token: 1 } },
      reason: "unexpected",
    },
  ])("falha $name vira o motivo $reason", async ({ reply, reason }) => {
    const { session, store } = await setup(() => reply);
    let result: Awaited<ReturnType<Session["login"]>> | undefined;
    await act(async () => {
      result = await session().login({ email: "a@b.c", password: "x" });
    });
    expect(result).toMatchObject({ ok: false, reason });
    expect(session().status).toBe("signedOut");
    expect(await store.load()).toBeNull();
  });

  it("sem rede: 'offline'", async () => {
    const { session } = await setup(() => networkFailure());
    let result: Awaited<ReturnType<Session["login"]>> | undefined;
    await act(async () => {
      result = await session().login({ email: "a@b.c", password: "x" });
    });
    expect(result).toEqual({ ok: false, reason: "offline" });
  });

  it("toque duplo: uma única requisição de entrada", async () => {
    const { session, server } = await setup(ok);
    await act(async () => {
      const input = { email: "a@b.c", password: "x" };
      await Promise.all([session().login(input), session().login(input)]);
    });
    expect(server.callsTo("/mobile/auth/login/")).toHaveLength(1);
  });
});

describe("ativar conta", () => {
  it("envia código, senha e nome e já abre a sessão", async () => {
    const { session, server } = await setup(
      routes({
        "/mobile/auth/activate/": { status: 200, body: tokensBody(1) },
      }),
    );
    await act(async () => {
      await session().activate({
        code: " convite-1 ",
        password: "uma senha longa",
        firstName: " Alex ",
        lastName: "Paciente",
      });
    });
    expect(server.calls[0].body).toEqual({
      code: "convite-1",
      password: "uma senha longa",
      first_name: "Alex",
      last_name: "Paciente",
      device_label: "iPhone",
      platform: "ios",
      app_version: "1.2.3",
    });
    expect(session().status).toBe("active");
  });

  it("senha fraca devolve a lista do servidor; código inválido tem motivo próprio", async () => {
    let reply: any = {
      status: 422,
      body: {
        detail: "Senha não aceita.",
        code: "weak_password",
        errors: ["Esta senha é muito curta."],
      },
    };
    const { session } = await setup(() => reply);
    let result: any;
    await act(async () => {
      result = await session().activate({
        code: "c",
        password: "123",
        firstName: "",
        lastName: "",
      });
    });
    expect(result).toEqual({
      ok: false,
      reason: "weak_password",
      errors: ["Esta senha é muito curta."],
    });
    reply = {
      status: 422,
      body: { detail: "x", code: "invalid_code", errors: [] },
    };
    await act(async () => {
      result = await session().activate({
        code: "c",
        password: "123456789",
        firstName: "",
        lastName: "",
      });
    });
    expect(result).toEqual({ ok: false, reason: "invalid_code" });
    expect(session().status).toBe("signedOut");
  });
});

describe("recuperar e redefinir a senha", () => {
  it("recuperação: resposta neutra (202) e erros de limite/rede", async () => {
    let handler: Handler = () => ({
      status: 202,
      body: { detail: "Se o e-mail existir..." },
    });
    const { session, server } = await setup((call) => handler(call));
    let result: any;
    await act(async () => {
      result = await session().requestRecovery(" alex@example.com ");
    });
    expect(result).toEqual({ ok: true });
    expect(server.calls[0].body).toEqual({ email: "alex@example.com" });
    expect(server.calls[0].headers.Authorization).toBeUndefined();
    handler = () => ({
      status: 429,
      body: { detail: "x", code: "rate_limited" },
    });
    await act(async () => {
      result = await session().requestRecovery("a@b.c");
    });
    expect(result).toEqual({ ok: false, reason: "rate_limited" });
    handler = () => networkFailure();
    await act(async () => {
      result = await session().requestRecovery("a@b.c");
    });
    expect(result).toEqual({ ok: false, reason: "offline" });
  });

  it("redefinição (204): avisa na tela de entrada e não abre sessão", async () => {
    const { session, server } = await setup(
      routes({ "/mobile/auth/password-reset/": { status: 204 } }),
    );
    let result: any;
    await act(async () => {
      result = await session().resetPassword({
        code: " MQ.abc ",
        newPassword: "nova senha longa",
      });
    });
    expect(result).toEqual({ ok: true });
    expect(server.calls[0].body).toEqual({
      code: "MQ.abc",
      new_password: "nova senha longa",
    });
    expect(session().status).toBe("signedOut");
    expect(session().notice).toBe("password_reset");
    act(() => session().clearNotice());
    expect(session().notice).toBeNull();
  });

  it("código inválido (400) e senha fraca (422)", async () => {
    let reply: any = {
      status: 400,
      body: { detail: "x", code: "invalid_code" },
    };
    const { session } = await setup(() => reply);
    let result: any;
    await act(async () => {
      result = await session().resetPassword({ code: "x", newPassword: "y" });
    });
    expect(result).toEqual({ ok: false, reason: "invalid_code" });
    reply = {
      status: 422,
      body: { detail: "x", code: "weak_password", errors: ["Curta demais."] },
    };
    await act(async () => {
      result = await session().resetPassword({ code: "x", newPassword: "y" });
    });
    expect(result).toEqual({
      ok: false,
      reason: "weak_password",
      errors: ["Curta demais."],
    });
    expect(session().notice).toBeNull();
  });
});

describe("sair", () => {
  const loggedOut = routes({ "/mobile/auth/logout/": { status: 204 } });

  it("avisa o servidor e limpa tokens e estado", async () => {
    const { session, server, store } = await setup(loggedOut, {
      signedIn: true,
    });
    await act(async () => {
      await session().logout();
    });
    const [call] = server.callsTo("/mobile/auth/logout/");
    expect(call.headers.Authorization).toBe("Bearer aem_access_1");
    expect(session().status).toBe("signedOut");
    expect(session().info).toBeNull();
    expect(session().notice).toBeNull();
    expect(await store.load()).toBeNull();
  });

  it("sem rede ainda assim sai neste aparelho", async () => {
    const { session, store } = await setup(() => networkFailure(), {
      signedIn: true,
    });
    await act(async () => {
      await session().logout();
    });
    expect(session().status).toBe("signedOut");
    expect(await store.load()).toBeNull();
  });

  it("servidor que não responde: sai depois de 5 s", async () => {
    const { session, store } = await setup((call) => hang(call), {
      signedIn: true,
    });
    let done = false;
    act(() => {
      void session()
        .logout()
        .then(() => {
          done = true;
        });
    });
    await act(async () => void (await jest.advanceTimersByTimeAsync(4_000)));
    expect(done).toBe(false);
    await act(async () => void (await jest.advanceTimersByTimeAsync(1_500)));
    expect(done).toBe(true);
    expect(session().status).toBe("signedOut");
    expect(await store.load()).toBeNull();
  });

  it("clínica bloqueada (402) não impede sair", async () => {
    const { session, store } = await setup(
      routes({
        "/mobile/auth/logout/": { status: 402, body: { detail: "x" } },
      }),
      { signedIn: true },
    );
    await act(async () => {
      await session().logout();
    });
    expect(session().status).toBe("signedOut");
    expect(await store.load()).toBeNull();
  });

  it("toque duplo: uma só chamada de saída", async () => {
    const { session, server } = await setup(loggedOut, { signedIn: true });
    await act(async () => {
      await Promise.all([session().logout(), session().logout()]);
    });
    expect(server.callsTo("/mobile/auth/logout/")).toHaveLength(1);
  });

  it("sem sessão ativa não faz nada", async () => {
    const { session, server } = await setup(loggedOut);
    await act(async () => {
      await session().logout();
    });
    expect(server.calls).toHaveLength(0);
  });
});

describe("sessão perdida", () => {
  it("renovação recusada volta para a entrada com aviso e apaga os tokens", async () => {
    const { session, store } = await setup(
      routes({
        "/mobile/me/": { status: 401, body: {} },
        "/mobile/auth/refresh/": {
          status: 401,
          body: { detail: "x", code: "invalid_token" },
        },
      }),
      { signedIn: true },
    );
    await act(async () => {
      await session()
        .api?.get("/mobile/me/")
        .catch(() => undefined);
    });
    expect(session().status).toBe("signedOut");
    expect(session().info).toBeNull();
    expect(session().notice).toBe("expired");
    expect(await store.load()).toBeNull();
  });

  it("falha de rede não derruba a sessão", async () => {
    const { session, store } = await setup(() => networkFailure(), {
      signedIn: true,
    });
    await act(async () => {
      await session()
        .api?.get("/mobile/me/")
        .catch(() => undefined);
    });
    expect(session().status).toBe("active");
    expect(await store.load()).not.toBeNull();
  });
});

describe("aparelhos", () => {
  const device = {
    id: "d1",
    device_label: "iPhone",
    platform: "ios",
    app_version: "1.2.3",
    created_at: "2026-10-01T10:00:00Z",
    last_used_at: "2026-10-02T10:00:00Z",
    is_current: true,
  };

  it("lista, encerra outros e revoga um (404 conta como já encerrado)", async () => {
    const { session, server } = await setup(
      (call) => {
        if (call.path === "/mobile/auth/sessions/")
          return { status: 200, body: [device] };
        if (call.path === "/mobile/auth/sessions/revoke-others/")
          return { status: 200, body: { revoked: 2 } };
        if (call.path === "/mobile/auth/sessions/d2/") return { status: 204 };
        return { status: 404, body: { detail: "x", code: "not_found" } };
      },
      { signedIn: true },
    );
    let list: unknown;
    let others: unknown;
    let revoked: unknown;
    let gone: unknown;
    await act(async () => {
      list = await session().listSessions();
      others = await session().logoutOthers();
      revoked = await session().revokeSession("d2");
      gone = await session().revokeSession("d9");
    });
    expect(list).toEqual([
      {
        id: "d1",
        deviceLabel: "iPhone",
        platform: "ios",
        appVersion: "1.2.3",
        createdAt: "2026-10-01T10:00:00Z",
        lastUsedAt: "2026-10-02T10:00:00Z",
        isCurrent: true,
      },
    ]);
    expect(others).toEqual({ ok: true, revoked: 2 });
    expect(revoked).toEqual({ ok: true });
    expect(gone).toEqual({ ok: true });
    expect(
      server.callsTo("/mobile/auth/sessions/revoke-others/")[0].method,
    ).toBe("POST");
  });

  it("logoutOthers com falha devolve o motivo e mantém a sessão deste aparelho", async () => {
    const { session } = await setup(() => networkFailure(), { signedIn: true });
    let result: unknown;
    await act(async () => {
      result = await session().logoutOthers();
    });
    expect(result).toEqual({ ok: false, reason: "offline" });
    expect(session().status).toBe("active");
  });
});

describe("identificação do aparelho", () => {
  it("iOS: iPhone; Android: modelo informado pelo sistema; web: Web/other", () => {
    const ios = jest.replaceProperty(Platform, "OS", "ios");
    expect(describeDevice()).toMatchObject({
      deviceLabel: "iPhone",
      platform: "ios",
    });
    ios.restore();

    const android = jest.replaceProperty(Platform, "OS", "android");
    const constants = jest
      .spyOn(Platform, "constants", "get")
      .mockReturnValue({ Model: " Pixel   8 " } as never);
    expect(describeDevice()).toMatchObject({
      deviceLabel: "Android Pixel 8",
      platform: "android",
    });
    constants.mockRestore();
    android.restore();

    const web = jest.replaceProperty(Platform, "OS", "web");
    expect(describeDevice()).toMatchObject({
      deviceLabel: "Web",
      platform: "other",
    });
    web.restore();
  });

  it("a versão vem de expo-constants e nunca é undefined", () => {
    expect(typeof describeDevice().appVersion).toBe("string");
  });
});
