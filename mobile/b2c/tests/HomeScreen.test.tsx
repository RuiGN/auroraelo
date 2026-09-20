import React from "react";
import "@testing-library/react-native/extend-expect";
import {
  render,
  screen,
  fireEvent,
  waitFor,
} from "@testing-library/react-native";
import AsyncStorage from "@react-native-async-storage/async-storage";
import App from "../App";

test.each([
  [
    "en",
    "Recovery at your own pace",
    "Recovery and connection to care",
    "No one has been notified.",
  ],
  [
    "es",
    "Recuperación a tu ritmo",
    "Recuperación y vínculo con el cuidado",
    "Nadie ha sido notificado.",
  ],
] as const)(
  "persiste %s e restaura na próxima abertura",
  async (code, b2c, connected, nobody) => {
    const view = render(<App />);
    await waitFor(() =>
      expect(screen.getByTestId("language-" + code)).not.toBeDisabled(),
    );
    fireEvent.press(screen.getByTestId("language-" + code));
    await waitFor(() =>
      expect(AsyncStorage.setItem).toHaveBeenCalledWith(
        "aurora-elo.ui-language",
        code,
      ),
    );
    expect(
      screen.getByText(new RegExp(nobody.replace(".", "\\."))),
    ).toBeTruthy();
    expect(
      screen.queryByText(b2c) || screen.queryByText(connected),
    ).toBeTruthy();
    view.unmount();
    render(<App />);
    await waitFor(() =>
      expect(screen.getByTestId("language-" + code)).toHaveProp(
        "accessibilityState",
        expect.objectContaining({ selected: true, disabled: false }),
      ),
    );
    expect(
      screen.queryByText(b2c) || screen.queryByText(connected),
    ).toBeTruthy();
    expect(global.fetch).not.toHaveBeenCalled();
  },
);

test("não promete persistência quando armazenamento falha", async () => {
  jest.mocked(AsyncStorage.setItem).mockRejectedValueOnce(new Error("disk"));
  render(<App />);
  await waitFor(() =>
    expect(screen.getByTestId("language-en")).not.toBeDisabled(),
  );
  fireEvent.press(screen.getByTestId("language-en"));
  expect(await screen.findByText(/Could not save or restore/)).toBeTruthy();
});

beforeEach(async () => {
  await AsyncStorage.clear();
  jest.clearAllMocks();
  global.fetch = jest.fn();
});

test("abre recuperação Aurora Elo sem dados fictícios ou rede e IA fechada", async () => {
  render(<App />);
  expect(screen.getByText("Aurora Elo")).toBeTruthy();
  await waitFor(() =>
    expect(screen.getByTestId("language-pt-br")).not.toBeDisabled(),
  );
  expect(screen.getByText("Álcool e outras substâncias")).toBeTruthy();
  expect(screen.getByText("Apostas e jogos de azar")).toBeTruthy();
  expect(screen.getByText("Jogos digitais")).toBeTruthy();
  expect(
    screen.getByLabelText(
      "Avatar de inteligência artificial, não é uma pessoa",
    ),
  ).toBeTruthy();
  expect(screen.getByRole("switch")).toBeDisabled();
  expect(screen.getByRole("switch")).toHaveProp("value", false);
  expect(screen.getByTestId("ai-start")).toBeDisabled();
  fireEvent.press(screen.getByTestId("ai-start"));
  expect(global.fetch).not.toHaveBeenCalled();
  expect(AsyncStorage.setItem).not.toHaveBeenCalled();
  expect(screen.queryByText(/Mariana|Escitalopram|14 Dias|29,90/)).toBeNull();
});
