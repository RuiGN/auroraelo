import {
  ColorTokens,
  darkColors,
  designTypography,
  lightColors,
  radius,
  space,
} from "./tokens.generated";

export { darkColors, lightColors, radius, space };
export type { ColorTokens };

/** Tamanho mínimo de qualquer alvo de toque (design system: --touch-target). */
export const TOUCH_TARGET = 44;
/** Altura de controles primários no mobile (maior que os 40px da web). */
export const CONTROL_HEIGHT = 48;
/** Largura máxima do conteúdo em telas largas (tablet/web). */
export const CONTENT_MAX_WIDTH = 640;

export type TextVariant = keyof typeof designTypography;

type Weight = 500 | 600 | 700 | 800;

/** Famílias Manrope carregadas via @expo-google-fonts/manrope. */
export const fontFamilyByWeight: Record<Weight, string> = {
  500: "Manrope_500Medium",
  600: "Manrope_600SemiBold",
  700: "Manrope_700Bold",
  800: "Manrope_800ExtraBold",
};

const systemWeight: Record<Weight, "500" | "600" | "700" | "800"> = {
  500: "500",
  600: "600",
  700: "700",
  800: "800",
};

export interface ResolvedTextStyle {
  fontSize: number;
  lineHeight: number;
  letterSpacing: number;
  fontFamily?: string;
  fontWeight?: "500" | "600" | "700" | "800";
}

/**
 * Converte um estilo de texto do design system em estilo React Native.
 * Com Manrope carregada usa só `fontFamily`; sem ela, cai para a fonte do sistema
 * preservando o peso (não combinamos `fontWeight` com família personalizada).
 */
export function resolveTextStyle(
  variant: TextVariant,
  fontsLoaded: boolean,
): ResolvedTextStyle {
  const base = designTypography[variant];
  const weight = base.fontWeight as Weight;
  const common = {
    fontSize: base.fontSize,
    lineHeight: base.lineHeight,
    letterSpacing: Number((base.letterSpacingEm * base.fontSize).toFixed(2)),
  };
  return fontsLoaded
    ? { ...common, fontFamily: fontFamilyByWeight[weight] }
    : { ...common, fontWeight: systemWeight[weight] };
}

/** Sombras do design system traduzidas para propriedades nativas. */
export function shadowStyle(scheme: "light" | "dark", level: "sm" | "md") {
  const opacity =
    scheme === "dark"
      ? level === "sm"
        ? 0.6
        : 0.7
      : level === "sm"
        ? 0.08
        : 0.16;
  return {
    shadowColor: scheme === "dark" ? "#000000" : "#0c2440",
    shadowOpacity: opacity,
    shadowRadius: level === "sm" ? 3 : 14,
    shadowOffset: { width: 0, height: level === "sm" ? 1 : 6 },
    elevation: level === "sm" ? 1 : 6,
  };
}

/** Razão de contraste WCAG entre duas cores #rrggbb. */
export function contrastRatio(foreground: string, background: string): number {
  const luminance = (hex: string) => {
    const channels = [1, 3, 5].map((index) => {
      const value = parseInt(hex.slice(index, index + 2), 16) / 255;
      return value <= 0.03928
        ? value / 12.92
        : ((value + 0.055) / 1.055) ** 2.4;
    });
    return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2];
  };
  const [light, dark] = [luminance(foreground), luminance(background)].sort(
    (a, b) => b - a,
  );
  return (light + 0.05) / (dark + 0.05);
}
