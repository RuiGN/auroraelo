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
import AsyncStorage from "@react-native-async-storage/async-storage";
import { en } from "./en";
import { es } from "./es";
import { MessageKey, Messages, ptBr } from "./pt-br";

export type Locale = "pt-br" | "en" | "es";

/** Mesma chave dos apps b2c/connected: guarda somente a preferência de idioma. */
export const LANGUAGE_KEY = "aurora-elo.ui-language";

export const localeLabels: Record<Locale, string> = {
  "pt-br": "Português (Brasil)",
  en: "English",
  es: "Español",
};

export const catalogs: Record<Locale, Messages> = { "pt-br": ptBr, en, es };

const intlTags: Record<Locale, string> = {
  "pt-br": "pt-BR",
  en: "en-US",
  es: "es",
};

export function isLocale(value: unknown): value is Locale {
  return value === "pt-br" || value === "en" || value === "es";
}

type StripPlural<K extends string> = K extends `${infer Base}_one`
  ? Base
  : K extends `${infer Base}_other`
    ? Base
    : K;

/** Chave de tradução: chaves simples ou a base de um par `_one`/`_other`. */
export type TranslationKey = StripPlural<MessageKey>;

export type TranslationParams = Record<string, string | number>;

function pluralCategory(locale: Locale, count: number): "one" | "other" {
  try {
    return new Intl.PluralRules(intlTags[locale]).select(count) === "one"
      ? "one"
      : "other";
  } catch {
    return count === 1 ? "one" : "other";
  }
}

export function translate(
  locale: Locale,
  key: TranslationKey,
  params?: TranslationParams,
): string {
  const catalog = catalogs[locale] as Record<string, string>;
  let template = catalog[key];
  if (template === undefined && params && typeof params.count === "number") {
    const category = pluralCategory(locale, params.count);
    template = catalog[`${key}_${category}`] ?? catalog[`${key}_other`];
  }
  if (template === undefined) return key;
  if (!params) return template;
  return template.replace(/\{(\w+)\}/g, (match, name: string) =>
    name in params ? String(params[name]) : match,
  );
}

export type DateInput = string | Date;

function toDate(value: DateInput): Date {
  if (value instanceof Date) return value;
  // YYYY-MM-DD é data local; ISO com horário já carrega o fuso.
  if (/^\d{4}-\d{2}-\d{2}$/.test(value)) {
    const [year, month, day] = value.split("-").map(Number);
    return new Date(year, month - 1, day, 12, 0, 0, 0);
  }
  return new Date(value);
}

export interface I18n {
  locale: Locale;
  t: (key: TranslationKey, params?: TranslationParams) => string;
  busy: boolean;
  storageError: boolean;
  setLocale: (next: Locale) => Promise<void>;
  formatDate: (
    value: DateInput,
    style?: "short" | "long" | "weekday",
  ) => string;
  formatTime: (value: DateInput) => string;
  formatDateTime: (value: DateInput) => string;
  /** "Hoje", "Amanhã", "Ontem" ou a data curta. */
  relativeDay: (value: DateInput, now: Date) => string;
}

const I18nContext = createContext<I18n | null>(null);

interface I18nProviderProps {
  children: ReactNode;
  /** Idioma inicial para testes/capturas; ignora o valor salvo quando informado. */
  initialLocale?: Locale;
}

export function I18nProvider({ children, initialLocale }: I18nProviderProps) {
  const [locale, setLocaleState] = useState<Locale>(initialLocale ?? "pt-br");
  const [busy, setBusy] = useState(initialLocale === undefined);
  const [storageError, setStorageError] = useState(false);
  const writePending = useRef(false);

  useEffect(() => {
    if (initialLocale !== undefined) return undefined;
    let mounted = true;
    AsyncStorage.getItem(LANGUAGE_KEY)
      .then((value) => {
        if (mounted && isLocale(value)) setLocaleState(value);
      })
      .catch(() => {
        if (mounted) setStorageError(true);
      })
      .finally(() => {
        if (mounted) setBusy(false);
      });
    return () => {
      mounted = false;
    };
  }, [initialLocale]);

  const setLocale = useCallback(
    async (next: Locale) => {
      if (busy || writePending.current || !isLocale(next)) return;
      writePending.current = true;
      setLocaleState(next);
      setBusy(true);
      setStorageError(false);
      try {
        await AsyncStorage.setItem(LANGUAGE_KEY, next);
      } catch {
        setStorageError(true);
      } finally {
        writePending.current = false;
        setBusy(false);
      }
    },
    [busy],
  );

  const value = useMemo<I18n>(() => {
    const tag = intlTags[locale];
    const formatDate: I18n["formatDate"] = (input, style = "short") => {
      const date = toDate(input);
      if (Number.isNaN(date.getTime())) return "";
      const options: Intl.DateTimeFormatOptions =
        style === "long"
          ? { weekday: "long", day: "numeric", month: "long" }
          : style === "weekday"
            ? { weekday: "short", day: "numeric", month: "short" }
            : { day: "2-digit", month: "2-digit", year: "numeric" };
      return date.toLocaleDateString(tag, options);
    };
    const formatTime: I18n["formatTime"] = (input) => {
      const date = toDate(input);
      if (Number.isNaN(date.getTime())) return "";
      return date.toLocaleTimeString(tag, {
        hour: "2-digit",
        minute: "2-digit",
      });
    };
    return {
      locale,
      t: (key, params) => translate(locale, key, params),
      busy,
      storageError,
      setLocale,
      formatDate,
      formatTime,
      formatDateTime: (input) =>
        `${formatDate(input, "weekday")} • ${formatTime(input)}`,
      relativeDay: (input, now) => {
        const target = toDate(input);
        const startOf = (d: Date) =>
          new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime();
        const diff = Math.round((startOf(target) - startOf(now)) / 86_400_000);
        if (diff === 0) return translate(locale, "common.today");
        if (diff === 1) return translate(locale, "common.tomorrow");
        if (diff === -1) return translate(locale, "common.yesterday");
        return formatDate(input, "weekday");
      },
    };
  }, [locale, busy, storageError, setLocale]);

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n(): I18n {
  const i18n = useContext(I18nContext);
  if (!i18n) throw new Error("useI18n precisa estar dentro de I18nProvider.");
  return i18n;
}
