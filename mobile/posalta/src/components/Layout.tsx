import React, { ReactNode } from "react";
import {
  ActivityIndicator,
  Image,
  ScrollView,
  StyleSheet,
  View,
} from "react-native";
import { useOptionalSession } from "../api/session";
import { Snapshot } from "../domain/types";
import { LoadFailure, Store, useStore } from "../data/store";
import { useI18n } from "../i18n";
import { useTheme } from "../theme/ThemeProvider";
import { CONTENT_MAX_WIDTH, radius } from "../theme/tokens";
import { Button } from "./Button";
import { Card } from "./Card";
import { Alert, DemoBanner } from "./Feedback";
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

/**
 * Estado do modo `live` quando o app não tem com quem falar (sem endereço válido do
 * servidor): nada é exibido nem inventado. Com servidor configurado o app mostra
 * carregando/erro (`NoDataState`), nunca este aviso.
 */
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

/** Carregando os dados da clínica (primeiro carregamento). */
export function LoadingState() {
  const { t } = useI18n();
  const { colors } = useTheme();
  return (
    <View
      testID="loading-state"
      accessibilityRole="progressbar"
      accessibilityLabel={t("data.loading")}
      accessibilityLiveRegion="polite"
      style={styles.loading}
    >
      <ActivityIndicator color={colors.primary} />
      <Text variant="bodySm" tone="muted">
        {t("data.loading")}
      </Text>
    </View>
  );
}

function failureKey(failure: LoadFailure | null) {
  if (failure === "offline") return "error.code.network" as const;
  if (failure === "blocked") return "error.code.clinic_blocked" as const;
  return "error.code.unknown" as const;
}

interface LoadErrorStateProps {
  failure: LoadFailure | null;
  onRetry: () => void;
}

/** Não foi possível carregar: mensagem acolhedora por motivo e "tentar de novo". */
export function LoadErrorState({ failure, onRetry }: LoadErrorStateProps) {
  const { t } = useI18n();
  return (
    <Card testID="load-error-state" tone="warning">
      <Text variant="title3" header>
        {t("data.error.title")}
      </Text>
      <Text variant="bodySm">{t(failureKey(failure))}</Text>
      <Button
        testID="retry-load"
        label={t("data.retry")}
        icon="refresh"
        variant="secondary"
        onPress={onRetry}
      />
    </Card>
  );
}

/**
 * O que mostrar quando ainda não há snapshot: sem servidor configurado, o aviso de
 * indisponível; carregando, o indicador; com falha, o erro com "tentar de novo".
 */
export function NoDataState() {
  const store = useStore();
  const session = useOptionalSession();
  if (
    store.mode === "live" &&
    (session === null || session.status === "disabled")
  ) {
    return <UnavailableState />;
  }
  if (store.status === "error") {
    return (
      <LoadErrorState
        failure={store.failure}
        onRetry={() => void store.refresh()}
      />
    );
  }
  return <LoadingState />;
}

/** Aviso sobre dados antigos: a última atualização falhou, mas há dados na tela. */
export function StaleNotice() {
  const { t } = useI18n();
  const store = useStore();
  if (store.mode !== "live" || store.status !== "error") return null;
  return (
    <Alert tone="warning" testID="stale-notice" live>
      <Text variant="bodySm">
        {t(
          store.failure === "blocked"
            ? "error.code.clinic_blocked"
            : "data.error.stale",
        )}
      </Text>
      <Button
        label={t("data.retry")}
        icon="refresh"
        size="sm"
        variant="secondary"
        testID="retry-refresh"
        onPress={() => void store.refresh()}
      />
    </Alert>
  );
}

interface WithDataProps {
  children: (snapshot: Snapshot, store: Store) => ReactNode;
}

/**
 * Renderiza a tela só quando há dados reais ou de demonstração; antes disso mostra
 * o carregando ou o erro com "tentar de novo". Se uma atualização falhar com dados
 * já na tela, mantém os dados e avisa.
 */
export function WithData({ children }: WithDataProps) {
  const store = useStore();
  if (!store.snapshot) return <NoDataState />;
  return (
    <>
      <StaleNotice />
      {children(store.snapshot, store)}
    </>
  );
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
  loading: { alignItems: "center", gap: 8, paddingVertical: 24 },
  unavailable: { flexDirection: "row", gap: 12 },
  unavailableText: { flex: 1, gap: 6 },
});
