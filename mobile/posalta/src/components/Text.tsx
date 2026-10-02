import React from "react";
import { Text as RNText, TextProps as RNTextProps } from "react-native";
import { useTheme } from "../theme/ThemeProvider";
import { ColorTokens, TextVariant } from "../theme/tokens";

export type Tone =
  | "ink"
  | "muted"
  | "primary"
  | "success"
  | "warning"
  | "danger"
  | "onPrimary"
  | "onDanger"
  | "nav"
  | "navMuted";

const toneToken: Record<Tone, keyof ColorTokens> = {
  ink: "ink",
  muted: "inkMuted",
  primary: "primary",
  success: "success",
  warning: "warning",
  danger: "danger",
  onPrimary: "onPrimary",
  onDanger: "onDanger",
  nav: "navInk",
  navMuted: "navInkMuted",
};

export interface TextProps extends RNTextProps {
  variant?: TextVariant;
  tone?: Tone;
  /** Marca o texto como título para leitores de tela. */
  header?: boolean;
}

/** Texto com a escala tipográfica do design system (Manrope). */
export function Text({
  variant = "body",
  tone = "ink",
  header,
  style,
  ...rest
}: TextProps) {
  const theme = useTheme();
  return (
    <RNText
      accessibilityRole={header ? "header" : undefined}
      maxFontSizeMultiplier={1.6}
      style={[
        theme.text(variant),
        { color: theme.colors[toneToken[tone]] },
        style,
      ]}
      {...rest}
    />
  );
}
