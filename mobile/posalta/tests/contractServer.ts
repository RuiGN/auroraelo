/**
 * Servidor de contrato: um `Handler` do `createFakeServer` que responde pelo OpenAPI do
 * backend (`tests/fixtures/openapi-mobile.json`, gerado pelo Django e conferido por
 * `tests/test_mobile_api_openapi_snapshot.py`).
 *
 * - Leituras devolvem um exemplo gerado do esquema de resposta (ou o `override`).
 * - Toda gravação tem o corpo conferido contra o esquema de entrada; violações ficam em
 *   `violations` (os testes exigem lista vazia). Assim um loader com campo trocado ou
 *   uma ação com enum/limite errado quebra aqui, antes de chegar ao servidor real.
 */
import { FakeCall, FakeReply, Handler } from "./fakeApi";
import spec from "./fixtures/openapi-mobile.json";

type Json = Record<string, any>;
const SCHEMAS: Record<string, Json> = (spec as any).components.schemas;
const PATHS: Record<string, Json> = (spec as any).paths;

const UUID = "55555555-5555-4555-8555-555555555555";

/** Valores de exemplo para campos cujo formato o esquema não descreve. */
const EXAMPLES: Record<string, unknown> = {
  "MedicationOut.schedule_times": ["08:00", "20:00"],
  "HabitOut.target_time": "08:00",
  "HabitOut.time_window": "morning",
  "MedicationOut.route": "oral",
  "CarePlanOut.status": "active",
  "ExerciseOut.response_format": "text",
  "ExerciseOut.status": "assigned",
  "ExerciseOut.visibility": "private",
  "CheckInOut.date": "2026-10-02",
  "CheckInOut.answers": {
    general_state: 3,
    anxiety: 2,
    sadness: 2,
    irritability: 1,
    energy: 3,
    sleep_quality: 3,
    motivation: 3,
  },
};

export function deref(schema: Json | undefined): Json {
  if (!schema) return {};
  const ref = schema.$ref as string | undefined;
  if (ref) return deref(SCHEMAS[ref.split("/").pop() as string]);
  return schema;
}

function pad(text: string, min: number): string {
  let result = text;
  while (result.length < min) result += text;
  return result;
}

/** Exemplo válido do esquema (o primeiro valor do enum, 1 item por lista, etc.). */
export function sample(raw: Json | undefined, hint = ""): any {
  if (raw?.$ref) {
    const name = (raw.$ref as string).split("/").pop() as string;
    return sample(SCHEMAS[name], name);
  }
  const schema = raw ?? {};
  if (schema.anyOf) {
    const choice =
      schema.anyOf.find((option: Json) => option.type !== "null") ??
      schema.anyOf[0];
    return sample(choice, hint);
  }
  if (schema.enum) return schema.enum[0];
  if (schema.const !== undefined) return schema.const;
  switch (schema.type) {
    case "string": {
      if (schema.format === "uuid") return UUID;
      if (schema.format === "date-time") return "2026-10-02T12:00:00Z";
      if (schema.format === "date") return "2026-10-02";
      return pad("x", schema.minLength ?? 1);
    }
    case "integer":
    case "number": {
      const min = schema.minimum ?? schema.exclusiveMinimum;
      return min !== undefined ? Math.ceil(min) : 1;
    }
    case "boolean":
      return true;
    case "array":
      return [sample(schema.items, hint)];
    case "object":
    default: {
      if (schema.properties) {
        const out: Json = {};
        for (const [key, value] of Object.entries<Json>(schema.properties)) {
          const example = EXAMPLES[`${hint}.${key}`];
          out[key] =
            example !== undefined ? example : sample(value, `${hint}.${key}`);
        }
        return out;
      }
      if (schema.additionalProperties && schema.additionalProperties !== true) {
        return { chave: sample(schema.additionalProperties, hint) };
      }
      return {};
    }
  }
}

/** Confere `value` contra o esquema; devolve as violações (vazio = válido). */
export function validate(
  raw: Json | undefined,
  value: unknown,
  path = "$",
): string[] {
  const schema = deref(raw);
  if (schema.anyOf) {
    const attempts = schema.anyOf.map((option: Json) =>
      validate(option, value, path),
    );
    return attempts.some((errors: string[]) => errors.length === 0)
      ? []
      : [`${path}: nenhuma alternativa aceita ${JSON.stringify(value)}`];
  }
  if (schema.type === "null") {
    return value === null ? [] : [`${path}: esperado null`];
  }
  const errors: string[] = [];
  if (schema.enum && !schema.enum.includes(value)) {
    return [`${path}: ${JSON.stringify(value)} fora de ${schema.enum}`];
  }
  switch (schema.type) {
    case "string": {
      if (typeof value !== "string") return [`${path}: esperado texto`];
      if (schema.minLength !== undefined && value.length < schema.minLength) {
        errors.push(`${path}: menor que ${schema.minLength}`);
      }
      if (schema.maxLength !== undefined && value.length > schema.maxLength) {
        errors.push(`${path}: maior que ${schema.maxLength}`);
      }
      if (
        schema.format === "date-time" &&
        (Number.isNaN(Date.parse(value)) ||
          !/(Z|[+-]\d{2}:?\d{2})$/.test(value))
      ) {
        errors.push(`${path}: date-time precisa de fuso`);
      }
      if (schema.format === "date" && !/^\d{4}-\d{2}-\d{2}$/.test(value)) {
        errors.push(`${path}: date inválida`);
      }
      if (
        schema.format === "uuid" &&
        !/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(
          value,
        )
      ) {
        errors.push(`${path}: uuid inválido`);
      }
      return errors;
    }
    case "integer":
    case "number": {
      if (typeof value !== "number") return [`${path}: esperado número`];
      if (schema.type === "integer" && !Number.isInteger(value)) {
        errors.push(`${path}: esperado inteiro`);
      }
      if (schema.minimum !== undefined && value < schema.minimum) {
        errors.push(`${path}: menor que ${schema.minimum}`);
      }
      if (schema.maximum !== undefined && value > schema.maximum) {
        errors.push(`${path}: maior que ${schema.maximum}`);
      }
      return errors;
    }
    case "boolean":
      return typeof value === "boolean" ? [] : [`${path}: esperado booleano`];
    case "array": {
      if (!Array.isArray(value)) return [`${path}: esperado lista`];
      if (schema.maxItems !== undefined && value.length > schema.maxItems) {
        errors.push(`${path}: mais de ${schema.maxItems} itens`);
      }
      if (schema.minItems !== undefined && value.length < schema.minItems) {
        errors.push(`${path}: menos de ${schema.minItems} itens`);
      }
      value.forEach((item, index) =>
        errors.push(...validate(schema.items, item, `${path}[${index}]`)),
      );
      return errors;
    }
    default: {
      if (typeof value !== "object" || value === null || Array.isArray(value)) {
        return [`${path}: esperado objeto`];
      }
      const body = value as Json;
      const props: Json = schema.properties ?? {};
      for (const key of schema.required ?? []) {
        if (!(key in body)) errors.push(`${path}.${key}: obrigatório ausente`);
      }
      for (const [key, item] of Object.entries(body)) {
        if (key in props) {
          errors.push(...validate(props[key], item, `${path}.${key}`));
        } else if (
          schema.additionalProperties &&
          typeof schema.additionalProperties === "object"
        ) {
          errors.push(
            ...validate(schema.additionalProperties, item, `${path}.${key}`),
          );
        } else if (Object.keys(props).length > 0) {
          errors.push(`${path}.${key}: campo desconhecido`);
        }
      }
      return errors;
    }
  }
}

interface Operation {
  method: string;
  template: string;
  regex: RegExp;
  op: Json;
}

const OPERATIONS: Operation[] = [];
for (const [template, methods] of Object.entries(PATHS)) {
  for (const [method, op] of Object.entries<Json>(methods)) {
    const local = template.replace(/^\/api\/v1/, "");
    const regex = new RegExp(
      "^" + local.replace(/\{[^}]+\}/g, "([^/]+)") + "$",
    );
    OPERATIONS.push({
      method: method.toUpperCase(),
      template: local,
      regex,
      op,
    });
  }
}

export function findOperation(method: string, path: string) {
  return OPERATIONS.find(
    (item) => item.method === method && item.regex.test(path),
  );
}

export type Override =
  | unknown
  | ((call: FakeCall, params: string[]) => FakeReply | unknown);

export interface ContractServerOptions {
  /** Respostas específicas por "METODO /caminho/{template}/" ou caminho concreto. */
  overrides?: Record<string, Override>;
}

export interface ContractServer {
  handler: Handler;
  /** Violações do contrato vistas até agora (corpo de entrada, rota inexistente…). */
  violations: string[];
}

export function createContractServer(
  options: ContractServerOptions = {},
): ContractServer {
  const violations: string[] = [];
  const handler: Handler = (call) => {
    const found = findOperation(call.method, call.path);
    if (!found) {
      violations.push(`${call.method} ${call.path}: rota fora do contrato`);
      return { status: 404, body: { detail: "x", code: "not_found" } };
    }
    const { op, template } = found;
    const params = (call.path.match(found.regex) ?? []).slice(1);
    // Corpo de entrada
    const requestSchema = op.requestBody?.content?.["application/json"]?.schema;
    if (requestSchema) {
      for (const error of validate(requestSchema, call.body)) {
        violations.push(`${call.method} ${template}: ${error}`);
      }
    } else if (call.body !== undefined) {
      violations.push(`${call.method} ${template}: corpo não esperado`);
    }
    // Parâmetros de caminho como UUID/data conforme o contrato
    (op.parameters ?? [])
      .filter((p: Json) => p.in === "path")
      .forEach((p: Json, index: number) => {
        for (const error of validate(p.schema, params[index], `{${p.name}}`)) {
          violations.push(`${call.method} ${template}: ${error}`);
        }
      });
    // Resposta
    const override =
      options.overrides?.[`${call.method} ${template}`] ??
      options.overrides?.[`${call.method} ${call.path}`];
    if (override !== undefined) {
      const value =
        typeof override === "function"
          ? (override as Function)(call, params)
          : override;
      if (
        value &&
        typeof value === "object" &&
        typeof (value as { status?: unknown }).status === "number"
      ) {
        return value as FakeReply;
      }
      return { status: 200, body: value };
    }
    const success = Object.entries<Json>(op.responses ?? {}).find(([code]) =>
      /^2\d\d$/.test(code),
    );
    if (!success) return { status: 204 };
    const [code, response] = success;
    const schema = response.content?.["application/json"]?.schema;
    return schema
      ? { status: Number(code), body: sample(schema) }
      : { status: Number(code) };
  };
  return { handler, violations };
}
