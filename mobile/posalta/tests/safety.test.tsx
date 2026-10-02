import { readFileSync, readdirSync, statSync } from "node:fs";
import { join, resolve } from "node:path";
import { fireEvent, screen } from "@testing-library/react-native";
import { Linking } from "react-native";
import { buildPreviewSnapshot } from "../src/data/previewData";
import { createFakeServer, Handler, meBody, networkFailure } from "./fakeApi";
import { flush, NOW, renderApp, settle } from "./helpers";

const root = resolve(__dirname, "..");
const appJson = JSON.parse(readFileSync(join(root, "app.json"), "utf8")).expo;

function sourceFiles(dir: string): string[] {
  return readdirSync(dir).flatMap((name) => {
    const path = join(dir, name);
    return statSync(path).isDirectory()
      ? sourceFiles(path)
      : /\.(ts|tsx)$/.test(name)
        ? [path]
        : [];
  });
}

/** Tudo o que só existe nos dados de demonstração: nunca pode aparecer no live. */
function previewSecrets() {
  const snapshot = buildPreviewSnapshot(NOW);
  return [
    snapshot.patient.displayName,
    snapshot.medications[0].name,
    snapshot.patient.careTeam[0].name,
    "Sertralina",
    "Recuperação",
  ];
}

const liveServer = (overrides: Record<string, Handler> = {}) =>
  createFakeServer((call) => {
    const custom = overrides[call.path];
    if (custom) return custom(call);
    return call.path === "/mobile/me/"
      ? { status: 200, body: meBody() }
      : { status: 404, body: { detail: "x", code: "not_found" } };
  });

describe("modo clínica (live) sem sessão", () => {
  it("sem servidor configurado não mostra nenhum dado, nem de demonstração", async () => {
    renderApp({ mode: "live" });
    await settle();
    expect(screen.getByTestId("screen-config-missing")).toBeTruthy();
    expect(screen.queryByTestId("demo-banner")).toBeNull();
    expect(screen.queryByTestId("header-demo")).toBeNull();
    const text = JSON.stringify(screen.toJSON());
    for (const secret of previewSecrets()) expect(text).not.toContain(secret);
    expect(text).not.toMatch(/recuperação\b.*dias/);
  });

  it("com servidor mas sem entrar, só existe a pilha de entrada", async () => {
    const server = liveServer();
    renderApp({ mode: "live", transport: server.transport });
    await settle();
    expect(screen.getByTestId("screen-signin")).toBeTruthy();
    expect(screen.queryByTestId("screen-home")).toBeNull();
    expect(screen.queryByLabelText("Cuidado")).toBeNull(); // sem abas
    expect(server.calls).toHaveLength(0); // nada é pedido antes de entrar
    const text = JSON.stringify(screen.toJSON());
    for (const secret of previewSecrets()) expect(text).not.toContain(secret);
  });

  it("explica, sem servidor, que nada é exibido, salvo ou enviado", async () => {
    renderApp({ mode: "live" });
    await settle();
    expect(screen.getByText("Aplicativo sem configuração")).toBeTruthy();
    expect(screen.getByText(/Nada é exibido, salvo ou enviado/)).toBeTruthy();
  });

  it("a Ajuda continua funcionando sem conexão e sem pessoas fictícias", async () => {
    const openURL = jest.spyOn(Linking, "openURL").mockResolvedValue(true);
    renderApp({ mode: "live" });
    await settle();
    fireEvent.press(await screen.findByTestId("header-help"));
    flush();
    expect(await screen.findByTestId("screen-urgent-help")).toBeTruthy();
    expect(
      screen.getByText(
        "Você ainda não cadastrou pessoas de confiança com a equipe.",
      ),
    ).toBeTruthy();
    expect(screen.queryByTestId("urgent-plan")).toBeNull();
    expect(screen.queryByText(/demonstração/i)).toBeNull();
    fireEvent.press(screen.getByTestId("call-192"));
    expect(openURL).toHaveBeenCalledWith("tel:192");
    openURL.mockRestore();
  });
});

describe("modo clínica (live) com sessão", () => {
  it("mostra carregando e depois só o que veio da API (nada de demonstração)", async () => {
    const server = liveServer();
    renderApp({ mode: "live", transport: server.transport, signedIn: true });
    await settle();
    expect(await screen.findByText("Bom dia, Alex")).toBeTruthy();
    expect(screen.queryByTestId("demo-banner")).toBeNull();
    expect(screen.queryByTestId("unavailable-state")).toBeNull();
    expect(screen.queryByText("Ainda não conectado à clínica")).toBeNull();
    const text = JSON.stringify(screen.toJSON());
    for (const secret of previewSecrets()) expect(text).not.toContain(secret);
  });

  it("o carregamento tem estado próprio (não o aviso de 'não conectado')", async () => {
    const server = liveServer({
      "/mobile/me/": () => new Promise(() => undefined) as never, // nunca responde
    });
    renderApp({ mode: "live", transport: server.transport, signedIn: true });
    await settle();
    expect(screen.getByTestId("loading-state")).toBeTruthy();
    expect(screen.queryByTestId("unavailable-state")).toBeNull();
  });

  it("falha ao carregar mostra o erro acolhedor e 'tentar de novo' recupera", async () => {
    let offline = true;
    const server = liveServer({
      "/mobile/me/": () =>
        offline ? networkFailure() : { status: 200, body: meBody() },
    });
    renderApp({ mode: "live", transport: server.transport, signedIn: true });
    await settle();
    expect(screen.getByTestId("load-error-state")).toBeTruthy();
    expect(screen.getByText(/Sem conexão com o servidor agora/)).toBeTruthy();
    expect(screen.queryByTestId("unavailable-state")).toBeNull();
    offline = false;
    fireEvent.press(screen.getByTestId("retry-load"));
    await settle();
    expect(await screen.findByText("Bom dia, Alex")).toBeTruthy();
    expect(screen.queryByTestId("load-error-state")).toBeNull();
  });

  it("o perfil mostra o paciente e a equipe reais; idioma e aparência funcionam", async () => {
    const server = liveServer();
    renderApp({ mode: "live", transport: server.transport, signedIn: true });
    await settle();
    fireEvent.press(await screen.findByTestId("header-profile"));
    await settle();
    expect(await screen.findByTestId("screen-profile")).toBeTruthy();
    expect(screen.getByText("Alex Paciente")).toBeTruthy();
    expect(screen.getByText("Dra. Helena")).toBeTruthy();
    fireEvent.press(screen.getByTestId("profile-settings"));
    await settle();
    expect(await screen.findByTestId("settings-language")).toBeTruthy();
    expect(screen.getByTestId("settings-theme")).toBeTruthy();
  });

  it("com só o paciente carregado, todas as abas abrem sem quebrar nem inventar dados", async () => {
    const server = liveServer();
    renderApp({ mode: "live", transport: server.transport, signedIn: true });
    await settle();
    await screen.findByText("Bom dia, Alex");
    const tabs: [string, string][] = [
      ["Cuidado", "screen-care"],
      ["Diário", "screen-diary"],
      ["Agenda", "screen-agenda"],
      ["Apoio", "screen-support"],
      ["Hoje", "screen-home"],
    ];
    for (const [label, id] of tabs) {
      fireEvent.press(screen.getByLabelText(label));
      await settle();
      expect(await screen.findByTestId(id)).toBeTruthy();
      expect(screen.queryByTestId("unavailable-state")).toBeNull();
      expect(screen.queryByTestId("demo-banner")).toBeNull();
    }
    // Sem loader de domínio ainda, só o paciente veio da API (uma leitura).
    expect(server.callsTo("/mobile/me/")).toHaveLength(1);
    expect(server.calls).toHaveLength(1);
  });

  it("gravar algo sem ação registrada diz que não está disponível (nunca 'salvo')", async () => {
    const server = liveServer();
    renderApp({ mode: "live", transport: server.transport, signedIn: true });
    await settle();
    fireEvent.press(await screen.findByTestId("low-energy-on"));
    await settle();
    const feedback = await screen.findByTestId("action-feedback");
    expect(feedback).toHaveTextContent(/ainda não está disponível/);
    expect(feedback).toHaveTextContent(/Nada foi salvo ou enviado/);
    expect(screen.queryByText(/Registrado na demonstração/)).toBeNull();
    // Só a leitura foi ao servidor: nenhuma gravação.
    expect(server.calls.every((call) => call.method === "GET")).toBe(true);
  });
});

describe("honestidade da interface", () => {
  it("nenhum texto do app afirma que alguém foi avisado ou que há monitoramento", () => {
    const { ptBr } = require("../src/i18n/pt-br");
    const { en } = require("../src/i18n/en");
    const { es } = require("../src/i18n/es");
    const forbidden = [
      /equipe foi (avisada|notificada)/i,
      /alerta enviado/i,
      /monitorando você/i,
      /atendimento imediato/i,
      /team (was|has been) notified/i,
      /alert (was )?sent/i,
      /equipo fue (avisado|notificado)/i,
    ];
    for (const catalog of [ptBr, en, es]) {
      for (const text of Object.values(catalog) as string[]) {
        for (const pattern of forbidden) expect(text).not.toMatch(pattern);
      }
    }
  });

  it("o código só fala com a rede pelo cliente HTTP e só guarda sessão no cofre seguro", () => {
    const outside: string[] = [];
    const where = (file: string) => file.replace(`${root}/`, "");
    for (const file of sourceFiles(join(root, "src"))) {
      const content = readFileSync(file, "utf8");
      const name = where(file);
      // Nunca em lugar nenhum: outros transportes e armazenamentos de dados.
      expect({
        name,
        found:
          /XMLHttpRequest|WebSocket|SQLite|localStorage|sessionStorage/.test(
            content,
          ),
      }).toEqual({ name, found: false });
      // `fetch(` e o cabeçalho Authorization só no cliente HTTP.
      if (
        /\bfetch\s*\(|globalThis\.fetch|\bBearer\b|\.Authorization\b|["']Authorization["']/.test(
          content,
        )
      ) {
        if (name !== "src/api/client.ts") outside.push(`${name}: rede`);
      }
      // O cofre seguro só no módulo de armazenamento de tokens.
      if (/SecureStore/.test(content) && name !== "src/api/tokenStore.ts") {
        outside.push(`${name}: cofre`);
      }
      // Nenhum console.* no código do app (tokens, corpos e códigos nunca em log).
      if (
        /\bconsole\./.test(content.replace(/\/\*[\s\S]*?\*\/|\/\/.*$/gm, ""))
      ) {
        outside.push(`${name}: console`);
      }
    }
    expect(outside).toEqual([]);
  });

  it("só idioma e aparência são gravados no aparelho (AsyncStorage)", () => {
    const users: string[] = [];
    for (const file of sourceFiles(join(root, "src"))) {
      if (
        /AsyncStorage\.(setItem|multiSet|mergeItem)/.test(
          readFileSync(file, "utf8"),
        )
      )
        users.push(file.replace(`${root}/`, ""));
    }
    expect(users.sort()).toEqual([
      "src/i18n/index.tsx",
      "src/theme/ThemeProvider.tsx",
    ]);
  });

  it("não há gamificação de sequência (streak) nem pontuação", () => {
    for (const file of sourceFiles(join(root, "src"))) {
      expect(readFileSync(file, "utf8")).not.toMatch(
        /\bstreak\b|leaderboard|ranking|\bpoints\b/i,
      );
    }
  });
});

describe("escopo do app do paciente", () => {
  // Pertencem ao aplicativo da clínica (PRD: Concierge e régua de comunicação), não ao paciente.
  const clinicSide =
    /concierge|conserje|régua|ConciergeLog|CommunicationRule|FamilyContact|post-discharge follow-up/i;

  it("não inclui régua pós-alta, concierge/família nem mensagens com a equipe", async () => {
    renderApp();
    await screen.findByTestId("screen-home");
    for (const id of ["quick-family", "quick-team", "followup-f-1"]) {
      expect(screen.queryByTestId(id)).toBeNull();
    }
    expect(screen.queryByText("Acompanhamento pós-alta")).toBeNull();
    expect(screen.queryByText(/Visita presencial/)).toBeNull();
  });

  it("o hub Apoio oferece só rede de apoio e conteúdo", async () => {
    renderApp();
    fireEvent.press(await screen.findByLabelText("Apoio"));
    flush();
    expect(await screen.findByTestId("support-network")).toBeTruthy();
    expect(screen.getByTestId("support-learn")).toBeTruthy();
    expect(screen.queryByTestId("support-concierge")).toBeNull();
    expect(screen.queryByTestId("support-messages")).toBeNull();
  });

  it("nenhum catálogo de textos, rota ou tela cita essas funções da clínica", () => {
    const { ptBr } = require("../src/i18n/pt-br");
    const { en } = require("../src/i18n/en");
    const { es } = require("../src/i18n/es");
    for (const catalog of [ptBr, en, es]) {
      for (const [key, value] of Object.entries(catalog) as [
        string,
        string,
      ][]) {
        expect(`${key} ${value}`).not.toMatch(
          /concierge|conserje|^(followUp|messages|support\.messages)\b/i,
        );
      }
    }
    const offenders = sourceFiles(join(root, "src"))
      .filter((file) => !file.endsWith("types.ts")) // o comentário de escopo menciona os termos
      .filter((file) => clinicSide.test(readFileSync(file, "utf8")));
    expect(offenders).toEqual([]);
  });
});

describe("configuração nativa", () => {
  it("não declara permissões e bloqueia câmera, microfone, localização e notificações", () => {
    expect(appJson.android.permissions).toEqual([]);
    expect(appJson.android.blockedPermissions).toEqual(
      expect.arrayContaining([
        "android.permission.CAMERA",
        "android.permission.RECORD_AUDIO",
        "android.permission.ACCESS_FINE_LOCATION",
        "android.permission.ACCESS_COARSE_LOCATION",
        "android.permission.POST_NOTIFICATIONS",
      ]),
    );
  });

  it("registra o esquema dos links do app e o cofre seguro", () => {
    expect(appJson.scheme).toBe("auroraelo-posalta");
    expect(appJson.plugins).toContain("expo-secure-store");
    const pkg = JSON.parse(readFileSync(join(root, "package.json"), "utf8"));
    expect(pkg.dependencies["expo-secure-store"]).toBeDefined();
  });

  it("identifica o app e usa a marca Aurora Elo", () => {
    expect(appJson.name).toBe("Aurora Elo Pós-Alta");
    expect(appJson.ios.bundleIdentifier).toBe("br.med.auroraelo.posalta");
    expect(appJson.android.package).toBe("br.med.auroraelo.posalta");
    for (const asset of [
      appJson.icon,
      appJson.splash.image,
      appJson.android.adaptiveIcon.foregroundImage,
    ]) {
      expect(statSync(join(root, asset)).size).toBeGreaterThan(1000);
    }
  });

  it("o símbolo do app é o logo.png fornecido", () => {
    const source = join(root, "../../../logo.png");
    const mark = join(root, "assets/aurora-elo-mark.png");
    expect(readFileSync(mark).equals(readFileSync(source))).toBe(true);
  });
});
