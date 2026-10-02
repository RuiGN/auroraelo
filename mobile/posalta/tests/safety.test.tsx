import { readFileSync, readdirSync, statSync } from "node:fs";
import { join, resolve } from "node:path";
import { fireEvent, screen } from "@testing-library/react-native";
import { Linking } from "react-native";
import { buildPreviewSnapshot } from "../src/data/previewData";
import { flush, NOW, renderApp } from "./helpers";

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

describe("modo clínica (live) sem API autenticada", () => {
  it("não mostra nenhum dado de paciente, nem de demonstração", async () => {
    renderApp({ mode: "live" });
    expect(await screen.findByTestId("unavailable-state")).toBeTruthy();
    expect(screen.queryByTestId("demo-banner")).toBeNull();
    expect(screen.queryByTestId("header-demo")).toBeNull();
    const snapshot = buildPreviewSnapshot(NOW);
    const text = JSON.stringify(screen.toJSON());
    for (const secret of [
      snapshot.patient.displayName,
      snapshot.medications[0].name,
      snapshot.patient.careTeam[0].name,
      "Sertralina",
      "Recuperação",
    ]) {
      expect(text).not.toContain(secret);
    }
    expect(text).not.toMatch(/recuperação\b.*dias/);
  });

  it("explica que nada é exibido, salvo ou enviado", async () => {
    renderApp({ mode: "live" });
    expect(
      await screen.findByText("Ainda não conectado à clínica"),
    ).toBeTruthy();
    expect(screen.getByText(/nada é exibido, salvo ou enviado/)).toBeTruthy();
  });

  it("a Ajuda continua funcionando sem conexão e sem pessoas fictícias", async () => {
    const openURL = jest.spyOn(Linking, "openURL").mockResolvedValue(true);
    renderApp({ mode: "live" });
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

  it("o perfil e as telas de dados mostram o estado indisponível", async () => {
    renderApp({ mode: "live" });
    fireEvent.press(await screen.findByTestId("header-profile"));
    flush();
    expect(await screen.findByTestId("screen-profile")).toBeTruthy();
    expect(screen.getByTestId("unavailable-state")).toBeTruthy();
    fireEvent.press(screen.getByTestId("profile-privacy"));
    flush();
    expect(await screen.findByTestId("screen-privacy")).toBeTruthy();
    expect(screen.queryByTestId("consent-terms_of_use")).toBeNull();
    expect(screen.queryByTestId("privacy-open-access")).toBeNull();
  });

  it("idioma e aparência funcionam também sem conexão", async () => {
    renderApp({ mode: "live" });
    fireEvent.press(await screen.findByTestId("header-profile"));
    flush();
    fireEvent.press(await screen.findByTestId("profile-settings"));
    flush();
    expect(await screen.findByTestId("settings-language")).toBeTruthy();
    expect(screen.getByTestId("settings-theme")).toBeTruthy();
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

  it("o código não envia dados: sem fetch, XMLHttpRequest, WebSocket nem armazenamento clínico", () => {
    const offenders: string[] = [];
    for (const file of sourceFiles(join(root, "src"))) {
      const content = readFileSync(file, "utf8");
      if (
        /\bfetch\s*\(|XMLHttpRequest|WebSocket|SecureStore|SQLite|localStorage/.test(
          content,
        )
      )
        offenders.push(file);
    }
    expect(offenders).toEqual([]);
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
