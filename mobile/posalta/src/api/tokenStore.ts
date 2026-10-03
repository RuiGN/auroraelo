/**
 * Armazenamento da sessão (par de tokens, expirações, id da sessão, clínica e
 * paciente).
 *
 * - iOS/Android: `expo-secure-store` (Keychain / Keystore), só neste aparelho
 *   (`WHEN_UNLOCKED_THIS_DEVICE_ONLY`: fora de backups e migrações).
 * - Web: SOMENTE memória. Nada persistente: recarregar a página encerra a sessão.
 * - NUNCA AsyncStorage: ele guarda só idioma e aparência.
 *
 * O cofre limita cada valor a 2048 bytes; por isso a sessão vai em duas chaves
 * (tokens e perfil). Leitura inválida ou incompleta conta como "sem sessão" e o que
 * sobrou é apagado. Erros do cofre nunca carregam o conteúdo.
 */
import { Platform } from "react-native";
import * as SecureStore from "expo-secure-store";
import { isRecord } from "./parse";
import { ClinicRef, PatientRef, StoredSession } from "./types";

export interface TokenStore {
  /** Sessão guardada, ou `null` (vazio, ilegível ou incompleto). Nunca rejeita. */
  load(): Promise<StoredSession | null>;
  /** Grava a sessão inteira. Rejeita se o cofre recusar. */
  save(session: StoredSession): Promise<void>;
  /** Apaga tudo. Nunca rejeita. */
  clear(): Promise<void>;
}

/** Chaves do cofre: só letras, dígitos, ".", "-" e "_" são aceitos. */
export const TOKENS_KEY = "aurora-elo.posalta.session.tokens";
export const PROFILE_KEY = "aurora-elo.posalta.session.profile";

function str(value: unknown, max: number): value is string {
  return typeof value === "string" && value.length > 0 && value.length <= max;
}

function stamp(value: unknown): value is string {
  return str(value, 64) && !Number.isNaN(Date.parse(value));
}

function parseSession(
  tokensRaw: string | null,
  profileRaw: string | null,
): StoredSession | null {
  if (tokensRaw === null || profileRaw === null) return null;
  try {
    const tokens: unknown = JSON.parse(tokensRaw);
    const profile: unknown = JSON.parse(profileRaw);
    if (!isRecord(tokens) || !isRecord(profile)) return null;
    const clinic = profile.clinic;
    const patient = profile.patient;
    if (!isRecord(clinic) || !isRecord(patient)) return null;
    if (
      !str(tokens.sessionId, 64) ||
      !str(tokens.accessToken, 256) ||
      !stamp(tokens.accessExpiresAt) ||
      !str(tokens.refreshToken, 256) ||
      !stamp(tokens.refreshExpiresAt) ||
      !str(clinic.id, 64) ||
      typeof clinic.name !== "string" ||
      !str(patient.id, 64) ||
      typeof patient.displayName !== "string"
    ) {
      return null;
    }
    const clinicRef: ClinicRef = {
      id: clinic.id,
      name: clinic.name.slice(0, 300),
    };
    const patientRef: PatientRef = {
      id: patient.id,
      displayName: patient.displayName.slice(0, 300),
    };
    return {
      sessionId: tokens.sessionId,
      accessToken: tokens.accessToken,
      accessExpiresAt: tokens.accessExpiresAt,
      refreshToken: tokens.refreshToken,
      refreshExpiresAt: tokens.refreshExpiresAt,
      clinic: clinicRef,
      patient: patientRef,
    };
  } catch {
    return null;
  }
}

/** Sessão só na memória do processo: web e testes. */
export function createMemoryTokenStore(): TokenStore {
  let current: StoredSession | null = null;
  return {
    async load() {
      return current;
    },
    async save(session) {
      current = { ...session };
    },
    async clear() {
      current = null;
    },
  };
}

type SecureStoreModule = Pick<
  typeof SecureStore,
  "getItemAsync" | "setItemAsync" | "deleteItemAsync"
>;

/** Cofre nativo. O módulo é injetável para testes. */
export function createSecureTokenStore(
  store: SecureStoreModule = SecureStore,
): TokenStore {
  const options = {
    keychainAccessible: SecureStore.WHEN_UNLOCKED_THIS_DEVICE_ONLY,
  };
  async function wipe() {
    // Cada apagamento é independente: uma falha não impede o outro.
    await Promise.allSettled([
      store.deleteItemAsync(TOKENS_KEY, options),
      store.deleteItemAsync(PROFILE_KEY, options),
    ]);
  }
  return {
    async load() {
      try {
        const [tokensRaw, profileRaw] = await Promise.all([
          store.getItemAsync(TOKENS_KEY, options),
          store.getItemAsync(PROFILE_KEY, options),
        ]);
        if (tokensRaw === null && profileRaw === null) return null;
        const session = parseSession(tokensRaw, profileRaw);
        if (session === null) await wipe();
        return session;
      } catch {
        return null;
      }
    },
    async save(session) {
      const tokens = JSON.stringify({
        sessionId: session.sessionId,
        accessToken: session.accessToken,
        accessExpiresAt: session.accessExpiresAt,
        refreshToken: session.refreshToken,
        refreshExpiresAt: session.refreshExpiresAt,
      });
      const profile = JSON.stringify({
        clinic: session.clinic,
        patient: session.patient,
      });
      try {
        // O perfil vai antes: sem os tokens a leitura seguinte já conta como vazia.
        await store.setItemAsync(PROFILE_KEY, profile, options);
        await store.setItemAsync(TOKENS_KEY, tokens, options);
      } catch {
        // Não repassa o erro original: ele poderia ecoar o valor.
        throw new Error("token_store_write_failed");
      }
    },
    clear: wipe,
  };
}

/** Nativo → cofre seguro; web → memória. */
export function createDefaultTokenStore(): TokenStore {
  return Platform.OS === "web"
    ? createMemoryTokenStore()
    : createSecureTokenStore();
}
