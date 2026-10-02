import React, { ReactNode } from "react";
import { Image, ScrollView, StyleSheet, View } from "react-native";
import { Snapshot } from "../domain/types";
import { Store, useStore } from "../data/store";
import { useI18n } from "../i18n";
import { useTheme } from "../theme/ThemeProvider";
import { CONTENT_MAX_WIDTH, radius } from "../theme/tokens";
import { Card } from "./Card";
import { DemoBanner } from "./Feedback";
import { Icon, IconName } from "./Icon";
import { Text } from "./Text";

interface ScreenProps {
  children: ReactNode;
  /** Desativa a rolagem quando a tela controla a própria (ex.: conversa). */
  scroll?: boolean;
  /** Oculta a faixa de demonstração (usado na ajuda urgente, cujos números são reais). */
  banner?: boolean;
  testID?: string;
}

/** Fundo `--surface` com coluna centralizada e espaçamento do design system. */
export function Screen({
  children,
  scroll = true,
  banner = true,
  testID,
}: ScreenProps) {
  const { colors } = useTheme();
  if (!scroll) {
    return (
      <View
        testID={testID}
        style={[styles.screen, { backgroundColor: colors.surface }]}
      >
        <View style={styles.column}>
          {banner ? <DemoBanner /> : null}
          {children}
        </View>
      </View>
    );
  }
  return (
    <ScrollView
      testID={testID}
      style={[styles.screen, { backgroundColor: colors.surface }]}
      contentContainerStyle={styles.scrollContent}
      keyboardShouldPersistTaps="handled"
    >
      <View style={styles.column}>
        {banner ? <DemoBanner /> : null}
        {children}
      </View>
    </ScrollView>
  );
}

interface SectionProps {
  title?: string;
  children: ReactNode;
  action?: ReactNode;
}

export function Section({ title, children, action }: SectionProps) {
  return (
    <View style={styles.section}>
      {title ? (
        <View style={styles.sectionHeader}>
          <Text variant="title2" header style={styles.sectionTitle}>
            {title}
          </Text>
          {action}
        </View>
      ) : null}
      {children}
    </View>
  );
}

interface ProgressBarProps {
  percent: number;
  label: string;
}

export function ProgressBar({ percent, label }: ProgressBarProps) {
  const { colors } = useTheme();
  const value = Math.max(0, Math.min(100, percent));
  return (
    <View
      accessibilityRole="progressbar"
      accessibilityLabel={label}
      accessibilityValue={{ min: 0, max: 100, now: value }}
      style={[styles.track, { backgroundColor: colors.surfaceSunken }]}
    >
      <View
        style={[
          styles.fill,
          { width: `${value}%`, backgroundColor: colors.primary },
        ]}
      />
    </View>
  );
}

interface EmptyStateProps {
  icon?: IconName;
  text: string;
}

export function EmptyState({ icon = "info", text }: EmptyStateProps) {
  const { colors } = useTheme();
  return (
    <View style={styles.empty}>
      <Icon name={icon} size={24} color={colors.inkMuted} />
      <Text variant="bodySm" tone="muted" style={styles.emptyText}>
        {text}
      </Text>
    </View>
  );
}

/** Estado honesto do modo `live` sem API autenticada: nada é exibido nem inventado. */
export function UnavailableState() {
  const { t } = useI18n();
  const { colors } = useTheme();
  return (
    <Card testID="unavailable-state" tone="primary">
      <View style={styles.unavailable}>
        <Icon name="lock" size={22} color={colors.primary} />
        <View style={styles.unavailableText}>
          <Text variant="title3" header>
            {t("mode.unavailable.title")}
          </Text>
          <Text variant="bodySm">{t("mode.unavailable.body")}</Text>
          <Text variant="bodySm" tone="muted">
            {t("mode.unavailable.help")}
          </Text>
        </View>
      </View>
    </Card>
  );
}

interface WithDataProps {
  children: (snapshot: Snapshot, store: Store) => ReactNode;
}

/** Renderiza a tela só quando há dados reais ou de demonstração. */
export function WithData({ children }: WithDataProps) {
  const store = useStore();
  if (!store.snapshot) return <UnavailableState />;
  return <>{children(store.snapshot, store)}</>;
}

const markSource = require("../../assets/aurora-elo-mark.png");

interface BrandMarkProps {
  size?: number;
}

/** Símbolo oficial (logo.png). Decorativo: o nome acompanha o símbolo. */
export function BrandMark({ size = 32 }: BrandMarkProps) {
  return (
    <Image
      source={markSource}
      accessibilityIgnoresInvertColors
      accessible={false}
      style={{ width: size, height: size }}
      resizeMode="contain"
    />
  );
}

interface WordmarkProps {
  tone?: "nav" | "surface";
  size?: "sm" | "md" | "lg";
}

/** “Aurora Elo” com as duas cores do design system (`.ae-brand__name`). */
export function Wordmark({ tone = "nav", size = "md" }: WordmarkProps) {
  const { colors } = useTheme();
  const fontSize = { sm: 18, md: 22, lg: 32 }[size];
  const auroraColor = tone === "nav" ? colors.navInk : colors.ink;
  const eloColor = tone === "nav" ? colors.navAccent : colors.primary;
  return (
    <Text
      variant="wordmark"
      accessibilityLabel="Aurora Elo"
      style={{ fontSize, lineHeight: fontSize + 2, color: auroraColor }}
    >
      Aurora{" "}
      <Text
        variant="wordmark"
        style={{ fontSize, lineHeight: fontSize + 2, color: eloColor }}
      >
        Elo
      </Text>
    </Text>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1 },
  scrollContent: { flexGrow: 1, paddingBottom: 32 },
  column: {
    width: "100%",
    maxWidth: CONTENT_MAX_WIDTH,
    alignSelf: "center",
    padding: 16,
    gap: 16,
    flexGrow: 1,
  },
  section: { gap: 12 },
  sectionHeader: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: 8,
  },
  sectionTitle: { flex: 1 },
  track: { height: 8, borderRadius: radius.full, overflow: "hidden" },
  fill: { height: 8, borderRadius: radius.full },
  empty: { alignItems: "center", gap: 8, paddingVertical: 16 },
  emptyText: { textAlign: "center" },
  unavailable: { flexDirection: "row", gap: 12 },
  unavailableText: { flex: 1, gap: 6 },
});
