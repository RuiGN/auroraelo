import { fireEvent, screen } from "@testing-library/react-native";
import { LIVE_ACTIONS } from "../src/data/live/actions";
import { LOADERS } from "../src/data/live/registry";
import { createContractServer } from "./contractServer";
import { createFakeServer, meBody } from "./fakeApi";
import { renderApp, settle } from "./helpers";

/** O carregamento passa por várias promessas encadeadas (sessão → loaders → detalhes). */
async function settleLoad() {
  for (let turn = 0; turn < 6; turn += 1) await settle();
}

const DOC = "66666666-6666-4666-8666-666666666666";

function consentRow(status: "pending" | "accepted") {
  return {
    document_id: DOC,
    purpose: "terms_of_use",
    kind: "terms",
    title: "Termos de uso",
    version: "2025.1",
    mandatory: true,
    status,
    decided_at: status === "accepted" ? "2026-10-02T12:00:00Z" : null,
    can_revoke: false,
  };
}

function liveApp(initial: "pending" | "accepted") {
  let status = initial;
  const contract = createContractServer({
    overrides: {
      "GET /mobile/me/": meBody(),
      "GET /mobile/consents/": () => [consentRow(status)],
      "GET /mobile/consents/{document_id}/": () => ({
        ...consentRow(status),
        content: "Texto completo dos termos.",
        refusal_consequence: "Não será possível usar o aplicativo.",
        alternative_instructions: "",
        clinic_contact_instructions: "",
      }),
      "POST /mobile/consents/{document_id}/decision/": () => {
        status = "accepted";
        return consentRow("accepted");
      },
    },
  });
  const server = createFakeServer(contract.handler);
  renderApp({
    mode: "live",
    signedIn: true,
    transport: server.transport,
    loaders: LOADERS,
    actions: LIVE_ACTIONS,
  });
  return { server, contract };
}

describe("aceite obrigatório no primeiro acesso", () => {
  it("mostra o documento antes dos dados e libera o app depois do aceite", async () => {
    const { server, contract } = liveApp("pending");
    await settleLoad();
    expect(await screen.findByTestId("screen-consent-gate")).toBeTruthy();
    expect(screen.getByText("Termos de uso")).toBeTruthy();
    expect(screen.getByTestId("gate-consent-content")).toHaveTextContent(
      "Texto completo dos termos.",
    );
    expect(screen.queryByTestId("screen-home")).toBeNull();
    fireEvent.press(screen.getByTestId("gate-consent-accept"));
    await settleLoad();
    expect(screen.queryByTestId("screen-consent-gate")).toBeNull();
    expect(
      server.calls.filter((call) => call.path.endsWith("/decision/")),
    ).toHaveLength(1);
    expect(contract.violations).toEqual([]);
  });

  it("sem pendência o app abre direto", async () => {
    liveApp("accepted");
    await settleLoad();
    expect(screen.queryByTestId("screen-consent-gate")).toBeNull();
    expect(await screen.findByTestId("screen-home")).toBeTruthy();
  });

  it("sair sem aceitar encerra a sessão", async () => {
    liveApp("pending");
    await settleLoad();
    fireEvent.press(await screen.findByTestId("gate-consent-signout"));
    await settleLoad();
    expect(await screen.findByTestId("screen-signin")).toBeTruthy();
  });
});
