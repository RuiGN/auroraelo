import { ClinicRef } from "./errors";
import {
  bool,
  id,
  isoDateTime,
  list,
  nonEmptyText,
  Parser,
  record,
  text,
} from "./parse";

export type { ClinicRef };

export interface PatientRef {
  id: string;
  displayName: string;
}

/**
 * Sessão do aparelho como guardada no cofre seguro. Contém os dois tokens: nunca
 * entra em estado do React, em log, em mensagem de erro nem em AsyncStorage.
 */
export interface StoredSession {
  sessionId: string;
  accessToken: string;
  accessExpiresAt: string;
  refreshToken: string;
  refreshExpiresAt: string;
  clinic: ClinicRef;
  patient: PatientRef;
}

/** O que o app pode mostrar/guardar em estado sobre a sessão (sem tokens). */
export interface SessionInfo {
  sessionId: string;
  clinic: ClinicRef;
  patient: PatientRef;
}

export function sessionInfo(session: StoredSession): SessionInfo {
  return {
    sessionId: session.sessionId,
    clinic: session.clinic,
    patient: session.patient,
  };
}

export interface DeviceSession {
  id: string;
  deviceLabel: string;
  platform: string;
  appVersion: string;
  createdAt: string;
  lastUsedAt: string;
  isCurrent: boolean;
}

export const parseClinicRef: Parser<ClinicRef> = (value) => {
  const source = record(value);
  return { id: id(source.id), name: text(source.name, 300) };
};

/** `TokensOut` de /mobile/auth/login|activate|refresh/ → sessão do aparelho. */
export const parseTokens: Parser<StoredSession> = (value) => {
  const source = record(value);
  const patient = record(source.patient);
  return {
    sessionId: id(source.session_id),
    accessToken: nonEmptyText(source.access_token, 256),
    accessExpiresAt: isoDateTime(source.access_expires_at),
    refreshToken: nonEmptyText(source.refresh_token, 256),
    refreshExpiresAt: isoDateTime(source.refresh_expires_at),
    clinic: parseClinicRef(source.clinic),
    patient: {
      id: id(patient.id),
      displayName: text(patient.display_name, 300),
    },
  };
};

export const parseDeviceSessions: Parser<DeviceSession[]> = (value) =>
  list(value, (entry) => {
    const source = record(entry);
    return {
      id: id(source.id),
      deviceLabel: text(source.device_label, 500),
      platform: text(source.platform, 16),
      appVersion: text(source.app_version, 100),
      createdAt: isoDateTime(source.created_at),
      lastUsedAt: isoDateTime(source.last_used_at),
      isCurrent: bool(source.is_current),
    };
  });
