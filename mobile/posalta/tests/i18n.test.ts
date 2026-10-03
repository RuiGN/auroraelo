import { catalogs, isLocale, Locale, translate } from "../src/i18n";
import {
  authFailureKey,
  ERROR_CODE_KEYS,
  errorCodeKey,
  errorMessageKey,
} from "../src/i18n/errorCodes";
import type { AuthFailureReason } from "../src/api/session";
import { ptBr } from "../src/i18n/pt-br";

const locales = Object.keys(catalogs) as Locale[];
const placeholders = (text: string) =>
  [...text.matchAll(/\{(\w+)\}/g)].map((m) => m[1]).sort();

describe("catálogos pt-br / en / es", () => {
  it("têm exatamente as mesmas chaves", () => {
    const base = Object.keys(ptBr).sort();
    for (const locale of locales) {
      expect(Object.keys(catalogs[locale]).sort()).toEqual(base);
    }
  });

  it("não têm textos vazios nem marcadores de pendência", () => {
    for (const locale of locales) {
      for (const value of Object.values(catalogs[locale])) {
        expect(value.trim()).not.toBe("");
        expect(value).not.toMatch(/\bTODO\b|FIXME|lorem ipsum/);
      }
    }
  });

  it("usam os mesmos {parâmetros} em todos os idiomas", () => {
    for (const [key, value] of Object.entries(ptBr)) {
      for (const locale of locales) {
        const translated = (catalogs[locale] as Record<string, string>)[key];
        expect({ key, locale, params: placeholders(translated) }).toEqual({
          key,
          locale,
          params: placeholders(value),
        });
      }
    }
  });

  it("todo plural tem as formas _one e _other", () => {
    const keys = Object.keys(ptBr);
    for (const key of keys.filter((k) => k.endsWith("_one"))) {
      expect(keys).toContain(key.replace(/_one$/, "_other"));
    }
    for (const key of keys.filter((k) => k.endsWith("_other"))) {
      expect(keys).toContain(key.replace(/_other$/, "_one"));
    }
  });

  it("en e es traduzem os textos longos (não repetem o português)", () => {
    for (const [key, value] of Object.entries(ptBr)) {
      if (value.length < 40) continue;
      expect({
        key,
        same: catalogs.en[key as keyof typeof ptBr] === value,
      }).toEqual({ key, same: false });
      expect({
        key,
        same: catalogs.es[key as keyof typeof ptBr] === value,
      }).toEqual({ key, same: false });
    }
  });

  it("a ajuda urgente deixa claro nos 3 idiomas que ninguém é avisado", () => {
    expect(translate("pt-br", "help.noOneNotified")).toMatch(
      /Ninguém foi notificado/,
    );
    expect(translate("en", "help.noOneNotified")).toMatch(
      /Nobody was notified/,
    );
    expect(translate("es", "help.noOneNotified")).toMatch(/no avisó a nadie/);
    for (const locale of locales) {
      expect(translate(locale, "help.disclaimer").length).toBeGreaterThan(80);
    }
  });
});

describe("translate", () => {
  it("interpola parâmetros", () => {
    expect(translate("pt-br", "home.greeting.morning", { name: "Alex" })).toBe(
      "Bom dia, Alex",
    );
    expect(translate("en", "home.greeting.evening", { name: "Alex" })).toBe(
      "Good evening, Alex",
    );
    expect(translate("es", "home.greeting.afternoon", { name: "Alex" })).toBe(
      "Buenas tardes, Alex",
    );
  });

  it("escolhe o plural conforme o idioma", () => {
    expect(translate("pt-br", "home.sinceDischarge", { count: 1 })).toBe(
      "Faz 1 dia desde a sua alta",
    );
    expect(translate("pt-br", "home.sinceDischarge", { count: 9 })).toBe(
      "Fazem 9 dias desde a sua alta",
    );
    expect(translate("en", "home.sinceDischarge", { count: 1 })).toBe(
      "It has been 1 day since your discharge",
    );
    expect(translate("en", "home.sinceDischarge", { count: 0 })).toBe(
      "It has been 0 days since your discharge",
    );
    expect(translate("es", "recovery.days", { count: 1 })).toBe("1 día");
    expect(translate("es", "recovery.days", { count: 3 })).toBe("3 días");
  });

  it("devolve a própria chave quando ela não existe e mantém {param} ausente", () => {
    expect(translate("pt-br", "inexistente" as never)).toBe("inexistente");
    expect(translate("en", "home.greeting.morning", {})).toBe(
      "Good morning, {name}",
    );
  });

  it("reconhece só os 3 idiomas suportados", () => {
    expect(isLocale("pt-br")).toBe(true);
    expect(isLocale("en")).toBe(true);
    expect(isLocale("es")).toBe(true);
    expect(isLocale("pt-BR")).toBe(false);
    expect(isLocale("fr")).toBe(false);
    expect(isLocale(null)).toBe(false);
  });
});

describe("mensagens por código de erro da API", () => {
  // Códigos de docs/mobile-patient-api.md (seção "Erros") e os do cliente HTTP.
  const serverCodes = [
    "invalid_credentials",
    "rate_limited",
    "clinic_choice_required",
    "invalid_token",
    "not_found",
    "invalid_dose_time",
    "timezone_required",
    "plan_closed",
    "invalid_date",
    "not_scheduled",
    "already_completed",
    "invalid_response",
    "unsupported",
    "no_actions_configured",
    "invalid_intensity",
    "invalid_scope",
    "reauthentication_failed",
    "consent_rejected",
    "revocation_rejected",
    "already_open",
    "rejected",
    "slot_unavailable",
    "weak_password",
    "invalid_code",
    "invalid_contact",
    "invalid_focus",
    "invalid_phone",
    "invalid_section_type",
    "already_exists",
    "limit_reached",
  ];
  const clientCodes = ["network", "timeout", "clinic_blocked", "rate_limited"];

  it("todo código do contrato e do cliente tem mensagem nos 3 idiomas", () => {
    for (const code of [...serverCodes, ...clientCodes]) {
      const key = errorCodeKey(code);
      expect({ code, key }).not.toEqual({ code, key: null });
      for (const locale of locales) {
        const text = translate(locale, key!);
        expect(text).not.toBe(key); // a chave existe no catálogo
        expect(text.trim().length).toBeGreaterThan(10);
      }
    }
  });

  it("código desconhecido (ou ausente) cai na mensagem genérica, nunca no detail", () => {
    expect(errorCodeKey("http_418")).toBeNull();
    expect(errorCodeKey(undefined)).toBeNull();
    expect(errorCodeKey("toString")).toBeNull(); // não herda de Object
    expect(errorMessageKey("http_418")).toBe("error.code.unknown");
    expect(errorMessageKey("invalid_credentials")).toBe(
      "error.code.invalid_credentials",
    );
  });

  it("todo motivo de falha de entrada tem texto", () => {
    const reasons: AuthFailureReason[] = [
      "invalid_credentials",
      "rate_limited",
      "offline",
      "invalid_code",
      "weak_password",
      "clinic_choice",
      "blocked",
      "unexpected",
    ];
    for (const reason of reasons) {
      const key = authFailureKey(reason);
      for (const locale of locales) {
        expect(translate(locale, key)).not.toBe(key);
      }
    }
  });

  it("as mensagens de erro não culpam a pessoa nem soam como alarme", () => {
    for (const locale of locales) {
      for (const key of Object.values(ERROR_CODE_KEYS)) {
        expect(translate(locale, key)).not.toMatch(
          /sua culpa|you failed|fracasso|falhou você|error fatal|fatal error/i,
        );
      }
    }
  });
});
