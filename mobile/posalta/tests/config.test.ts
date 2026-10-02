import { readFileSync } from "node:fs";
import { join } from "node:path";
import { API_BASE_URL, IS_DEV, resolveApiBaseUrl } from "../src/config";

describe("resolveApiBaseUrl", () => {
  it("aceita https com host DNS e devolve a origem normalizada", () => {
    expect(resolveApiBaseUrl("https://api.auroraelo.med.br", false)).toBe(
      "https://api.auroraelo.med.br",
    );
    expect(resolveApiBaseUrl("  https://API.Auroraelo.med.br/  ", false)).toBe(
      "https://api.auroraelo.med.br",
    );
    expect(resolveApiBaseUrl("https://api.auroraelo.med.br:8443", false)).toBe(
      "https://api.auroraelo.med.br:8443",
    );
  });

  it("omite a porta padrão (a URL da resposta vem sem ela)", () => {
    expect(resolveApiBaseUrl("https://api.auroraelo.med.br:443", false)).toBe(
      "https://api.auroraelo.med.br",
    );
    expect(resolveApiBaseUrl("http://localhost:80", true)).toBe(
      "http://localhost",
    );
  });

  it("http só em localhost, 127.0.0.1 e 10.0.2.2, e só em desenvolvimento", () => {
    for (const host of ["localhost", "127.0.0.1", "10.0.2.2"]) {
      expect(resolveApiBaseUrl(`http://${host}:8000`, true)).toBe(
        `http://${host}:8000`,
      );
      expect(resolveApiBaseUrl(`http://${host}:8000`, false)).toBeNull();
    }
    expect(resolveApiBaseUrl("http://api.auroraelo.med.br", true)).toBeNull();
    expect(resolveApiBaseUrl("http://192.168.0.10:8000", true)).toBeNull();
    expect(resolveApiBaseUrl("http://evil.localhost", true)).toBeNull();
  });

  it("https para IP só nos hosts de desenvolvimento", () => {
    expect(resolveApiBaseUrl("https://10.0.0.5", true)).toBeNull();
    expect(resolveApiBaseUrl("https://127.0.0.1:8443", false)).toBe(
      "https://127.0.0.1:8443",
    );
  });

  it("https sem ponto só vale para localhost", () => {
    expect(resolveApiBaseUrl("https://intranet", false)).toBeNull();
    expect(resolveApiBaseUrl("https://localhost:8443", false)).toBe(
      "https://localhost:8443",
    );
  });

  it.each([
    undefined,
    null,
    "",
    "   ",
    "api.auroraelo.med.br",
    "ftp://api.auroraelo.med.br",
    "https://",
    "https://user:senha@api.auroraelo.med.br",
    "https://api.auroraelo.med.br/api/v1",
    "https://api.auroraelo.med.br/?x=1",
    "https://api.auroraelo.med.br#frag",
    "https://api.auroraelo.med.br:0",
    "https://api.auroraelo.med.br:70000",
    "https://api.auroraelo.med.br:abc",
    "https://exemplo.com\\@evil.com",
    "https://exemplo..com",
    "https://-exemplo.com",
    "https://exémplo.com",
    "javascript:alert(1)",
  ])("recusa %p", (raw) => {
    expect(
      resolveApiBaseUrl(raw as string | null | undefined, true),
    ).toBeNull();
  });
});

describe("API_BASE_URL (variável pública do Expo)", () => {
  // O Expo troca `process.env.EXPO_PUBLIC_*` por um literal em tempo de compilação, e
  // só quando a referência é literal: acesso dinâmico (`process.env[nome]`) não funciona.
  const source = readFileSync(join(__dirname, "../src/config.ts"), "utf8");

  it("usa a referência literal e nunca acesso dinâmico a process.env", () => {
    expect(source).toContain("process.env.EXPO_PUBLIC_API_BASE_URL");
    expect(source).toContain("process.env.EXPO_PUBLIC_APP_MODE");
    expect(source).not.toMatch(/process\.env\[/);
    expect(source).not.toMatch(/const\s*\{[^}]*\}\s*=\s*process\.env/);
  });

  it("sem a variável no Jest o endereço é nulo (o app mostra 'sem configuração')", () => {
    expect(API_BASE_URL).toBeNull();
  });

  it("o ambiente de teste roda com __DEV__ (http em localhost só vale assim)", () => {
    expect(IS_DEV).toBe(true);
  });
});
