import {
  ApiClient,
  createApiClient,
  DEFAULT_TIMEOUT_MS,
} from "../src/api/client";
import { ApiError, isOfflineError, isSessionError } from "../src/api/errors";
import { createMemoryTokenStore, TokenStore } from "../src/api/tokenStore";
import {
  API,
  BASE_URL,
  createFakeServer,
  deferred,
  FakeCall,
  FakeServer,
  hang,
  Handler,
  networkFailure,
  storedSession,
  tokensBody,
} from "./fakeApi";

const REFRESH = "/mobile/auth/refresh/";

interface Setup {
  client: ApiClient;
  server: FakeServer;
  store: TokenStore;
  lost: jest.Mock;
}

async function setup(
  handler: Handler,
  options: { signedIn?: boolean; baseUrl?: string | null } = {},
): Promise<Setup> {
  const server = createFakeServer(handler);
  const store = createMemoryTokenStore();
  const client = createApiClient({
    baseUrl: options.baseUrl === undefined ? BASE_URL : options.baseUrl,
    transport: server.transport,
    tokenStore: store,
  });
  if (options.signedIn !== false) await client.setSession(storedSession(1));
  const lost = jest.fn();
  client.onSessionLost(lost);
  return { client, server, store, lost };
}

async function failure(promise: Promise<unknown>): Promise<ApiError> {
  try {
    await promise;
  } catch (error) {
    expect(error).toBeInstanceOf(ApiError);
    return error as ApiError;
  }
  throw new Error("a chamada deveria ter falhado");
}

/** Resposta padrão: renova com sucesso e aceita só o token de acesso mais novo. */
function rotating(latest: { access: string }): Handler {
  return (call) => {
    if (call.path === REFRESH) {
      latest.access = "aem_access_2";
      return { status: 200, body: tokensBody(2) };
    }
    return call.headers.Authorization === `Bearer ${latest.access}`
      ? { status: 200, body: { ok: true } }
      : { status: 401, body: { detail: "Unauthorized" } };
  };
}

describe("requisição", () => {
  it("monta a URL só a partir da origem validada e envia JSON seguro", async () => {
    const { client, server } = await setup(() => ({
      status: 200,
      body: { ok: true },
    }));
    await client.post("/mobile/checkins/", { a: 1 });
    const [call] = server.calls;
    expect(call.url).toBe(`${API}/mobile/checkins/`);
    expect(call.method).toBe("POST");
    expect(call.headers).toMatchObject({
      Accept: "application/json",
      "Content-Type": "application/json",
      Authorization: "Bearer aem_access_1",
    });
    expect(call.body).toEqual({ a: 1 });
    expect(call.init.credentials).toBe("omit");
    expect(call.init.redirect).toBe("error");
    expect(call.init.signal).toBeDefined();
  });

  it("GET não leva Content-Type nem corpo e a consulta é codificada", async () => {
    const { client, server } = await setup(() => ({ status: 200, body: [] }));
    await client.get("/mobile/routine/", {
      query: { days: 7, nome: "a b&c", vazio: undefined, nulo: null },
    });
    const [call] = server.calls;
    expect(call.url).toBe(`${API}/mobile/routine/?days=7&nome=a%20b%26c`);
    expect(call.headers["Content-Type"]).toBeUndefined();
    expect(call.init.body).toBeUndefined();
  });

  it("rotas públicas (auth: false) não levam o token", async () => {
    const { client, server } = await setup(() => ({ status: 202, body: {} }));
    await client.post(
      "/mobile/auth/password-recovery/",
      { email: "a@b.c" },
      { auth: false },
    );
    expect(server.calls[0].headers.Authorization).toBeUndefined();
  });

  it("recusa caminhos fora do formato antes de abrir a rede", async () => {
    const { client, server } = await setup(() => ({ status: 200, body: {} }));
    for (const path of [
      "https://evil.example/x/",
      "//evil.example/x/",
      "/mobile/me", // sem a barra final
      "/mobile/../x/",
      "/mobile/me/?a=1",
      "mobile/me/",
      "/mobile/%2e%2e/x/",
      "",
    ]) {
      const error = await failure(client.get(path));
      expect(error.code).toBe("invalid_request");
    }
    expect(server.calls).toHaveLength(0);
  });

  it("sem endereço válido não há requisição nem token enviado", async () => {
    const { client, server } = await setup(() => ({ status: 200, body: {} }), {
      baseUrl: null,
    });
    expect(client.configured).toBe(false);
    const error = await failure(client.get("/mobile/me/"));
    expect(error.code).toBe("configuration");
    expect(server.calls).toHaveLength(0);
  });

  it("http só vale em desenvolvimento e só em localhost", async () => {
    const server = createFakeServer(() => ({ status: 200, body: {} }));
    const prod = createApiClient({
      baseUrl: "http://localhost:8000",
      transport: server.transport,
      dev: false,
    });
    expect(prod.configured).toBe(false);
    const dev = createApiClient({
      baseUrl: "http://localhost:8000",
      transport: server.transport,
      dev: true,
    });
    expect(dev.configured).toBe(true);
    await dev.get("/mobile/help/", { auth: false });
    expect(server.calls[0].url).toBe(
      "http://localhost:8000/api/v1/mobile/help/",
    );
  });

  it("204 devolve undefined e o corpo é validado por parse", async () => {
    let reply: any = { status: 204 };
    const { client } = await setup(() => reply);
    await expect(
      client.delete("/mobile/habits/h1/checks/2026-10-01/"),
    ).resolves.toBeUndefined();
    reply = { status: 200, body: { n: "texto" } };
    const error = await failure(
      client.get("/mobile/me/", {
        parse: (value) => {
          if (typeof (value as any).n !== "number") throw new TypeError("x");
          return value;
        },
      }),
    );
    expect(error.code).toBe("malformed_response");
  });
});

describe("renovação de tokens", () => {
  it("401 renova o par uma vez e repete a requisição original com o token novo", async () => {
    const latest = { access: "" };
    const { client, server, store } = await setup(rotating(latest));
    await expect(client.get("/mobile/me/")).resolves.toEqual({ ok: true });
    expect(server.calls.map((call) => call.path)).toEqual([
      "/mobile/me/",
      REFRESH,
      "/mobile/me/",
    ]);
    expect(server.calls[0].headers.Authorization).toBe("Bearer aem_access_1");
    expect(server.calls[2].headers.Authorization).toBe("Bearer aem_access_2");
    // A renovação não leva Authorization: só o token de renovação, no corpo.
    expect(server.calls[1].headers.Authorization).toBeUndefined();
    expect(server.calls[1].body).toEqual({ refresh_token: "aer_refresh_1" });
    expect((await store.load())?.refreshToken).toBe("aer_refresh_2");
  });

  it("chamadas simultâneas aguardam a MESMA renovação (single-flight)", async () => {
    const latest = { access: "" };
    const gate = deferred();
    const inner = rotating(latest);
    const { client, server } = await setup(async (call) => {
      if (call.path === REFRESH) await gate.promise; // segura a renovação
      return inner(call);
    });
    const results = Promise.all([
      client.get("/mobile/me/"),
      client.get("/mobile/diary/"),
      client.get("/mobile/goals/"),
      client.get("/mobile/appointments/"),
    ]);
    // Deixa todas receberem o 401 antes de a renovação terminar.
    await jest.advanceTimersByTimeAsync(0);
    gate.resolve();
    await expect(results).resolves.toHaveLength(4);
    expect(server.callsTo(REFRESH)).toHaveLength(1);
    // Cada uma repetiu exatamente uma vez.
    for (const path of [
      "/mobile/me/",
      "/mobile/diary/",
      "/mobile/goals/",
      "/mobile/appointments/",
    ]) {
      expect(server.callsTo(path)).toHaveLength(2);
    }
  });

  it("uma chamada que recebe 401 depois que outra já renovou só repete", async () => {
    const latest = { access: "aem_access_1" };
    const lateReply = deferred<void>();
    const { client, server } = await setup(async (call) => {
      if (call.path === "/mobile/slow/") {
        await lateReply.promise; // o 401 desta chega depois da renovação
        return { status: 401, body: {} };
      }
      return rotating(latest)(call);
    });
    const slow = client.get("/mobile/slow/").catch(() => undefined);
    await jest.advanceTimersByTimeAsync(0);
    await client.get("/mobile/me/"); // renova (1 vez)
    lateReply.resolve();
    await slow;
    expect(server.callsTo(REFRESH)).toHaveLength(1);
  });

  it("repete a original UMA vez: novo 401 depois de renovar encerra a sessão", async () => {
    const { client, server, store, lost } = await setup((call) =>
      call.path === REFRESH
        ? { status: 200, body: tokensBody(2) }
        : { status: 401, body: { detail: "Unauthorized" } },
    );
    const error = await failure(client.get("/mobile/me/"));
    expect(error.code).toBe("session_lost");
    expect(isSessionError(error)).toBe(true);
    expect(server.callsTo("/mobile/me/")).toHaveLength(2);
    expect(server.callsTo(REFRESH)).toHaveLength(1);
    expect(await store.load()).toBeNull();
    expect(client.currentSession()).toBeNull();
    expect(lost).toHaveBeenCalledTimes(1);
  });

  it.each([401, 403])(
    "renovação recusada (%s) = sessão perdida: limpa os tokens e avisa uma vez",
    async (status) => {
      const { client, server, store, lost } = await setup((call) =>
        call.path === REFRESH
          ? { status, body: { detail: "x", code: "invalid_token" } }
          : { status: 401, body: {} },
      );
      const results = await Promise.all([
        failure(client.get("/mobile/me/")),
        failure(client.get("/mobile/diary/")),
      ]);
      expect(results.map((error) => error.code)).toEqual([
        "session_lost",
        "session_lost",
      ]);
      expect(server.callsTo(REFRESH)).toHaveLength(1);
      expect(await store.load()).toBeNull();
      expect(lost).toHaveBeenCalledTimes(1);
      // Sem sessão, nada mais sai com Authorization.
      const again = await failure(client.get("/mobile/me/"));
      expect(again.code).toBe("session_lost");
      // A chamada seguinte nem chega ao servidor: não há mais token.
      expect(server.callsTo("/mobile/me/")).toHaveLength(1);
    },
  );

  it("sem token na memória a sessão é perdida sem ir ao servidor", async () => {
    const { client, server, lost } = await setup(
      () => ({ status: 200, body: {} }),
      { signedIn: false },
    );
    const error = await failure(client.get("/mobile/me/"));
    expect(error.code).toBe("session_lost");
    expect(server.calls).toHaveLength(0);
    expect(lost).toHaveBeenCalledTimes(1);
  });

  it("erro de rede ou tempo esgotado na renovação NÃO derruba a sessão", async () => {
    let failRefresh = true;
    const latest = { access: "" };
    const inner = rotating(latest);
    const { client, store, lost } = await setup((call) => {
      if (call.path === REFRESH && failRefresh) return networkFailure();
      return inner(call);
    });
    const offline = await failure(client.get("/mobile/me/"));
    expect(isOfflineError(offline)).toBe(true);
    expect(isSessionError(offline)).toBe(false);
    expect(lost).not.toHaveBeenCalled();
    expect((await store.load())?.refreshToken).toBe("aer_refresh_1");
    // A rede volta: a mesma sessão renova e segue.
    failRefresh = false;
    await expect(client.get("/mobile/me/")).resolves.toEqual({ ok: true });
  });

  it("falha de servidor (5xx) na renovação também preserva a sessão", async () => {
    const { client, store, lost } = await setup((call) =>
      call.path === REFRESH
        ? { status: 503, body: { detail: "x" } }
        : { status: 401, body: {} },
    );
    const error = await failure(client.get("/mobile/me/"));
    expect(error.code).toBe("server_error");
    expect(lost).not.toHaveBeenCalled();
    expect(await store.load()).not.toBeNull();
  });

  it("sair durante a renovação não ressuscita a sessão", async () => {
    const gate = deferred();
    const { client, store, lost } = await setup(async (call) => {
      if (call.path === REFRESH) {
        await gate.promise;
        return { status: 200, body: tokensBody(2) };
      }
      return { status: 401, body: {} };
    });
    const pending = failure(client.get("/mobile/me/"));
    await jest.advanceTimersByTimeAsync(0);
    await client.clearSession(); // o paciente saiu enquanto renovava
    gate.resolve();
    const error = await pending;
    expect(error.code).toBe("session_changed");
    expect(isSessionError(error)).toBe(true);
    expect(await store.load()).toBeNull();
    expect(client.currentSession()).toBeNull();
    expect(lost).not.toHaveBeenCalled(); // saída voluntária não é "perdida"
  });

  it("falha ao gravar no cofre não impede a sessão de seguir na memória", async () => {
    const broken: TokenStore = {
      load: async () => null,
      save: async () => {
        throw new Error("cofre indisponível");
      },
      clear: async () => undefined,
    };
    const server = createFakeServer(() => ({ status: 200, body: { ok: 1 } }));
    const client = createApiClient({
      baseUrl: BASE_URL,
      transport: server.transport,
      tokenStore: broken,
    });
    await client.setSession(storedSession(1));
    await expect(client.get("/mobile/me/")).resolves.toEqual({ ok: 1 });
  });

  it("restaura do cofre; renovação vencida conta como sem sessão e é apagada", async () => {
    const { client, store } = await setup(() => ({ status: 200, body: {} }), {
      signedIn: false,
    });
    expect(await client.restore()).toBeNull();
    await store.save(storedSession(3));
    expect(await client.restore()).toEqual({
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
    await store.save({
      ...storedSession(3),
      refreshExpiresAt: "2000-01-01T00:00:00Z",
    });
    expect(await client.restore()).toBeNull();
    expect(await store.load()).toBeNull();
  });
});

describe("erros", () => {
  it("rede e tempo esgotado viram códigos próprios, sem derrubar a sessão", async () => {
    let mode: "network" | "hang" = "network";
    const { client, store, lost } = await setup((call) =>
      mode === "network" ? networkFailure() : hang(call),
    );
    const offline = await failure(client.get("/mobile/me/"));
    expect(offline.code).toBe("network");
    expect(offline.status).toBe(0);

    mode = "hang";
    const pending = failure(client.get("/mobile/me/"));
    await jest.advanceTimersByTimeAsync(DEFAULT_TIMEOUT_MS - 1);
    await jest.advanceTimersByTimeAsync(1);
    const timeout = await pending;
    expect(timeout.code).toBe("timeout");
    expect(isOfflineError(timeout)).toBe(true);
    expect(lost).not.toHaveBeenCalled();
    expect(await store.load()).not.toBeNull();
  });

  it("aborta a requisição ao estourar o tempo", async () => {
    const { client, server } = await setup((call) => hang(call));
    const pending = failure(client.get("/mobile/me/", { timeoutMs: 1000 }));
    await jest.advanceTimersByTimeAsync(1000);
    await pending;
    expect(server.calls[0].init.signal?.aborted).toBe(true);
  });

  it("402 vira clinic_blocked (sem renovar nem encerrar a sessão)", async () => {
    const { client, server, lost } = await setup(() => ({
      status: 402,
      body: { detail: "Acesso suspenso pela clínica." },
    }));
    const error = await failure(client.get("/mobile/me/"));
    expect(error).toMatchObject({ status: 402, code: "clinic_blocked" });
    expect(server.callsTo(REFRESH)).toHaveLength(0);
    expect(lost).not.toHaveBeenCalled();
  });

  it("429 vira rate_limited e 5xx vira server_error", async () => {
    let status = 429;
    const { client } = await setup(() => ({
      status,
      body: { detail: "x", code: "rate_limited" },
    }));
    expect((await failure(client.get("/mobile/me/"))).code).toBe(
      "rate_limited",
    );
    status = 502;
    expect((await failure(client.get("/mobile/me/"))).code).toBe(
      "server_error",
    );
  });

  it("409 clinic_choice_required traz a lista de clínicas", async () => {
    const { client } = await setup(() => ({
      status: 409,
      body: {
        detail: "Escolha a clínica para continuar.",
        code: "clinic_choice_required",
        clinics: [
          { id: "c1", name: "Clínica Norte" },
          { id: "c2", name: "Clínica Sul" },
        ],
      },
    }));
    const error = await failure(
      client.post("/mobile/auth/login/", {}, { auth: false }),
    );
    expect(error.status).toBe(409);
    expect(error.code).toBe("clinic_choice_required");
    expect(error.clinics).toEqual([
      { id: "c1", name: "Clínica Norte" },
      { id: "c2", name: "Clínica Sul" },
    ]);
  });

  it("422 de senha carrega errors[]; o código vem do corpo", async () => {
    const { client } = await setup(() => ({
      status: 422,
      body: {
        detail: "Senha não aceita.",
        code: "weak_password",
        errors: ["Esta senha é muito curta.", "Esta senha é muito comum.", 7],
      },
    }));
    const error = await failure(
      client.post("/mobile/auth/activate/", {}, { auth: false }),
    );
    expect(error.status).toBe(422);
    expect(error.code).toBe("weak_password");
    expect(error.errors).toEqual([
      "Esta senha é muito curta.",
      "Esta senha é muito comum.",
    ]);
  });

  it("4xx usa o code do corpo; sem code cai em http_<status>", async () => {
    let body: unknown = { detail: "Sessão não encontrada.", code: "not_found" };
    const { client } = await setup(() => ({ status: 404, body }));
    expect((await failure(client.get("/mobile/me/"))).code).toBe("not_found");
    body = { detail: "texto" };
    expect((await failure(client.get("/mobile/me/"))).code).toBe("http_404");
    body = { detail: "x", code: "Código Inválido!" }; // fora do formato: ignorado
    expect((await failure(client.get("/mobile/me/"))).code).toBe("http_404");
  });

  it("a mensagem do erro nunca carrega token, corpo nem URL", async () => {
    const { client } = await setup(() => ({
      status: 400,
      body: { detail: "SEGREDO do corpo", code: "rejected" },
    }));
    const error = await failure(
      client.post("/mobile/diary/", { texto: "diário privado" }),
    );
    for (const text of [error.message, String(error), JSON.stringify(error)]) {
      expect(text).not.toMatch(/aem_|aer_|SEGREDO|diário|api\.clinica|http/);
    }
    expect(error.detail).toBe("SEGREDO do corpo"); // só diagnóstico, nunca exibido
  });

  it("não escreve nada em console (nem token, nem corpo, nem URL)", async () => {
    const spies = (["log", "info", "warn", "error", "debug"] as const).map(
      (method) => jest.spyOn(console, method).mockImplementation(() => {}),
    );
    const latest = { access: "" };
    const { client } = await setup(rotating(latest));
    await client.get("/mobile/me/");
    await failure(client.get("/mobile/me/", { parse: () => networkFailure() }));
    for (const spy of spies) {
      expect(spy).not.toHaveBeenCalled();
      spy.mockRestore();
    }
  });
});

describe("resposta", () => {
  it("redirecionamento: descarta a resposta sem ler o corpo", async () => {
    const { client, server } = await setup(() => ({
      status: 200,
      body: { vazou: true },
      url: "https://outro.example/api/v1/mobile/me/",
    }));
    const error = await failure(client.get("/mobile/me/"));
    expect(error.code).toBe("malformed_response");
    expect(server.jsonReads()).toBe(0);
  });

  it("a URL da resposta pode diferir só na consulta (reescrita pelo sistema)", async () => {
    const { client } = await setup((call) => ({
      status: 200,
      body: { ok: true },
      url: call.url.replace("days=7", "days=%377"),
    }));
    await expect(
      client.get("/mobile/routine/", { query: { days: 7 } }),
    ).resolves.toEqual({ ok: true });
  });

  it("exige application/json (inclusive com charset)", async () => {
    let contentType: string | null = "text/html";
    const { client } = await setup(() => ({
      status: 200,
      body: { ok: true },
      contentType,
    }));
    expect((await failure(client.get("/mobile/me/"))).code).toBe(
      "malformed_response",
    );
    contentType = null;
    expect((await failure(client.get("/mobile/me/"))).code).toBe(
      "malformed_response",
    );
    contentType = "application/json; charset=utf-8";
    await expect(client.get("/mobile/me/")).resolves.toEqual({ ok: true });
  });

  it("erro com corpo não JSON ainda vira ApiError pelo status", async () => {
    const { client } = await setup(() => ({
      status: 500,
      body: "<html>",
      contentType: "text/html",
    }));
    const error = await failure(client.get("/mobile/me/"));
    expect(error).toMatchObject({ status: 500, code: "server_error" });
    expect(error.detail).toBeUndefined();
  });

  it("corpo JSON ilegível em 200 é resposta malformada", async () => {
    const { client } = await setup(() => ({ status: 200, unreadable: true }));
    expect((await failure(client.get("/mobile/me/"))).code).toBe(
      "malformed_response",
    );
  });
});

describe("autorização só no servidor configurado", () => {
  it("toda chamada com Authorization vai para a origem configurada", async () => {
    const latest = { access: "" };
    const { client, server } = await setup(rotating(latest));
    await client.get("/mobile/me/");
    await client.put("/mobile/low-energy/", { active: true });
    await client.delete("/mobile/habits/h-1/checks/2026-10-01/");
    const withToken = server.calls.filter((call: FakeCall) =>
      Boolean(call.headers.Authorization),
    );
    expect(withToken.length).toBeGreaterThan(0);
    for (const call of server.calls) {
      expect(call.url.startsWith(`${BASE_URL}/api/v1/`)).toBe(true);
    }
  });
});
