/**
 * Validação de respostas JSON. Todo corpo vindo do servidor é `unknown` até passar
 * por aqui; qualquer desvio vira `ApiError("malformed_response")` (nunca um
 * `TypeError` solto, e sem o conteúdo do corpo na mensagem).
 */
import { ApiError, CLIENT_CODES } from "./errors";

export function malformed(): never {
  throw new ApiError(0, CLIENT_CODES.malformedResponse);
}

export type Parser<T> = (value: unknown) => T;

export function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

export function record(value: unknown): Record<string, unknown> {
  return isRecord(value) ? value : malformed();
}

/** Texto obrigatório (aceita vazio); `max` limita o tamanho aceito. */
export function text(value: unknown, max = 2000): string {
  return typeof value === "string" && value.length <= max ? value : malformed();
}

/** Texto obrigatório e não vazio (tokens, nomes de exibição). */
export function nonEmptyText(value: unknown, max = 2000): string {
  const result = text(value, max);
  return result.trim().length > 0 ? result : malformed();
}

export function maybeText(value: unknown, max = 2000): string | null {
  return value === null || value === undefined ? null : text(value, max);
}

export function bool(value: unknown): boolean {
  return typeof value === "boolean" ? value : malformed();
}

export function int(value: unknown): number {
  return typeof value === "number" && Number.isInteger(value)
    ? value
    : malformed();
}

/** Identificador (UUID ou texto curto sem espaços). */
export function id(value: unknown): string {
  return typeof value === "string" && /^[A-Za-z0-9_-]{1,64}$/.test(value)
    ? value
    : malformed();
}

/** Instante ISO 8601 com fuso. */
export function isoDateTime(value: unknown): string {
  const raw = text(value, 64);
  return Number.isNaN(Date.parse(raw)) ? malformed() : raw;
}

/** Data AAAA-MM-DD. */
export function isoDate(value: unknown): string {
  const raw = text(value, 10);
  return /^\d{4}-\d{2}-\d{2}$/.test(raw) ? raw : malformed();
}

export function maybeIsoDate(value: unknown): string | null {
  return value === null || value === undefined ? null : isoDate(value);
}

export function list<T>(value: unknown, item: Parser<T>, max = 500): T[] {
  if (!Array.isArray(value) || value.length > max) return malformed();
  return value.map((entry) => item(entry));
}

/** Escolha em lista fechada; valor desconhecido cai em `fallback`. */
export function oneOf<T extends string>(
  value: unknown,
  allowed: readonly T[],
  fallback: T,
): T {
  return typeof value === "string" &&
    (allowed as readonly string[]).includes(value)
    ? (value as T)
    : fallback;
}
