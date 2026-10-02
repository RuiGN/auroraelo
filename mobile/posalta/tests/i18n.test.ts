import { catalogs, isLocale, Locale, translate } from "../src/i18n";
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
