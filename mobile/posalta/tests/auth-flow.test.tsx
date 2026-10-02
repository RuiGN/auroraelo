import { fireEvent, screen, within } from "@testing-library/react-native";
import * as SecureStore from "expo-secure-store";
import { Linking } from "react-native";
import { createMemoryTokenStore } from "../src/api/tokenStore";
import {
  createFakeServer,
  FakeServer,
  Handler,
  hang,
  meBody,
  networkFailure,
  storedSession,
  tokensBody,
} from "./fakeApi";
import { Options, renderApp, settle } from "./helpers";

/** `toHaveTextContent` com texto exato é rígido: aqui basta conter o trecho. */
const has = (text: string) =>
  new RegExp(text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"));

const LOGIN = "/mobile/auth/login/";
const ACTIVATE = "/mobile/auth/activate/";
const RECOVERY = "/mobile/auth/password-recovery/";
const RESET = "/mobile/auth/password-reset/";
const LOGOUT = "/mobile/auth/logout/";
const OTHERS = "/mobile/auth/sessions/revoke-others/";

/** Servidor feliz por padrão; cada teste sobrescreve só a rota que importa. */
function server(overrides: Record<string, Handler> = {}): FakeServer {
  return createFakeServer((call) => {
    const custom = overrides[call.path];
    if (custom) return custom(call);
    switch (call.path) {
      case LOGIN:
      case ACTIVATE:
        return { status: 200, body: tokensBody(1) };
      case "/mobile/me/":
        return { status: 200, body: meBody() };
      case RECOVERY:
        return { status: 202, body: { detail: "ok" } };
      case RESET:
      case LOGOUT:
        return { status: 204 };
      case OTHERS:
        return { status: 200, body: { revoked: 2 } };
      default:
        return { status: 404, body: { detail: "x", code: "not_found" } };
    }
  });
}

async function openApp(options: Options = {}) {
  const utils = renderApp({ mode: "live", ...options });
  await settle();
  return utils;
}

function type(testID: string, value: string) {
  fireEvent.changeText(screen.getByTestId(testID), value);
}

async function press(testID: string) {
  fireEvent.press(screen.getByTestId(testID));
  await settle();
}

async function signIn(email = "alex@example.com", password = "senha-segura") {
  type("auth-email", email);
  type("auth-password", password);
  await press("auth-submit");
}

describe("live sem endereço do servidor", () => {
  it("mostra a tela de configuração ausente, sem dados nem erro", async () => {
    await openApp();
    expect(screen.getByTestId("screen-config-missing")).toBeTruthy();
    expect(screen.getByText("Aplicativo sem configuração")).toBeTruthy();
    expect(screen.getByTestId("config-missing")).toHaveTextContent(
      /não sabe com qual servidor falar/,
    );
    expect(screen.queryByTestId("screen-home")).toBeNull();
    expect(screen.queryByTestId("auth-email")).toBeNull();
    expect(screen.queryByTestId("demo-banner")).toBeNull();
  });

  it("a Ajuda urgente abre, funciona e fecha de volta para a configuração", async () => {
    const openURL = jest.spyOn(Linking, "openURL").mockResolvedValue(true);
    await openApp();
    await press("auth-help");
    expect(screen.getByTestId("screen-urgent-help")).toBeTruthy();
    fireEvent.press(screen.getByTestId("call-192"));
    expect(openURL).toHaveBeenCalledWith("tel:192");
    await press("help-close");
    expect(screen.getByTestId("screen-config-missing")).toBeTruthy();
    openURL.mockRestore();
  });
});

describe("abrindo a conta", () => {
  it("mostra 'abrindo' enquanto lê o cofre e depois a entrada", async () => {
    renderApp({ mode: "live", transport: server().transport });
    expect(screen.getByTestId("screen-restoring")).toBeTruthy();
    expect(screen.getByTestId("auth-help")).toBeTruthy(); // ajuda até aqui
    await settle();
    expect(screen.getByTestId("screen-signin")).toBeTruthy();
    expect(screen.queryByTestId("screen-restoring")).toBeNull();
  });

  it("com sessão guardada vai direto para o app e carrega os dados", async () => {
    const fake = server();
    await openApp({ transport: fake.transport, signedIn: true });
    expect(screen.getByTestId("screen-home")).toBeTruthy();
    expect(screen.queryByTestId("screen-signin")).toBeNull();
    expect(fake.callsTo("/mobile/me/")).toHaveLength(1);
    expect(await screen.findByText("Bom dia, Alex")).toBeTruthy();
    // Dado real: nada de faixa de demonstração e nada de domínio inventado.
    expect(screen.queryByTestId("demo-banner")).toBeNull();
    expect(screen.queryByText(/Alex Exemplo/)).toBeNull();
  });
});

describe("entrar", () => {
  it("tem campos acessíveis e preenchimento automático corretos", async () => {
    await openApp({ transport: server().transport });
    const email = screen.getByTestId("auth-email");
    const password = screen.getByTestId("auth-password");
    expect(email.props.accessibilityLabel).toBe("E-mail");
    expect(email.props).toMatchObject({
      textContentType: "username",
      autoComplete: "username",
      keyboardType: "email-address",
      autoCapitalize: "none",
      autoCorrect: false,
    });
    expect(password.props.accessibilityLabel).toBe("Senha");
    expect(password.props).toMatchObject({
      textContentType: "password",
      autoComplete: "current-password",
      autoCapitalize: "none",
      autoCorrect: false,
      spellCheck: false,
      secureTextEntry: true,
    });
  });

  it("mostrar/ocultar a senha alterna o campo e o rótulo do botão", async () => {
    await openApp({ transport: server().transport });
    const toggle = () => screen.getByTestId("auth-password-toggle");
    expect(toggle().props.accessibilityLabel).toBe("Mostrar senha");
    fireEvent.press(toggle());
    expect(screen.getByTestId("auth-password").props.secureTextEntry).toBe(
      false,
    );
    expect(toggle().props.accessibilityLabel).toBe("Ocultar senha");
    fireEvent.press(toggle());
    expect(screen.getByTestId("auth-password").props.secureTextEntry).toBe(
      true,
    );
  });

  it("só habilita o envio com e-mail e senha", async () => {
    await openApp({ transport: server().transport });
    expect(screen.getByTestId("auth-submit")).toBeDisabled();
    type("auth-email", "alex@example.com");
    expect(screen.getByTestId("auth-submit")).toBeDisabled();
    type("auth-password", "x");
    expect(screen.getByTestId("auth-submit")).toBeEnabled();
  });

  it("entra, mostra as abas e guarda os tokens só no cofre", async () => {
    const fake = server();
    const store = createMemoryTokenStore();
    await openApp({ transport: fake.transport, tokenStore: store });
    await signIn();
    expect(screen.getByTestId("screen-home")).toBeTruthy();
    expect(screen.queryByTestId("screen-signin")).toBeNull();
    expect(fake.callsTo(LOGIN)[0].body).toMatchObject({
      email: "alex@example.com",
      password: "senha-segura",
      platform: "ios",
    });
    expect((await store.load())?.accessToken).toBe("aem_access_1");
    expect(await screen.findByText("Bom dia, Alex")).toBeTruthy();
    // A senha não ficou em nenhum texto da tela.
    expect(JSON.stringify(screen.toJSON())).not.toContain("senha-segura");
  });

  it("credenciais inválidas: mensagem acolhedora e continua na entrada", async () => {
    await openApp({
      transport: server({
        [LOGIN]: () => ({
          status: 401,
          body: {
            detail: "E-mail ou senha inválidos.",
            code: "invalid_credentials",
          },
        }),
      }).transport,
    });
    await signIn();
    expect(screen.getByTestId("auth-error")).toHaveTextContent(
      has("E-mail ou senha não conferem"),
    );
    expect(screen.getByTestId("screen-signin")).toBeTruthy();
    // O texto do servidor (detail) nunca aparece.
    expect(screen.queryByText(/E-mail ou senha inválidos\./)).toBeNull();
  });

  it.each([
    {
      name: "muitas tentativas (429)",
      reply: () => ({
        status: 429,
        body: { detail: "x", code: "rate_limited" },
      }),
      text: "Muitas tentativas",
    },
    {
      name: "sem rede",
      reply: () => networkFailure(),
      text: "Sem conexão com o servidor",
    },
    {
      name: "clínica bloqueada (402)",
      reply: () => ({ status: 402, body: { detail: "x" } }),
      text: "temporariamente suspenso pela clínica",
    },
    {
      name: "erro do servidor",
      reply: () => ({ status: 500, body: { detail: "x" } }),
      text: "Não foi possível concluir",
    },
  ])("falha: $name", async ({ reply, text }) => {
    await openApp({ transport: server({ [LOGIN]: reply }).transport });
    await signIn();
    expect(screen.getByTestId("auth-error")).toHaveTextContent(has(text));
  });

  it("mais de uma clínica: pede a escolha e reenvia com clinic_id", async () => {
    const clinics = [
      { id: "c1", name: "Clínica Norte" },
      { id: "c2", name: "Clínica Sul" },
    ];
    const fake = server({
      [LOGIN]: (call) =>
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
    });
    await openApp({ transport: fake.transport });
    await signIn();
    expect(screen.getByTestId("auth-clinic-choice")).toBeTruthy();
    expect(screen.queryByTestId("auth-error")).toBeNull();
    expect(screen.getByTestId("auth-submit")).toBeDisabled(); // falta escolher
    fireEvent.press(screen.getByText("Clínica Sul"));
    expect(screen.getByTestId("auth-submit")).toBeEnabled();
    await press("auth-submit");
    expect(fake.callsTo(LOGIN)[1].body.clinic_id).toBe("c2");
    expect(screen.getByTestId("screen-home")).toBeTruthy();
  });

  it("trocar o e-mail depois da escolha descarta a lista de clínicas", async () => {
    const fake = server({
      [LOGIN]: () => ({
        status: 409,
        body: {
          detail: "x",
          code: "clinic_choice_required",
          clinics: [
            { id: "c1", name: "Clínica Norte" },
            { id: "c2", name: "Clínica Sul" },
          ],
        },
      }),
    });
    await openApp({ transport: fake.transport });
    await signIn();
    expect(screen.getByTestId("auth-clinic-choice")).toBeTruthy();
    type("auth-email", "outra@example.com");
    expect(screen.queryByTestId("auth-clinic-choice")).toBeNull();
  });

  it("toque duplo em Entrar envia uma só requisição", async () => {
    const fake = server();
    await openApp({ transport: fake.transport });
    type("auth-email", "alex@example.com");
    type("auth-password", "senha-segura");
    fireEvent.press(screen.getByTestId("auth-submit"));
    fireEvent.press(screen.getByTestId("auth-submit"));
    await settle();
    expect(fake.callsTo(LOGIN)).toHaveLength(1);
  });
});

describe("Ajuda urgente em todas as telas de entrada", () => {
  it("há acesso visível (cabeçalho e corpo) em entrar, ativar, recuperar e redefinir", async () => {
    await openApp({ transport: server().transport });
    const expectHelp = (id: string) => {
      const current = screen.getByTestId(id);
      expect(within(current).getByTestId("auth-help")).toBeTruthy();
      expect(screen.getByTestId("header-help")).toBeTruthy();
      expect(screen.queryByTestId("header-profile")).toBeNull();
    };
    expectHelp("screen-signin");
    await press("auth-forgot");
    expectHelp("screen-recover");
    await press("auth-have-reset-code");
    expectHelp("screen-reset");
    await press("auth-back"); // volta à tela de entrada original
    expectHelp("screen-signin");
    await press("auth-have-code");
    expectHelp("screen-activate");
  });

  it("a Ajuda urgente abre sem sessão e sem rede, com os números de emergência", async () => {
    const openURL = jest.spyOn(Linking, "openURL").mockResolvedValue(true);
    const fake = createFakeServer((call) => hang(call));
    await openApp({ transport: fake.transport });
    await press("auth-help");
    expect(screen.getByTestId("screen-urgent-help")).toBeTruthy();
    for (const number of ["192", "188", "193", "190"]) {
      expect(screen.getByTestId(`call-${number}`)).toBeTruthy();
    }
    fireEvent.press(screen.getByTestId("call-188"));
    expect(openURL).toHaveBeenCalledWith("tel:188");
    expect(screen.queryByTestId("urgent-plan")).toBeNull(); // nada da clínica
    await press("help-close");
    expect(screen.getByTestId("screen-signin")).toBeTruthy();
    openURL.mockRestore();
  });
});

describe("ativar conta", () => {
  async function openActivate(fake: FakeServer) {
    await openApp({ transport: fake.transport });
    await press("auth-have-code");
    expect(screen.getByTestId("screen-activate")).toBeTruthy();
  }

  it("campos com as dicas certas para o gerenciador de senhas", async () => {
    await openActivate(server());
    expect(screen.getByTestId("auth-code").props).toMatchObject({
      textContentType: "oneTimeCode",
      autoComplete: "one-time-code",
      autoCapitalize: "none",
      autoCorrect: false,
    });
    expect(screen.getByTestId("auth-password").props).toMatchObject({
      textContentType: "newPassword",
      autoComplete: "new-password",
      secureTextEntry: true,
      autoCorrect: false,
    });
    expect(screen.getByTestId("auth-first-name").props.textContentType).toBe(
      "givenName",
    );
    expect(screen.getByTestId("auth-last-name").props.textContentType).toBe(
      "familyName",
    );
  });

  it("ativa com código, nome e senha e já entra no app", async () => {
    const fake = server();
    await openActivate(fake);
    type("auth-code", "convite-abc");
    type("auth-first-name", "Alex");
    type("auth-last-name", "Paciente");
    type("auth-password", "uma senha bem longa");
    await press("auth-submit");
    expect(fake.callsTo(ACTIVATE)[0].body).toMatchObject({
      code: "convite-abc",
      first_name: "Alex",
      last_name: "Paciente",
      password: "uma senha bem longa",
    });
    expect(screen.getByTestId("screen-home")).toBeTruthy();
  });

  it("senha recusada mostra a lista de erros do servidor", async () => {
    await openActivate(
      server({
        [ACTIVATE]: () => ({
          status: 422,
          body: {
            detail: "Senha não aceita.",
            code: "weak_password",
            errors: ["Esta senha é muito curta.", "Esta senha é muito comum."],
          },
        }),
      }),
    );
    type("auth-code", "c");
    type("auth-password", "123");
    await press("auth-submit");
    const error = screen.getByTestId("auth-error");
    expect(error).toHaveTextContent(has("Esta senha não foi aceita"));
    expect(error).toHaveTextContent(has("Esta senha é muito curta."));
    expect(error).toHaveTextContent(has("Esta senha é muito comum."));
    expect(screen.getByTestId("screen-activate")).toBeTruthy();
  });

  it("código inválido ou expirado tem mensagem própria", async () => {
    await openActivate(
      server({
        [ACTIVATE]: () => ({
          status: 422,
          body: { detail: "x", code: "invalid_code", errors: [] },
        }),
      }),
    );
    type("auth-code", "velho");
    type("auth-password", "uma senha bem longa");
    await press("auth-submit");
    expect(screen.getByTestId("auth-error")).toHaveTextContent(
      has("não é válido ou já expirou"),
    );
  });

  it("senha atual errada de quem já tem conta não culpa o código", async () => {
    await openActivate(
      server({
        [ACTIVATE]: () => ({
          status: 401,
          body: { detail: "x", code: "invalid_credentials" },
        }),
      }),
    );
    type("auth-code", "c");
    type("auth-password", "errada");
    await press("auth-submit");
    expect(screen.getByTestId("auth-error")).toHaveTextContent(
      has("A senha não conferiu"),
    );
  });
});

describe("recuperar e redefinir a senha", () => {
  it("recuperar: resposta neutra, sem dizer se o e-mail existe", async () => {
    const fake = server();
    await openApp({ transport: fake.transport });
    await press("auth-forgot");
    expect(screen.getByTestId("screen-recover")).toBeTruthy();
    type("auth-email", "qualquer@example.com");
    await press("auth-submit");
    expect(screen.getByTestId("auth-recover-sent")).toHaveTextContent(
      has("Se este e-mail estiver cadastrado"),
    );
    expect(fake.callsTo(RECOVERY)[0].body).toEqual({
      email: "qualquer@example.com",
    });
  });

  it("recuperar: limite de tentativas e falta de rede têm aviso", async () => {
    let reply: Handler = () => ({
      status: 429,
      body: { detail: "x", code: "rate_limited" },
    });
    await openApp({
      transport: server({ [RECOVERY]: (call) => reply(call) }).transport,
    });
    await press("auth-forgot");
    type("auth-email", "a@b.c");
    await press("auth-submit");
    expect(screen.getByTestId("auth-error")).toHaveTextContent(
      has("Muitas tentativas"),
    );
    expect(screen.queryByTestId("auth-recover-sent")).toBeNull();
    reply = () => networkFailure();
    await press("auth-submit");
    expect(screen.getByTestId("auth-error")).toHaveTextContent(
      has("Sem conexão"),
    );
  });

  it("redefinir: troca a senha, volta à entrada e avisa", async () => {
    const fake = server();
    await openApp({ transport: fake.transport });
    await press("auth-forgot");
    await press("auth-have-reset-code");
    expect(screen.getByTestId("screen-reset")).toBeTruthy();
    expect(screen.getByTestId("auth-new-password").props).toMatchObject({
      textContentType: "newPassword",
      autoComplete: "new-password",
      secureTextEntry: true,
    });
    type("auth-code", "MQ.abc-123");
    type("auth-new-password", "outra senha longa");
    await press("auth-submit");
    expect(fake.callsTo(RESET)[0].body).toEqual({
      code: "MQ.abc-123",
      new_password: "outra senha longa",
    });
    expect(screen.getByTestId("screen-signin")).toBeTruthy();
    expect(screen.getByTestId("auth-notice")).toHaveTextContent(
      has("Senha alterada"),
    );
    expect(screen.queryByTestId("screen-home")).toBeNull();
  });

  it("redefinir: código inválido não troca nada", async () => {
    await openApp({
      transport: server({
        [RESET]: () => ({
          status: 400,
          body: { detail: "x", code: "invalid_code" },
        }),
      }).transport,
    });
    await press("auth-forgot");
    await press("auth-have-reset-code");
    type("auth-code", "velho");
    type("auth-new-password", "outra senha longa");
    await press("auth-submit");
    expect(screen.getByTestId("auth-error")).toHaveTextContent(
      has("não é válido ou já expirou"),
    );
    expect(screen.getByTestId("screen-reset")).toBeTruthy();
  });
});

describe("links do app (e-mail)", () => {
  it("convite: abre a ativação com o código preenchido e editável", async () => {
    jest
      .spyOn(Linking, "getInitialURL")
      .mockResolvedValue("auroraelo-posalta://activate?code=convite-xyz");
    await openApp({ transport: server().transport });
    expect(screen.getByTestId("screen-activate")).toBeTruthy();
    const code = screen.getByTestId("auth-code");
    expect(code.props.value).toBe("convite-xyz");
    expect(code.props.editable).not.toBe(false);
    expect(
      screen.getByText(/Preenchemos o código a partir do link/),
    ).toBeTruthy();
    fireEvent.changeText(code, "corrigido");
    expect(screen.getByTestId("auth-code").props.value).toBe("corrigido");
    expect(screen.queryByText(/Preenchemos o código/)).toBeNull();
  });

  it("recuperação: abre a redefinição com o código preenchido", async () => {
    jest
      .spyOn(Linking, "getInitialURL")
      .mockResolvedValue("auroraelo-posalta://reset?code=MQ.token-1");
    await openApp({ transport: server().transport });
    expect(screen.getByTestId("screen-reset")).toBeTruthy();
    expect(screen.getByTestId("auth-code").props.value).toBe("MQ.token-1");
  });

  it("link desconhecido é ignorado: continua na entrada", async () => {
    jest
      .spyOn(Linking, "getInitialURL")
      .mockResolvedValue("auroraelo-posalta://settings?code=abc");
    await openApp({ transport: server().transport });
    expect(screen.getByTestId("screen-signin")).toBeTruthy();
    expect(screen.queryByTestId("screen-activate")).toBeNull();
  });

  it("o código não vai para parâmetros de navegação nem para o log", async () => {
    const spies = (["log", "info", "warn", "error", "debug"] as const).map(
      (method) => jest.spyOn(console, method).mockImplementation(() => {}),
    );
    jest
      .spyOn(Linking, "getInitialURL")
      .mockResolvedValue("auroraelo-posalta://activate?code=SEGREDO-123");
    await openApp({ transport: server().transport });
    for (const spy of spies) {
      for (const call of spy.mock.calls) {
        expect(JSON.stringify(call)).not.toContain("SEGREDO-123");
      }
      spy.mockRestore();
    }
  });
});

describe("sair", () => {
  async function openProfile(fake: FakeServer, options: Options = {}) {
    await openApp({ transport: fake.transport, signedIn: true, ...options });
    await press("header-profile");
    expect(screen.getByTestId("screen-profile")).toBeTruthy();
  }

  it("o perfil oferece 'Sair' e 'Sair dos outros aparelhos' com confirmação", async () => {
    await openProfile(server());
    expect(screen.getByTestId("profile-logout")).toBeTruthy();
    expect(screen.getByTestId("profile-logout-others")).toBeTruthy();
    await press("profile-logout");
    expect(screen.getByText("Sair deste aparelho?")).toBeTruthy();
    await press("profile-session-cancel");
    expect(screen.queryByText("Sair deste aparelho?")).toBeNull();
    expect(screen.getByTestId("screen-profile")).toBeTruthy(); // continua dentro
  });

  it("confirmar sai: volta à entrada e apaga tokens e dados", async () => {
    const fake = server();
    const store = createMemoryTokenStore();
    await store.save(storedSession(1));
    await openProfile(fake, { tokenStore: store });
    await press("profile-logout");
    await press("profile-logout-confirm");
    expect(fake.callsTo(LOGOUT)).toHaveLength(1);
    expect(screen.getByTestId("screen-signin")).toBeTruthy();
    expect(screen.queryByTestId("screen-profile")).toBeNull();
    expect(await store.load()).toBeNull();
    expect(JSON.stringify(screen.toJSON())).not.toMatch(
      /Alex Paciente|Dra\. Helena/,
    );
  });

  it("sem rede o aparelho sai do mesmo jeito", async () => {
    const store = createMemoryTokenStore();
    await store.save(storedSession(1));
    await openProfile(
      server({
        [LOGOUT]: () => networkFailure(),
      }),
      { tokenStore: store },
    );
    await press("profile-logout");
    await press("profile-logout-confirm");
    expect(screen.getByTestId("screen-signin")).toBeTruthy();
    expect(await store.load()).toBeNull();
  });

  it("sair dos outros aparelhos informa quantos foram desconectados", async () => {
    const fake = server();
    await openProfile(fake);
    await press("profile-logout-others");
    await press("profile-logout-others-confirm");
    expect(fake.callsTo(OTHERS)).toHaveLength(1);
    expect(screen.getByTestId("action-feedback")).toHaveTextContent(
      has("2 outros aparelhos foram desconectados"),
    );
    expect(screen.getByTestId("screen-profile")).toBeTruthy(); // este segue conectado
  });

  it("sessão expirada no servidor volta à entrada com aviso", async () => {
    const fake = server({
      "/mobile/me/": () => ({ status: 401, body: {} }),
      "/mobile/auth/refresh/": () => ({
        status: 401,
        body: { detail: "x", code: "invalid_token" },
      }),
    });
    await openApp({ transport: fake.transport, signedIn: true });
    expect(screen.getByTestId("screen-signin")).toBeTruthy();
    expect(screen.getByTestId("auth-notice")).toHaveTextContent(
      has("Sua sessão terminou"),
    );
  });
});

describe("modo preview não usa sessão", () => {
  it("abre direto nas abas, sem entrada e sem rede", async () => {
    const fake = server();
    renderApp({ mode: "preview", transport: fake.transport });
    await settle();
    expect(screen.getByTestId("screen-home")).toBeTruthy();
    expect(screen.queryByTestId("screen-signin")).toBeNull();
    expect(screen.queryByTestId("profile-logout")).toBeNull();
    expect(fake.calls).toHaveLength(0);
    expect(SecureStore.getItemAsync).not.toHaveBeenCalled();
  });
});
