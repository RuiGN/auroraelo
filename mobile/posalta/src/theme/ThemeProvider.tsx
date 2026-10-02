import React, {
  createContext,
  ReactNode,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import { useColorScheme } from "react-native";
import AsyncStorage from "@react-native-async-storage/async-storage";
import {
  ColorTokens,
  darkColors,
  lightColors,
  resolveTextStyle,
  ResolvedTextStyle,
  shadowStyle,
  TextVariant,
} from "./tokens";

export type ThemePreference = "system" | "light" | "dark";
export const THEME_KEY = "aurora-elo.posalta.theme";

export function isThemePreference(value: unknown): value is ThemePreference {
  return value === "system" || value === "light" || value === "dark";
}

export interface Theme {
  colors: ColorTokens;
  scheme: "light" | "dark";
  preference: ThemePreference;
  setPreference: (next: ThemePreference) => void;
  text: (variant: TextVariant) => ResolvedTextStyle;
  shadow: (level: "sm" | "md") => ReturnType<typeof shadowStyle>;
  fontsLoaded: boolean;
  storageError: boolean;
}

const ThemeContext = createContext<Theme | null>(null);

interface ThemeProviderProps {
  children: ReactNode;
  fontsLoaded?: boolean;
  /** Para testes e capturas: ignora o esquema do sistema. */
  forcedScheme?: "light" | "dark";
}

/**
 * Tema Aurora Elo (claro/escuro). Persiste somente a preferência de aparência;
 * nada clínico é gravado no aparelho.
 */
export function ThemeProvider({
  children,
  fontsLoaded = false,
  forcedScheme,
}: ThemeProviderProps) {
  const systemScheme = useColorScheme();
  const [preference, setPreferenceState] = useState<ThemePreference>("system");
  const [storageError, setStorageError] = useState(false);

  useEffect(() => {
    let mounted = true;
    AsyncStorage.getItem(THEME_KEY)
      .then((value) => {
        if (mounted && isThemePreference(value)) setPreferenceState(value);
      })
      .catch(() => {
        if (mounted) setStorageError(true);
      });
    return () => {
      mounted = false;
    };
  }, []);

  const setPreference = useCallback((next: ThemePreference) => {
    if (!isThemePreference(next)) return;
    setPreferenceState(next);
    setStorageError(false);
    AsyncStorage.setItem(THEME_KEY, next).catch(() => setStorageError(true));
  }, []);

  const scheme: "light" | "dark" =
    forcedScheme ??
    (preference === "system"
      ? systemScheme === "dark"
        ? "dark"
        : "light"
      : preference);

  const value = useMemo<Theme>(
    () => ({
      colors: scheme === "dark" ? darkColors : lightColors,
      scheme,
      preference,
      setPreference,
      text: (variant) => resolveTextStyle(variant, fontsLoaded),
      shadow: (level) => shadowStyle(scheme, level),
      fontsLoaded,
      storageError,
    }),
    [scheme, preference, setPreference, fontsLoaded, storageError],
  );

  return (
    <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
  );
}

export function useTheme(): Theme {
  const theme = useContext(ThemeContext);
  if (!theme)
    throw new Error("useTheme precisa estar dentro de ThemeProvider.");
  return theme;
}
