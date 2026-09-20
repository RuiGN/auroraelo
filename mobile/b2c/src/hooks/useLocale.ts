import { useEffect, useRef, useState } from "react";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { catalogs, isLocale, LANGUAGE_KEY, Locale } from "../../../shared/i18n";

// Somente preferência de UI. Nunca tokens, relatos ou consentimento clínico.
export function useLocale() {
  const [locale, setLocale] = useState<Locale>("pt-br");
  const [busy, setBusy] = useState(true);
  const [storageError, setStorageError] = useState(false);
  const writePending = useRef(false);
  useEffect(() => {
    let mounted = true;
    AsyncStorage.getItem(LANGUAGE_KEY)
      .then((value) => {
        if (mounted && isLocale(value)) setLocale(value);
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
  }, []);

  async function selectLocale(next: Locale) {
    if (busy || writePending.current || !isLocale(next)) return;
    writePending.current = true;
    setLocale(next);
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
  }
  return { t: catalogs[locale], locale, busy, storageError, selectLocale };
}
