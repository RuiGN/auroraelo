import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";
import {
  darkColors,
  lightColors,
  designTypography,
} from "../src/theme/tokens.generated";
import {
  contrastRatio,
  resolveTextStyle,
  shadowStyle,
} from "../src/theme/tokens";

const pairs: [keyof typeof lightColors, keyof typeof lightColors][] = [
  ["ink", "surface"],
  ["ink", "surfaceRaised"],
  ["inkMuted", "surface"],
  ["inkMuted", "surfaceRaised"],
  ["inkMuted", "surfaceSunken"],
  ["primary", "surfaceRaised"],
  ["primary", "primarySoft"],
  ["onPrimary", "primary"],
  ["onDanger", "danger"],
  ["success", "successSoft"],
  ["warning", "warningSoft"],
  ["danger", "dangerSoft"],
  ["navInk", "navBg"],
  ["navInkMuted", "navBg"],
];

describe.each([
  ["claro", lightColors],
  ["escuro", darkColors],
])("contraste WCAG AA no tema %s", (_name, palette) => {
  it.each(pairs)("%s sobre %s tem razão ≥ 4,5:1", (foreground, background) => {
    expect(
      contrastRatio(palette[foreground], palette[background]),
    ).toBeGreaterThanOrEqual(4.5);
  });
});

describe("tokens gerados", () => {
  it("usam a marca do design system", () => {
    expect(lightColors.brandNavy).toBe("#0d3665");
    expect(lightColors.primary).toBe("#2072ab");
    expect(darkColors.primary).toBe("#58abdf");
    expect(lightColors.navBg).toBe("#0a2342");
  });

  it("resolvem variáveis (var(--x)) em hex", () => {
    for (const value of [
      ...Object.values(lightColors),
      ...Object.values(darkColors),
    ]) {
      expect(value).toMatch(/^#[0-9a-f]{6,8}$/i);
    }
    expect(lightColors.navAccent).toBe(lightColors.brandSky);
    expect(darkColors.focus).toBe(darkColors.primary);
  });

  it("não ficam defasados em relação ao CSS do design system (quando presente)", () => {
    const css = resolve(
      __dirname,
      "../../../../auroraelo_design_system/static/css/aurora-elo.css",
    );
    if (!existsSync(css)) return; // o design system fica fora do app; sem ele só validamos o gerado
    const source = readFileSync(css, "utf8");
    for (const hex of Object.values(lightColors))
      expect(source.toLowerCase()).toContain(hex.toLowerCase());
    for (const hex of Object.values(darkColors))
      expect(source.toLowerCase()).toContain(hex.toLowerCase());
  });
});

describe("tipografia", () => {
  it("traduz a escala do design system para React Native", () => {
    expect(designTypography.title1).toMatchObject({
      fontSize: 24,
      lineHeight: 32,
      fontWeight: 800,
    });
    const style = resolveTextStyle("title1", true);
    expect(style).toMatchObject({
      fontSize: 24,
      lineHeight: 32,
      fontFamily: "Manrope_800ExtraBold",
    });
    expect(style.letterSpacing).toBeCloseTo(-0.24, 2);
    expect(style.fontWeight).toBeUndefined();
  });

  it("cai para a fonte do sistema com o peso, sem misturar fontFamily", () => {
    const style = resolveTextStyle("body", false);
    expect(style.fontFamily).toBeUndefined();
    expect(style.fontWeight).toBe("500");
  });

  it("sombras ficam mais densas no escuro", () => {
    expect(shadowStyle("dark", "sm").shadowOpacity).toBeGreaterThan(
      shadowStyle("light", "sm").shadowOpacity,
    );
  });
});
