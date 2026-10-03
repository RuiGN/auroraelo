import React from "react";
import { act, fireEvent, render, screen } from "@testing-library/react-native";
import { View } from "react-native";
import { ApiError } from "../src/api/errors";
import { Button } from "../src/components/Button";
import {
  failureFeedback,
  FeedbackAlert,
  useRunAction,
} from "../src/components/Feedback";
import { LiveActionRegistry } from "../src/data/live/actions";
import { mutations } from "../src/data/mutations";
import { ActionOutcome } from "../src/data/outcome";
import { translate } from "../src/i18n";
import { createFakeServer, deferred, meBody } from "./fakeApi";
import { Options, Providers, settle } from "./helpers";

/** Avança só o relógio (sem disparar os temporizadores seguintes). */
const advance = (ms: number) =>
  act(async () => void (await jest.advanceTimersByTimeAsync(ms)));

const t = (key: Parameters<typeof translate>[1]) => translate("pt-br", key);

describe("failureFeedback", () => {
  const failures: [ActionOutcome, RegExp][] = [
    [{ ok: false, reason: "unavailable" }, /ainda não está disponível/],
    [
      { ok: false, reason: "unavailable", code: "server_error" },
      /servidor não conseguiu concluir/,
    ],
    [{ ok: false, reason: "invalid" }, /Confira os campos/],
    [
      { ok: false, reason: "invalid", code: "invalid_intensity" },
      /entre 1 e 10/,
    ],
    [{ ok: false, reason: "offline" }, /Sem conexão com a clínica agora/],
    [{ ok: false, reason: "rejected" }, /Não foi possível salvar/],
    [
      { ok: false, reason: "rejected", code: "plan_closed" },
      /plano já foi encerrado/,
    ],
    [
      { ok: false, reason: "rejected", code: "codigo_novo_do_servidor" },
      /Não foi possível salvar/,
    ],
    [{ ok: false, reason: "session" }, /sessão terminou/],
    [{ ok: false, reason: "blocked" }, /temporariamente suspenso/],
  ];

  it.each(failures)("%j", (outcome, text) => {
    const feedback = failureFeedback(
      outcome as Extract<ActionOutcome, { ok: false }>,
      t,
    );
    expect(feedback.text).toMatch(text);
    // Falha nunca tem tom de sucesso nem texto de "salvo/concluído".
    expect(feedback.tone).not.toBe("success");
    expect(feedback.text).not.toMatch(/^(Salvo|Concluído|Registrado)/);
  });
});

/** Tela mínima: um botão que grava e mostra o resultado, como as telas do app. */
function Probe() {
  const { run, feedback, pending } = useRunAction();
  return (
    <View>
      <Button
        testID="probe"
        label="Gravar"
        loading={pending}
        onPress={() => void run(mutations.setLowEnergy(true), "common.done")}
      />
      <FeedbackAlert feedback={feedback} />
    </View>
  );
}

function renderProbe(options: Options) {
  return render(
    <Providers {...options}>
      <Probe />
    </Providers>,
  );
}

const okAction = (
  work: () => Promise<void> = async () => undefined,
): LiveActionRegistry => ({
  setLowEnergy: {
    run: () => async () => {
      await work();
      return { ok: true };
    },
    refresh: [],
  },
});

const server = () => createFakeServer(() => ({ status: 200, body: meBody() }));

describe("useRunAction", () => {
  it("só diz 'concluído' quando a ação remota deu certo", async () => {
    renderProbe({
      mode: "live",
      signedIn: true,
      transport: server().transport,
      actions: okAction(),
    });
    await settle();
    fireEvent.press(screen.getByTestId("probe"));
    await settle();
    expect(screen.getByTestId("action-feedback")).toHaveTextContent(
      "Concluído",
    );
    expect(screen.getByTestId("action-feedback")).not.toHaveTextContent(
      /demonstração/,
    );
  });

  it.each([
    {
      name: "sem rede",
      error: new ApiError(0, "network"),
      text: /Sem conexão com a clínica agora/,
    },
    {
      name: "recusada pelo servidor",
      error: new ApiError(409, "already_completed"),
      text: /já foi concluído/,
    },
    {
      name: "clínica bloqueada",
      error: new ApiError(402, "clinic_blocked"),
      text: /temporariamente suspenso/,
    },
  ])(
    "falha ($name) mostra o motivo e nunca 'concluído'",
    async ({ error, text }) => {
      renderProbe({
        mode: "live",
        signedIn: true,
        transport: server().transport,
        actions: okAction(async () => {
          throw error;
        }),
      });
      await settle();
      fireEvent.press(screen.getByTestId("probe"));
      await settle();
      const feedback = screen.getByTestId("action-feedback");
      expect(feedback).toHaveTextContent(text);
      expect(feedback).not.toHaveTextContent(/Concluído/);
    },
  );

  it("gravação lenta: mostra 'trabalhando' depois de 250 ms e some ao terminar", async () => {
    const gate = deferred();
    renderProbe({
      mode: "live",
      signedIn: true,
      transport: server().transport,
      actions: okAction(() => gate.promise),
    });
    await settle();
    fireEvent.press(screen.getByTestId("probe"));
    await advance(100);
    expect(screen.queryByTestId("action-feedback")).toBeNull();
    expect(
      screen.getByTestId("probe").props.accessibilityState,
    ).not.toMatchObject({
      busy: true,
    });
    await advance(300);
    expect(screen.getByTestId("probe")).toBeDisabled(); // `loading` desabilita
    gate.resolve();
    await settle();
    expect(screen.getByTestId("probe")).toBeEnabled();
    expect(screen.getByTestId("action-feedback")).toHaveTextContent(
      "Concluído",
    );
  });

  it("no preview resolve na hora e mantém o aviso de demonstração", async () => {
    renderProbe({ mode: "preview" });
    fireEvent.press(screen.getByTestId("probe"));
    await settle();
    const feedback = screen.getByTestId("action-feedback");
    expect(feedback).toHaveTextContent(/Concluído/);
    expect(feedback).toHaveTextContent(/Registrado na demonstração/);
  });
});
