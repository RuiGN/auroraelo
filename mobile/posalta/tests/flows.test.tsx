import {
  act,
  fireEvent,
  screen,
  waitFor,
  within,
} from "@testing-library/react-native";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { Linking } from "react-native";
import { CHECKIN_QUESTION_KEYS } from "../src/domain/types";
import { flush, renderApp } from "./helpers";

async function press(testID: string) {
  fireEvent.press(screen.getByTestId(testID));
  flush();
}

async function openTab(label: string) {
  fireEvent.press(screen.getByLabelText(label));
  flush();
}

describe("Hoje", () => {
  it("cumprimenta pelo horário e conta os dias desde a alta", async () => {
    renderApp();
    expect(await screen.findByText("Bom dia, Alex")).toBeTruthy();
    expect(screen.getByText("Fazem 9 dias desde a sua alta")).toBeTruthy();
    expect(screen.getByTestId("recovery-days")).toHaveTextContent(
      "9 dias em recuperação",
    );
  });

  it("mostra a faixa de demonstração e o selo DEMO", async () => {
    renderApp();
    expect(await screen.findByTestId("demo-banner")).toBeTruthy();
    expect(screen.getByTestId("header-demo")).toBeTruthy();
  });

  it("o modo de pouca energia reduz a tela ao essencial", async () => {
    renderApp();
    await screen.findByTestId("low-energy-prompt");
    expect(screen.getByTestId("today-habits")).toBeTruthy();
    await press("low-energy-on");
    expect(await screen.findByTestId("low-energy-active")).toBeTruthy();
    expect(screen.queryByTestId("today-habits")).toBeNull();
    expect(screen.queryByTestId("today-appointment")).toBeNull();
    expect(screen.getByText("Beber um copo de água")).toBeTruthy();
    expect(screen.getByTestId("today-medications")).toBeTruthy(); // medicação segue visível
    await press("low-energy-off");
    expect(await screen.findByTestId("today-habits")).toBeTruthy();
  });

  it("em inglês e espanhol traduz a interface mas mantém o texto clínico original", async () => {
    renderApp({ locale: "en" });
    expect(await screen.findByText("Good morning, Alex")).toBeTruthy();
    expect(
      screen.getByText("It has been 9 days since your discharge"),
    ).toBeTruthy();
    expect(screen.getByText("Log how you are feeling")).toBeTruthy();
    // texto do prontuário/equipe preserva o idioma original
    expect(screen.getByText("Mapa de gatilhos da semana")).toBeTruthy();
  });

  it("em espanhol cumprimenta e usa o plural correto", async () => {
    renderApp({ locale: "es" });
    expect(await screen.findByText("Buenos días, Alex")).toBeTruthy();
    expect(screen.getByText("Han pasado 9 días desde tu alta")).toBeTruthy();
  });
});

describe("Medicações", () => {
  it("registra uma dose e atualiza o resumo de hoje", async () => {
    renderApp();
    await press("today-medications");
    await screen.findByTestId("screen-medications");
    const taken = screen.getAllByTestId(/^dose-taken-/);
    expect(taken).toHaveLength(3);
    fireEvent.press(taken[0]);
    flush();
    expect(await screen.findByText("Tomada")).toBeTruthy();
    expect(screen.getAllByTestId(/^undo-/)).toHaveLength(1);
    expect(
      screen.getByText("1 de 3 registradas", { includeHiddenElements: true }),
    ).toBeTruthy(); // resumo da tela Hoje
    // o resultado deixa claro que é demonstração
    expect(screen.getByTestId("action-feedback")).toHaveTextContent(
      /Registrado na demonstração/,
    );
  });

  it("permite desfazer o registro", async () => {
    renderApp();
    await press("today-medications");
    await screen.findByTestId("screen-medications");
    fireEvent.press(screen.getAllByTestId(/^dose-late-/)[0]);
    flush();
    fireEvent.press(screen.getAllByTestId(/^undo-/)[0]);
    flush();
    await waitFor(() =>
      expect(screen.queryAllByTestId(/^undo-/)).toHaveLength(0),
    );
    expect(screen.getAllByTestId(/^dose-taken-/)).toHaveLength(3);
  });
});

describe("Check-in diário", () => {
  async function answerAll(
    values: Partial<Record<(typeof CHECKIN_QUESTION_KEYS)[number], number>>,
  ) {
    for (const key of CHECKIN_QUESTION_KEYS) {
      fireEvent.press(screen.getByTestId(`q-${key}-${values[key] ?? 3}`));
    }
  }

  it("só habilita o envio com as 7 perguntas respondidas", async () => {
    renderApp();
    await press("today-checkin");
    await screen.findByTestId("screen-checkin");
    expect(screen.getByTestId("checkin-submit")).toBeDisabled();
    expect(
      screen.getByText("Responda todas as perguntas de 1 a 5 para salvar."),
    ).toBeTruthy();
    for (const key of CHECKIN_QUESTION_KEYS.slice(0, 6))
      fireEvent.press(screen.getByTestId(`q-${key}-3`));
    expect(screen.getByTestId("checkin-submit")).toBeDisabled();
    fireEvent.press(screen.getByTestId("q-motivation-3"));
    expect(screen.getByTestId("checkin-submit")).toBeEnabled();
  });

  it("salva sem prometer acompanhamento em tempo real", async () => {
    renderApp();
    await press("today-checkin");
    await screen.findByTestId("screen-checkin");
    await answerAll({});
    await press("checkin-submit");
    const feedback = await screen.findByTestId("action-feedback");
    expect(feedback).toHaveTextContent(
      /Sua equipe não acompanha este aplicativo em tempo real/,
    );
    expect(screen.queryByTestId("checkin-support-cta")).toBeNull();
    expect(
      await screen.findByText("Registro de hoje feito", {
        includeHiddenElements: true,
      }),
    ).toBeTruthy();
  });

  it("num dia difícil oferece a Ajuda, que abre a tela de ajuda urgente", async () => {
    renderApp();
    await press("today-checkin");
    await screen.findByTestId("screen-checkin");
    await answerAll({ anxiety: 5, general_state: 2 });
    await press("checkin-submit");
    expect(await screen.findByText("Parece um dia difícil")).toBeTruthy();
    await press("checkin-support-cta");
    expect(await screen.findByTestId("screen-urgent-help")).toBeTruthy();
  });
});

describe("Diário", () => {
  it("exige o relato e salva privado por padrão", async () => {
    renderApp();
    await press("quick-diary");
    await screen.findByTestId("screen-journal-new");
    expect(screen.getByTestId("entry-submit")).toBeDisabled();
    fireEvent.press(screen.getByTestId("entry-mood-4"));
    fireEvent.press(screen.getByTestId("entry-intensity-2"));
    fireEvent.press(screen.getByTestId("entry-emotions-calm"));
    expect(screen.getByTestId("entry-submit")).toBeEnabled();
    await press("entry-submit");
    expect(
      await screen.findByText(
        "Escreva pelo menos uma linha sobre o que aconteceu.",
      ),
    ).toBeTruthy();
    expect(screen.getByTestId("entry-visibility-private")).toBeChecked();
    fireEvent.changeText(
      screen.getByTestId("entry-context"),
      "Dia calmo, caminhei à tarde.",
    );
    await press("entry-submit");
    expect(await screen.findByText("Registro salvo no diário.")).toBeTruthy();
  });

  it("registrar vontade de usar mostra as estratégias do plano de prevenção", async () => {
    renderApp();
    await press("quick-craving");
    await screen.findByTestId("screen-craving");
    expect(screen.getByText(/Respirar por 2 minutos/)).toBeTruthy();
    expect(screen.getByTestId("craving-submit")).toBeDisabled();
    fireEvent.press(screen.getByTestId("craving-intensity-7"));
    await press("craving-submit");
    expect(
      await screen.findByText(
        /Se a vontade ficar forte demais, use o botão Ajuda/,
      ),
    ).toBeTruthy();
    expect(screen.getAllByText("Intensidade 7 de 10").length).toBeGreaterThan(
      0,
    );
  });
});

describe("Cuidado e metas", () => {
  it("responde ao plano de cuidado", async () => {
    renderApp();
    await openTab("Cuidado");
    await press("care-plan");
    await screen.findByTestId("screen-care-plan");
    expect(screen.getByTestId("plan-submit")).toBeDisabled();
    fireEvent.press(screen.getByTestId("plan-decision-review_requested"));
    fireEvent.changeText(
      screen.getByTestId("plan-notes"),
      "Posso trocar o dia da caminhada?",
    );
    await press("plan-submit");
    const response = await screen.findByTestId("plan-response");
    expect(
      within(response).getByText("Você respondeu: Pedir revisão"),
    ).toBeTruthy();
    expect(
      within(response).getByText(/não avisa ninguém em tempo real/),
    ).toBeTruthy();
  });

  it("marca passos de uma meta e atualiza o progresso", async () => {
    renderApp();
    await openTab("Cuidado");
    await press("care-goals");
    await screen.findByTestId("screen-goals");
    await press("goal-g-1");
    await screen.findByTestId("screen-goal-detail");
    expect(screen.getByTestId("goal-progress")).toHaveTextContent(
      "1 de 3 passos",
    );
    await press("step-gs-2");
    expect(screen.getByTestId("goal-progress")).toHaveTextContent(
      "2 de 3 passos",
    );
    await press("goal-complete");
    expect(await screen.findByText("Concluída")).toBeTruthy();
  });

  it("conclui um exercício com escala de 1 a 5", async () => {
    renderApp();
    await openTab("Cuidado");
    await press("care-exercises");
    await screen.findByTestId("screen-exercises");
    await press("exercise-ex-1");
    await screen.findByTestId("screen-exercise-detail");
    expect(screen.getByTestId("exercise-submit")).toBeDisabled();
    fireEvent.changeText(
      screen.getByTestId("exercise-text"),
      "Gatilho: bar perto do trabalho.",
    );
    expect(
      screen.getByTestId("exercise-visibility-confirmation_required"),
    ).toBeChecked();
    await press("exercise-submit");
    expect(await screen.findByTestId("exercise-response")).toHaveTextContent(
      "Gatilho: bar perto do trabalho.",
    );
  });
});

describe("Agenda", () => {
  it("solicita consulta: fica 'aguardando confirmação', nunca confirmada", async () => {
    renderApp();
    await openTab("Agenda");
    await press("agenda-request");
    await screen.findByTestId("screen-request-appointment");
    expect(screen.getByTestId("request-submit")).toBeDisabled();
    fireEvent.press(screen.getByTestId("request-service-s-2"));
    const slots = screen.getAllByTestId(/^request-slot-/);
    expect(slots.length).toBe(2);
    fireEvent.press(slots[0]);
    await press("request-submit");
    expect(await screen.findByTestId("action-feedback")).toHaveTextContent(
      /Aguarde a confirmação da clínica/,
    );
    expect(screen.getAllByTestId(/^request-slot-/)).toHaveLength(1); // o horário pedido saiu da lista
  });

  it("pede reagendamento sem mudar o horário e cancela com confirmação", async () => {
    renderApp();
    await openTab("Agenda");
    await press("appointment-a-2");
    await screen.findByTestId("screen-appointment-detail");
    await press("appointment-reschedule");
    expect(
      await screen.findByText(/só vale quando a clínica responder/),
    ).toBeTruthy();
    expect(screen.queryByTestId("appointment-reschedule")).toBeNull();
  });
});

describe("Perfil, idioma e privacidade", () => {
  it("troca o idioma da interface e persiste só essa preferência", async () => {
    renderApp();
    await press("header-profile");
    await screen.findByTestId("screen-profile");
    await press("profile-settings");
    await screen.findByTestId("screen-settings");
    await press("settings-language-en");
    await waitFor(() => expect(screen.getByText("Language")).toBeTruthy());
    expect(AsyncStorage.setItem).toHaveBeenCalledWith(
      "aurora-elo.ui-language",
      "en",
    );
    expect(
      screen.getByText(/Changes only the interface language/),
    ).toBeTruthy();
    // nada além de idioma e tema é gravado no aparelho
    const keys = (AsyncStorage.setItem as jest.Mock).mock.calls.map(
      ([key]) => key,
    );
    expect(new Set(keys)).toEqual(new Set(["aurora-elo.ui-language"]));
  });

  it("troca a aparência e a persiste", async () => {
    renderApp();
    await press("header-profile");
    await press("profile-settings");
    await screen.findByTestId("screen-settings");
    await press("settings-theme-dark");
    expect(AsyncStorage.setItem).toHaveBeenCalledWith(
      "aurora-elo.posalta.theme",
      "dark",
    );
  });

  it("consentimentos obrigatórios não têm botão de revogar; os opcionais têm", async () => {
    renderApp();
    await press("header-profile");
    await press("profile-privacy");
    await screen.findByTestId("screen-privacy");
    expect(screen.queryByTestId("consent-toggle-terms_of_use")).toBeNull();
    expect(screen.queryByTestId("consent-toggle-clinical_limits")).toBeNull();
    await press("consent-toggle-communication");
    expect(
      within(screen.getByTestId("consent-communication")).getByText("Revogado"),
    ).toBeTruthy();
    expect(
      within(screen.getByTestId("consent-communication")).getByText(
        "Autorizar de novo",
      ),
    ).toBeTruthy();
  });

  it("pedidos LGPD ficam aguardando identidade e não duplicam", async () => {
    renderApp();
    await press("header-profile");
    await press("profile-privacy");
    await screen.findByTestId("screen-privacy");
    await press("privacy-open-access");
    expect(
      await screen.findByText(/Em produção, a clínica confirma sua identidade/),
    ).toBeTruthy();
    expect(
      screen.getByText(/Aguardando confirmação de identidade/),
    ).toBeTruthy();
    await press("privacy-open-access");
    expect(
      await screen.findByText("Já existe um pedido deste tipo em andamento."),
    ).toBeTruthy();
  });

  it("o perfil explica que anotações da psicoterapia são restritas ao psicólogo e ao paciente", async () => {
    renderApp();
    await press("header-profile");
    expect(
      await screen.findByText(/restritas ao seu psicólogo e a você/),
    ).toBeTruthy();
  });
});

describe("Rede de apoio e conteúdo", () => {
  it("garante que o diário nunca é compartilhado e permite encerrar o acompanhamento", async () => {
    renderApp();
    await openTab("Apoio");
    await press("support-network");
    await screen.findByTestId("screen-network");
    expect(
      screen.getByText("Seu diário nunca é compartilhado com a rede de apoio."),
    ).toBeTruthy();
    await press("revoke-sn-1");
    await press("revoke-confirm-sn-1");
    expect(await screen.findByText("Acompanhamento encerrado")).toBeTruthy();
  });

  it("abre um conteúdo indicado, mostra cuidados e marca como lido", async () => {
    renderApp();
    await openTab("Apoio");
    await press("support-learn");
    await screen.findByTestId("screen-learn");
    await press("content-c-1");
    await screen.findByTestId("screen-content-detail");
    expect(
      screen.getByText("Indicado por Rafael Moura", { exact: false }),
    ).toBeTruthy();
    expect(
      screen.getByText(/não substitui a orientação da sua equipe/),
    ).toBeTruthy();
    await press("content-read");
    expect(
      within(screen.getByTestId("content-read")).getByText("Lido"),
    ).toBeTruthy();
  });
});

describe("Ajuda urgente", () => {
  let openURL: jest.SpyInstance;
  beforeEach(() => {
    openURL = jest.spyOn(Linking, "openURL").mockResolvedValue(true);
  });
  afterEach(() => openURL.mockRestore());

  it("está no cabeçalho e abre o discador só quando a pessoa toca", async () => {
    renderApp();
    await press("header-help");
    await screen.findByTestId("screen-urgent-help");
    expect(openURL).not.toHaveBeenCalled(); // abrir a tela nunca liga nem avisa ninguém
    await press("call-192");
    await press("call-188");
    expect(openURL.mock.calls.map(([url]) => url)).toEqual([
      "tel:192",
      "tel:188",
    ]);
  });

  it("tem botão visível para fechar e voltar à tela anterior", async () => {
    renderApp();
    await press("header-help");
    await screen.findByTestId("screen-urgent-help");
    await press("help-close");
    await waitFor(() =>
      expect(screen.queryByTestId("screen-urgent-help")).toBeNull(),
    );
    expect(screen.getByTestId("screen-home")).toBeTruthy();
  });

  it("diz claramente que ninguém é notificado e que o app não é serviço de emergência", async () => {
    renderApp();
    await press("header-help");
    expect(await screen.findByTestId("help-no-one-notified")).toHaveTextContent(
      "Ninguém foi notificado por este aplicativo.",
    );
    expect(
      screen.getByText(
        /não é um serviço de emergência e não monitora você em tempo real/,
      ),
    ).toBeTruthy();
  });

  it("liga ou envia mensagem às pessoas de confiança, com texto codificado", async () => {
    renderApp();
    await press("header-help");
    const card = await screen.findByTestId("urgent-contact-uc-1");
    fireEvent.press(within(card).getByLabelText("Ligar"));
    fireEvent.press(within(card).getByLabelText("Enviar mensagem"));
    const [call, sms] = openURL.mock.calls.map(([url]) => String(url));
    expect(call).toBe("tel:+558100000002");
    expect(sms.startsWith("sms:+558100000002?body=")).toBe(true);
    expect(decodeURIComponent(sms.split("body=")[1])).toBe(
      "Oi, estou em um momento difícil e queria conversar. Pode falar agora?",
    );
  });

  it("avisa se o aparelho não consegue abrir o discador", async () => {
    openURL.mockRejectedValue(new Error("sem discador"));
    renderApp();
    await press("header-help");
    await act(async () => {
      fireEvent.press(screen.getByTestId("call-192"));
    });
    expect(await screen.findByText(/Disque o número manualmente/)).toBeTruthy();
  });

  it("mostra o plano pessoal e o exercício 5-4-3-2-1", async () => {
    renderApp();
    await press("header-help");
    expect(await screen.findByTestId("urgent-plan")).toBeTruthy();
    expect(
      screen.getByText("Olhe ao redor e nomeie 5 coisas que você vê"),
    ).toBeTruthy();
    expect(screen.getByTestId("breathing-toggle")).toBeTruthy();
  });

  it("a respiração guiada inicia e para por conta da pessoa", async () => {
    renderApp();
    await press("header-help");
    await screen.findByTestId("breathing");
    // sem avançar relógios: iniciar mostra a primeira fase
    fireEvent.press(screen.getByTestId("breathing-toggle"));
    expect(await screen.findByText("Inspire devagar")).toBeTruthy();
    act(() => {
      jest.advanceTimersByTime(4000);
    });
    expect(await screen.findByText("Solte o ar devagar")).toBeTruthy();
    fireEvent.press(screen.getByTestId("breathing-toggle"));
    expect(screen.queryByText("Solte o ar devagar")).toBeNull();
    expect(screen.getByText("Começar respiração")).toBeTruthy();
  });
});
