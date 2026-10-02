import React, { ReactNode, useCallback, useState } from "react";
import { StyleSheet, View } from "react-native";
import { APP_MODE } from "../config";
import { ActionOutcome, useStore } from "../data/store";
import { TranslationKey, useI18n } from "../i18n";
import { useTheme } from "../theme/ThemeProvider";
import { radius } from "../theme/tokens";
import { Icon, IconName } from "./Icon";
import { Text } from "./Text";

export type AlertTone = "info" | "success" | "warning" | "danger";

interface AlertProps {
  tone?: AlertTone;
  title?: string;
  children?: ReactNode;
  testID?: string;
  /** Anuncia mudanças a leitores de tela (use em mensagens de resultado). */
  live?: boolean;
}

const iconByTone: Record<AlertTone, IconName> = {
  info: "info",
  success: "check",
  warning: "alert",
  danger: "alert",
};

/** Alerta do design system (`.ae-alert`): fundo suave por estado com ícone. */
export function Alert({
  tone = "info",
  title,
  children,
  testID,
  live,
}: AlertProps) {
  const { colors } = useTheme();
  const palette = {
    info: { bg: colors.primarySoft, fg: colors.primary },
    success: { bg: colors.successSoft, fg: colors.success },
    warning: { bg: colors.warningSoft, fg: colors.warning },
    danger: { bg: colors.dangerSoft, fg: colors.danger },
  }[tone];
  return (
    <View
      testID={testID}
      accessibilityRole={
        tone === "danger" || tone === "warning" ? "alert" : undefined
      }
      accessibilityLiveRegion={live ? "polite" : undefined}
      style={[styles.alert, { backgroundColor: palette.bg }]}
    >
      <View style={styles.alertIcon}>
        <Icon name={iconByTone[tone]} size={20} color={palette.fg} />
      </View>
      <View style={styles.alertBody}>
        {title ? (
          <Text variant="title3" header>
            {title}
          </Text>
        ) : null}
        {typeof children === "string" ? (
          <Text variant="bodySm">{children}</Text>
        ) : (
          children
        )}
      </View>
    </View>
  );
}

interface BadgeProps {
  label: string;
  tone?: "neutral" | "success" | "warning" | "danger" | "info";
}

/** Selo de estado (`.ae-badge`): pílula de 24 px com ponto de cor. */
export function Badge({ label, tone = "neutral" }: BadgeProps) {
  const { colors } = useTheme();
  const palette = {
    neutral: { bg: colors.surfaceSunken, fg: colors.inkMuted },
    success: { bg: colors.successSoft, fg: colors.success },
    warning: { bg: colors.warningSoft, fg: colors.warning },
    danger: { bg: colors.dangerSoft, fg: colors.danger },
    info: { bg: colors.primarySoft, fg: colors.primary },
  }[tone];
  return (
    <View style={[styles.badge, { backgroundColor: palette.bg }]}>
      <View style={[styles.dot, { backgroundColor: palette.fg }]} />
      <Text variant="caption" style={{ color: palette.fg, letterSpacing: 0 }}>
        {label}
      </Text>
    </View>
  );
}

export interface FeedbackState {
  tone: AlertTone;
  text: string;
  note?: string;
}

/**
 * Resultado de uma gravação. Em modo demonstração acrescenta o aviso de que nada
 * foi salvo de verdade; sem conexão (live) mostra a recusa — nunca um sucesso falso.
 */
export function useActionFeedback() {
  const { t } = useI18n();
  const store = useStore();
  const [feedback, setFeedback] = useState<FeedbackState | null>(null);

  const report = useCallback(
    (outcome: ActionOutcome, successKey: TranslationKey): boolean => {
      if (outcome.ok) {
        setFeedback({
          tone: "success",
          text: t(successKey),
          note: store.mode === "preview" ? t("mode.preview.saved") : undefined,
        });
        return true;
      }
      setFeedback({
        tone: outcome.reason === "unavailable" ? "warning" : "danger",
        text: t(
          outcome.reason === "unavailable"
            ? "mode.action.unavailable"
            : "mode.action.invalid",
        ),
      });
      return false;
    },
    [store.mode, t],
  );
  const clear = useCallback(() => setFeedback(null), []);
  return { feedback, report, clear, setFeedback };
}

export function FeedbackAlert({
  feedback,
}: {
  feedback: FeedbackState | null;
}) {
  if (!feedback) return null;
  return (
    <Alert tone={feedback.tone} live testID="action-feedback">
      <Text variant="bodySm">{feedback.text}</Text>
      {feedback.note ? (
        <Text variant="bodySm" tone="muted">
          {feedback.note}
        </Text>
      ) : null}
    </Alert>
  );
}

/** Faixa no topo de cada tela que identifica o modo demonstração (dados fictícios). */
export function DemoBanner() {
  const { colors } = useTheme();
  const { t } = useI18n();
  const store = useStore();
  if (store.mode !== "preview") return null;
  return (
    <View
      testID="demo-banner"
      accessibilityRole="alert"
      style={[
        styles.banner,
        { backgroundColor: colors.warningSoft, borderColor: colors.warning },
      ]}
    >
      <Icon name="alert" size={16} color={colors.warning} />
      <Text variant="caption" tone="warning" style={styles.bannerText}>
        {t("mode.preview.banner")}
      </Text>
    </View>
  );
}

/** Texto de referência do modo atual, reutilizado em Configurações. */
export const currentModeKey: TranslationKey =
  APP_MODE === "preview" ? "settings.mode.preview" : "settings.mode.live";

const styles = StyleSheet.create({
  alert: {
    flexDirection: "row",
    gap: 12,
    padding: 12,
    paddingHorizontal: 16,
    borderRadius: radius.lg,
  },
  alertIcon: { paddingTop: 1 },
  alertBody: { flex: 1, gap: 4 },
  badge: {
    flexDirection: "row",
    alignItems: "center",
    alignSelf: "flex-start",
    gap: 6,
    height: 24,
    paddingHorizontal: 10,
    borderRadius: radius.full,
  },
  dot: { width: 6, height: 6, borderRadius: radius.full },
  banner: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderWidth: 1,
    borderRadius: radius.md,
  },
  bannerText: { flex: 1, letterSpacing: 0 },
});
