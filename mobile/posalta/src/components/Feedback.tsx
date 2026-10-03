import React, {
  ReactNode,
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";
import { StyleSheet, View } from "react-native";
import { APP_MODE } from "../config";
import { Mutation } from "../data/mutations";
import { ActionOutcome, useStore } from "../data/store";
import { TranslationKey, useI18n } from "../i18n";
import { errorCodeKey } from "../i18n/errorCodes";
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

/** Mensagem acolhedora para uma gravação que não deu certo (nunca "salvo"). */
export function failureFeedback(
  outcome: Extract<ActionOutcome, { ok: false }>,
  t: (key: TranslationKey) => string,
): FeedbackState {
  switch (outcome.reason) {
    case "unavailable":
      // Com `code` o servidor falhou; sem `code` a ação nem existe neste app ainda.
      return {
        tone: "warning",
        text: t(
          outcome.code ? "mode.action.server" : "mode.action.unavailable",
        ),
      };
    case "invalid":
      return {
        tone: "danger",
        text: t(errorCodeKey(outcome.code) ?? "mode.action.invalid"),
      };
    case "offline":
      return { tone: "warning", text: t("mode.action.offline") };
    case "rejected":
      return {
        tone: "danger",
        text: t(errorCodeKey(outcome.code) ?? "mode.action.rejected"),
      };
    case "session":
      return { tone: "warning", text: t("mode.action.session") };
    case "blocked":
      return { tone: "warning", text: t("mode.action.blocked") };
  }
}

/**
 * Resultado de uma gravação. Em modo demonstração acrescenta o aviso de que nada
 * foi salvo de verdade; no live só diz "salvo" com `ok: true` e, nas falhas, explica
 * por motivo (sem rede, recusado, sessão, clínica bloqueada…).
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
      setFeedback(failureFeedback(outcome, t));
      return false;
    },
    [store.mode, t],
  );
  const clear = useCallback(() => setFeedback(null), []);
  return { feedback, report, clear, setFeedback };
}

/** Só mostra "trabalhando" se a gravação demorar (no preview ela resolve na hora). */
const PENDING_DELAY_MS = 250;

/**
 * Caminho único de escrita das telas: `await run(mutations.x(input), "chave.sucesso")`.
 * Aguarda `store.run`, mostra o resultado em `feedback` e devolve `true` só com
 * `ok: true` (use para limpar formulários). `pending` fica `true` enquanto uma
 * gravação lenta está em andamento (para desabilitar botões).
 */
export function useRunAction() {
  const store = useStore();
  const base = useActionFeedback();
  const [pending, setPending] = useState(false);
  const mounted = useRef(true);
  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);

  const { report } = base;
  const storeRun = store.run;
  const remote = store.mode === "live";
  const run = useCallback(
    async (
      mutation: Mutation,
      successKey: TranslationKey,
    ): Promise<boolean> => {
      let shown = false;
      // O preview resolve na hora: sem temporizador nem estado "trabalhando".
      const timer = remote
        ? setTimeout(() => {
            if (mounted.current) {
              shown = true;
              setPending(true);
            }
          }, PENDING_DELAY_MS)
        : undefined;
      try {
        const outcome = await storeRun(mutation);
        return mounted.current ? report(outcome, successKey) : outcome.ok;
      } finally {
        clearTimeout(timer);
        if (shown && mounted.current) setPending(false);
      }
    },
    [storeRun, report, remote],
  );
  return { ...base, run, pending };
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
