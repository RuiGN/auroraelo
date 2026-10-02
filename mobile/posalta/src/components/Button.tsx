import React from "react";
import {
  ActivityIndicator,
  Pressable,
  StyleProp,
  StyleSheet,
  View,
  ViewStyle,
} from "react-native";
import { useTheme } from "../theme/ThemeProvider";
import { CONTROL_HEIGHT, radius, TOUCH_TARGET } from "../theme/tokens";
import { Icon, IconName } from "./Icon";
import { Text } from "./Text";

export type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";

interface ButtonProps {
  label: string;
  onPress?: () => void;
  variant?: ButtonVariant;
  icon?: IconName;
  size?: "md" | "sm";
  disabled?: boolean;
  loading?: boolean;
  fullWidth?: boolean;
  accessibilityHint?: string;
  accessibilityLabel?: string;
  testID?: string;
  style?: StyleProp<ViewStyle>;
}

/** Botão do design system Aurora Elo (altura mínima de 48 px; 44 px no tamanho sm). */
export function Button({
  label,
  onPress,
  variant = "primary",
  icon,
  size = "md",
  disabled = false,
  loading = false,
  fullWidth = false,
  accessibilityHint,
  accessibilityLabel,
  testID,
  style,
}: ButtonProps) {
  const { colors } = useTheme();
  const palette = {
    primary: {
      bg: colors.primary,
      border: colors.primary,
      fg: colors.onPrimary,
    },
    secondary: {
      bg: colors.surfaceRaised,
      border: colors.lineStrong,
      fg: colors.ink,
    },
    ghost: { bg: "transparent", border: "transparent", fg: colors.primary },
    danger: { bg: colors.danger, border: colors.danger, fg: colors.onDanger },
  }[variant];
  const inactive = disabled || loading;
  return (
    <Pressable
      testID={testID}
      accessibilityRole="button"
      accessibilityLabel={accessibilityLabel ?? label}
      accessibilityHint={accessibilityHint}
      accessibilityState={{ disabled: inactive, busy: loading }}
      disabled={inactive}
      onPress={onPress}
      style={({ pressed }) => [
        styles.base,
        {
          minHeight: size === "md" ? CONTROL_HEIGHT : TOUCH_TARGET,
          backgroundColor:
            pressed && variant === "primary" ? colors.primaryHover : palette.bg,
          borderColor: palette.border,
          opacity: inactive ? 0.5 : pressed ? 0.92 : 1,
        },
        fullWidth && styles.full,
        style,
      ]}
    >
      <View style={styles.content}>
        {loading ? (
          <ActivityIndicator color={palette.fg} />
        ) : icon ? (
          <Icon name={icon} size={18} color={palette.fg} />
        ) : null}
        <Text
          variant="label"
          style={[styles.label, { color: palette.fg }]}
          numberOfLines={2}
        >
          {label}
        </Text>
      </View>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  base: {
    borderWidth: 1,
    borderRadius: radius.md,
    paddingHorizontal: 16,
    paddingVertical: 8,
    justifyContent: "center",
    alignItems: "center",
  },
  full: { alignSelf: "stretch" },
  content: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
  },
  label: { fontSize: 14, lineHeight: 18, textAlign: "center", flexShrink: 1 },
});
