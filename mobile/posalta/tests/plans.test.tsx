import { fireEvent, screen, within } from "@testing-library/react-native";
import { buildPreviewSnapshot } from "../src/data/previewData";
import { NOW, renderApp, settle } from "./helpers";

async function press(testID: string) {
  fireEvent.press(screen.getByTestId(testID));
  await settle();
}

async function type(testID: string, text: string) {
  fireEvent.changeText(screen.getByTestId(testID), text);
  await settle();
}

async function openTab(label: string) {
  fireEvent.press(screen.getByLabelText(label));
  await settle();
}

describe("conteúdo pessoal editado pelo paciente (demonstração)", () => {
  it("define a meta de recuperação quando ainda não existe", async () => {
    const snapshot = { ...buildPreviewSnapshot(NOW), sobriety: null };
    renderApp({ initialSnapshot: snapshot });
    await openTab("Diário");
    await press("recovery-define");
    await screen.findByTestId("screen-recovery-goal");
    expect(screen.getByTestId("goal-submit")).toBeDisabled();
    await type("goal-focus", "Álcool");
    await press("goal-type-reduction");
    await press("goal-since-week");
    await press("goal-submit");
    // volta ao diário já com o contador da meta
    expect(await screen.findByTestId("recovery-card")).toBeTruthy();
    expect(screen.getByTestId("recovery-count")).toHaveTextContent("7 dias");
  });

  it("cria e edita o plano de prevenção de recaída", async () => {
    const snapshot = { ...buildPreviewSnapshot(NOW), relapsePlan: null };
    renderApp({ initialSnapshot: snapshot });
    await openTab("Cuidado");
    await press("care-relapse");
    await press("relapse-create");
    await screen.findByTestId("screen-relapse-edit");
    await type("relapse-field-triggers", "Fim do expediente");
    await press("relapse-save");
    expect(
      within(await screen.findByTestId("relapse-triggers")).getByText(
        "Fim do expediente",
      ),
    ).toBeTruthy();
    expect(screen.queryByTestId("relapse-protective_factors")).toBeNull();
    await press("relapse-edit");
    await type("relapse-field-triggers", "");
    await type("relapse-field-protective_factors", "Caminhar");
    await press("relapse-save");
    expect(
      await screen.findByTestId("relapse-protective_factors"),
    ).toBeTruthy();
    expect(screen.queryByTestId("relapse-triggers")).toBeNull();
  });

  it("edita o plano urgente: instruções, uma pessoa de confiança nova e remoção", async () => {
    renderApp();
    await openTab("Cuidado");
    await press("care-urgent-plan");
    await screen.findByTestId("screen-urgent-edit");
    await type("urgent-instructions", "Respirar e ligar para alguém.");
    await press("urgent-save");
    await press("urgent-add");
    await type("contact-name", "Rafa");
    await type("contact-relationship", "Amigo");
    await type("contact-phone", "11 98888-7777");
    await press("contact-save");
    expect(await screen.findByText("Rafa")).toBeTruthy();
    // telefone curto demais não é aceito
    await press("urgent-add");
    await type("contact-name", "Zé");
    await type("contact-relationship", "Vizinho");
    await type("contact-phone", "123");
    await press("contact-save");
    expect(screen.queryByText("Zé")).toBeNull();
  });

  it("escolhe as ações de pouca energia", async () => {
    renderApp();
    await settle();
    await press("low-energy-edit");
    await screen.findByTestId("screen-lowenergy-edit");
    await type("lowenergy-action-0", "Beber água");
    await type("lowenergy-action-1", "Abrir a janela");
    await type("lowenergy-action-2", "");
    await press("lowenergy-save");
    await press("low-energy-on");
    expect(await screen.findByTestId("low-energy-active")).toBeTruthy();
    expect(screen.getByText("Beber água")).toBeTruthy();
  });
});
