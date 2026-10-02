import React, { ReactNode } from "react";
import {
  Pressable,
  StyleProp,
  StyleSheet,
  View,
  ViewStyle,
} from "react-native";
import { useTheme } from "../theme/ThemeProvider";
import { radius } from "../theme/tokens";
import { Icon, IconName } from "./Icon";
import { Text, Tone } from "./Text";

interface CardProps {
  children: ReactNode;
  onPress?: () => void;
  accessibilityLabel?: string;
  accessibilityHint?: string;
  testID?: string;
  style?: StyleProp<ViewStyle>;
  /** Realça o cartão com a cor de um estado (ex.: pendência). */
  tone?: "default" | "primary" | "warning" | "danger" | "success";
}

/** Superfície elevada do design system: fundo raised, borda 1 px e raio 16. */
export function Card({
  children,
  onPress,
  accessibilityLabel,
  accessibilityHint,
  testID,
  style,
  tone = "default",
}: CardProps) {
  const theme = useTheme();
  const { colors } = theme;
  const toneBackground = {
    default: colors.surfaceRaised,
    primary: colors.primarySoft,
    warning: colors.warningSoft,
    danger: colors.dangerSoft,
    success: colors.successSoft,
  }[tone];
  const base = [
    styles.card,
    theme.shadow("sm"),
    { backgroundColor: toneBackground, borderColor: colors.line },
    style,
  ];
  if (!onPress) {
    return (
      <View testID={testID} style={base}>
        {children}
      </View>
    );
  }
  return (
    <Pressable
      testID={testID}
      accessibilityRole="button"
      accessibilityLabel={accessibilityLabel}
      accessibilityHint={accessibilityHint}
      onPress={onPress}
      style={({ pressed }) => [base, pressed && { opacity: 0.9 }]}
    >
      {children}
    </Pressable>
  );
}

interface IconTileProps {
  name: IconName;
  tone?: "primary" | "success" | "warning" | "danger";
  size?: number;
}

/** Quadrado arredondado com ícone (mesmo padrão de `.ae-dropdown__icon`). */
export function IconTile({ name, tone = "primary", size = 36 }: IconTileProps) {
  const { colors } = useTheme();
  const palette = {
    primary: { bg: colors.primarySoft, fg: colors.primary },
    success: { bg: colors.successSoft, fg: colors.success },
    warning: { bg: colors.warningSoft, fg: colors.warning },
    danger: { bg: colors.dangerSoft, fg: colors.danger },
  }[tone];
  return (
    <View
      style={{
        width: size,
        height: size,
        borderRadius: radius.md,
        backgroundColor: palette.bg,
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      <Icon name={name} size={Math.round(size * 0.55)} color={palette.fg} />
    </View>
  );
}

interface ListRowProps {
  icon?: IconName;
  iconTone?: "primary" | "success" | "warning" | "danger";
  title: string;
  subtitle?: string;
  trailing?: ReactNode;
  /** Selo de estado exibido sob o texto (não disputa largura com o título). */
  badge?: ReactNode;
  onPress?: () => void;
  accessibilityHint?: string;
  testID?: string;
}

/** Linha de lista com ícone, título, apoio e seta; alvo de toque mínimo de 56 px. */
export function ListRow({
  icon,
  iconTone,
  title,
  subtitle,
  trailing,
  badge,
  onPress,
  accessibilityHint,
  testID,
}: ListRowProps) {
  const { colors } = useTheme();
  const content = (
    <View style={styles.row}>
      {icon ? <IconTile name={icon} tone={iconTone} /> : null}
      <View style={styles.rowText}>
        <Text variant="title3">{title}</Text>
        {subtitle ? (
          <Text variant="bodySm" tone="muted">
            {subtitle}
          </Text>
        ) : null}
        {badge ? <View style={styles.rowBadge}>{badge}</View> : null}
      </View>
      {trailing ??
        (onPress ? (
          <Icon name="chevron-right" size={18} color={colors.inkMuted} />
        ) : null)}
    </View>
  );
  if (!onPress) return <View testID={testID}>{content}</View>;
  return (
    <Pressable
      testID={testID}
      accessibilityRole="button"
      accessibilityLabel={subtitle ? `${title}. ${subtitle}` : title}
      accessibilityHint={accessibilityHint}
      onPress={onPress}
      style={({ pressed }) => [styles.pressRow, pressed && { opacity: 0.85 }]}
    >
      {content}
    </Pressable>
  );
}

/** Divisor fino do design system (`--line`). */
export function Divider() {
  const { colors } = useTheme();
  return <View style={{ height: 1, backgroundColor: colors.line }} />;
}

interface KeyValueProps {
  label: string;
  value: string;
  tone?: Tone;
}

export function KeyValue({ label, value, tone = "ink" }: KeyValueProps) {
  return (
    <View style={styles.kv}>
      <Text variant="caption" tone="muted">
        {label.toUpperCase()}
      </Text>
      <Text variant="body" tone={tone}>
        {value}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  card: { borderWidth: 1, borderRadius: radius.lg, padding: 16, gap: 12 },
  row: { flexDirection: "row", alignItems: "center", gap: 12, minHeight: 44 },
  rowText: { flex: 1, gap: 2 },
  rowBadge: { marginTop: 4, alignSelf: "flex-start" },
  pressRow: { minHeight: 56, justifyContent: "center" },
  kv: { gap: 2 },
});
