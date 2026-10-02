import React, { ReactElement } from "react";
import { act, render } from "@testing-library/react-native";
import { SafeAreaProvider } from "react-native-safe-area-context";
import { AppMode } from "../src/config";
import { StoreProvider } from "../src/data/store";
import { I18nProvider, Locale } from "../src/i18n";
import { RootNavigator } from "../src/navigation/RootNavigator";
import { ThemeProvider } from "../src/theme/ThemeProvider";

/** Instante fixo (hora local de Brasília): 2026-10-02 09:00. */
export const NOW = new Date(2026, 9, 2, 9, 0, 0);

interface Options {
  mode?: AppMode;
  locale?: Locale;
  scheme?: "light" | "dark";
  clock?: () => Date;
}

export function Providers({
  children,
  mode = "preview",
  locale = "pt-br",
  scheme = "light",
  clock = () => NOW,
}: Options & { children: ReactElement }) {
  return (
    <SafeAreaProvider>
      <ThemeProvider forcedScheme={scheme} fontsLoaded={false}>
        <I18nProvider initialLocale={locale}>
          <StoreProvider mode={mode} clock={clock}>
            {children}
          </StoreProvider>
        </I18nProvider>
      </ThemeProvider>
    </SafeAreaProvider>
  );
}

/** Deixa os temporizadores internos da navegação rodarem dentro de act(). */
export function flush(ms = 0) {
  act(() => {
    jest.advanceTimersByTime(ms);
    jest.runOnlyPendingTimers();
  });
}

export function renderApp(options: Options = {}) {
  const utils = render(
    <Providers {...options}>
      <RootNavigator />
    </Providers>,
  );
  flush();
  return utils;
}
