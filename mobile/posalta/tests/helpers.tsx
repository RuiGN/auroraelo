import React, { ReactElement } from "react";
import { act, render } from "@testing-library/react-native";
import { SafeAreaProvider } from "react-native-safe-area-context";
import { Transport } from "../src/api/client";
import { DeepLinkProvider } from "../src/api/deepLinks";
import { SessionProvider } from "../src/api/session";
import { createMemoryTokenStore, TokenStore } from "../src/api/tokenStore";
import { AppMode } from "../src/config";
import { LiveActionRegistry } from "../src/data/live/actions";
import { LoaderEntry } from "../src/data/live/registry";
import { StoreProvider } from "../src/data/store";
import { I18nProvider, Locale } from "../src/i18n";
import { RootNavigator } from "../src/navigation/RootNavigator";
import { ThemeProvider } from "../src/theme/ThemeProvider";
import { BASE_URL, storedSession } from "./fakeApi";

/** Instante fixo (hora local de Brasília): 2026-10-02 09:00. */
export const NOW = new Date(2026, 9, 2, 9, 0, 0);

export interface Options {
  mode?: AppMode;
  locale?: Locale;
  scheme?: "light" | "dark";
  clock?: () => Date;
  /** Live: transporte do servidor falso. Sem ele o app fica "sem configuração". */
  transport?: Transport;
  /** Live: endereço do servidor (padrão: `BASE_URL` se houver transporte). */
  baseUrl?: string | null;
  /** Live: começa com uma sessão guardada no cofre (em memória). */
  signedIn?: boolean;
  tokenStore?: TokenStore;
  /** Live: registros de loaders e ações do store (padrão: os reais). */
  loaders?: readonly LoaderEntry[];
  actions?: LiveActionRegistry;
}

export function Providers({
  children,
  mode = "preview",
  locale = "pt-br",
  scheme = "light",
  clock = () => NOW,
  transport,
  baseUrl,
  signedIn = false,
  tokenStore,
  loaders,
  actions,
}: Options & { children: ReactElement }) {
  // Lido só na primeira montagem, como o próprio SessionProvider.
  const [store] = React.useState<TokenStore>(() => {
    if (tokenStore) return tokenStore;
    const memory = createMemoryTokenStore();
    if (signedIn) void memory.save(storedSession(1));
    return memory;
  });
  return (
    <SafeAreaProvider>
      <ThemeProvider forcedScheme={scheme} fontsLoaded={false}>
        <I18nProvider initialLocale={locale}>
          <SessionProvider
            mode={mode}
            baseUrl={baseUrl === undefined && transport ? BASE_URL : baseUrl}
            transport={transport}
            tokenStore={store}
            device={() => ({
              deviceLabel: "iPhone",
              platform: "ios",
              appVersion: "1.0.0",
            })}
          >
            <DeepLinkProvider>
              <StoreProvider
                mode={mode}
                clock={clock}
                loaders={loaders}
                actions={actions}
              >
                {children}
              </StoreProvider>
            </DeepLinkProvider>
          </SessionProvider>
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

/**
 * Como `flush`, e ainda deixa as promessas pendentes (gravações, requisições) terminarem
 * dentro de act(): sem isso o React avisa de atualizações fora de act().
 */
export async function settle(ms = 0) {
  await act(async () => {
    await jest.advanceTimersByTimeAsync(ms);
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
