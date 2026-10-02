/**
 * Links profundos do app: `auroraelo-posalta://activate?code=…` (convite) e
 * `auroraelo-posalta://reset?code=…` (recuperação de senha), enviados por e-mail.
 *
 * O código é uma credencial de uso único. Por isso:
 * - nunca vai para log, parâmetro de navegação (na web viraria endereço/histórico)
 *   nem armazenamento: fica só em memória, em `pending`, até a tela de ativar ou
 *   redefinir preencher o campo (editável) e limpar;
 * - links com esquema, ação ou código fora do formato são ignorados;
 * - só valem sem sessão ativa (entrando, recuperando ou ativando).
 */
import React, {
  createContext,
  ReactNode,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { Linking } from "react-native";
import { useOptionalSession } from "./session";

/** Esquema registrado em app.json (`scheme`) e usado pelo backend (`MOBILE_APP_SCHEME`). */
export const APP_SCHEME = "auroraelo-posalta";

export type DeepLinkKind = "activate" | "reset";

export interface DeepLink {
  kind: DeepLinkKind;
  code: string;
}

/**
 * Letras, dígitos e `._~-`: cobre `token_urlsafe` do convite e o `uid.token` do
 * Django. Qualquer outro caractere descarta o link inteiro.
 */
const CODE = /^[A-Za-z0-9._~-]{1,256}$/;

const LINK = new RegExp(
  `^${APP_SCHEME}:(?://)?/*([a-z]+)/?(?:\\?([^#]*))?(?:#.*)?$`,
  "i",
);

/** Lê um link do app; `null` para qualquer outra coisa. Função pura, sem efeitos. */
export function parseDeepLink(url: string | null | undefined): DeepLink | null {
  if (typeof url !== "string" || url.length > 2048) return null;
  const match = LINK.exec(url.trim());
  if (!match) return null;
  const kind = match[1].toLowerCase();
  if (kind !== "activate" && kind !== "reset") return null;
  for (const pair of (match[2] ?? "").split("&")) {
    const separator = pair.indexOf("=");
    if (separator < 0) continue;
    let key: string;
    let value: string;
    try {
      key = decodeURIComponent(pair.slice(0, separator));
      value = decodeURIComponent(pair.slice(separator + 1));
    } catch {
      return null;
    }
    if (key !== "code") continue;
    const code = value.trim();
    return CODE.test(code) ? { kind, code } : null;
  }
  return null;
}

interface DeepLinkContextValue {
  /** Link recebido e ainda não usado por uma tela. */
  pending: DeepLink | null;
  clear: () => void;
}

const DeepLinkContext = createContext<DeepLinkContextValue | null>(null);

interface DeepLinkProviderProps {
  children: ReactNode;
}

export function DeepLinkProvider({ children }: DeepLinkProviderProps) {
  const session = useOptionalSession();
  const status = session?.status ?? "disabled";
  const accepting = status === "restoring" || status === "signedOut";
  const acceptingRef = useRef(accepting);
  acceptingRef.current = accepting;
  const [pending, setPending] = useState<DeepLink | null>(null);

  useEffect(() => {
    let alive = true;
    const accept = (url: string | null | undefined) => {
      const link = parseDeepLink(url);
      if (link && alive && acceptingRef.current) setPending(link);
    };
    // `Promise.resolve().then` também cobre uma implementação que lance de forma síncrona.
    Promise.resolve()
      .then(() => Linking.getInitialURL())
      .then(accept)
      .catch(() => undefined);
    const subscription = Linking.addEventListener("url", (event) =>
      accept(event.url),
    );
    return () => {
      alive = false;
      subscription.remove();
    };
  }, []);

  // Com sessão ativa (ou sem sessão no app) um código pendente não serve mais.
  useEffect(() => {
    if (!accepting) setPending(null);
  }, [accepting]);

  const clear = useCallback(() => setPending(null), []);
  const value = useMemo(() => ({ pending, clear }), [pending, clear]);
  return (
    <DeepLinkContext.Provider value={value}>
      {children}
    </DeepLinkContext.Provider>
  );
}

/** Link pendente e `clear`; sem provider devolve um valor vazio (telas isoladas). */
export function useDeepLinks(): DeepLinkContextValue {
  return (
    useContext(DeepLinkContext) ?? { pending: null, clear: () => undefined }
  );
}

/**
 * Entrega o código do link à tela (para preencher o campo) uma única vez e limpa o
 * pendente. O campo continua editável: o código é só um valor inicial.
 */
export function useDeepLinkCode(
  kind: DeepLinkKind,
  onCode: (code: string) => void,
): void {
  const { pending, clear } = useDeepLinks();
  const handler = useRef(onCode);
  handler.current = onCode;
  useEffect(() => {
    if (pending?.kind !== kind) return;
    handler.current(pending.code);
    clear();
  }, [pending, kind, clear]);
}
