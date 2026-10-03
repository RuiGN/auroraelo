import React, { useEffect, useRef, useState } from "react";
import { StyleSheet, View } from "react-native";
import { useOptionalSession } from "../api/session";
import { Button } from "../components/Button";
import { Card, Divider, ListRow } from "../components/Card";
import {
  Alert,
  Badge,
  currentModeKey,
  FeedbackAlert,
  FeedbackState,
  useRunAction,
} from "../components/Feedback";
import { ChipGroup } from "../components/Form";
import { Icon } from "../components/Icon";
import {
  BrandMark,
  NoDataState,
  Screen,
  Section,
  StaleNotice,
  Wordmark,
} from "../components/Layout";
import { Text } from "../components/Text";
import { mutations } from "../data/mutations";
import { useStore } from "../data/store";
import { PrivacyRequestType, TeamRole } from "../domain/types";
import {
  catalogs,
  Locale,
  localeLabels,
  TranslationKey,
  useI18n,
} from "../i18n";
import { authFailureKey } from "../i18n/errorCodes";
import { useNav } from "../navigation/useNav";
import { ThemePreference, useTheme } from "../theme/ThemeProvider";

const ROLE_ICON = {
  psychiatrist: "stethoscope",
  psychologist: "message",
  nurse: "heart-pulse",
  pharmacist: "pill",
  other: "patient",
} as const satisfies Record<TeamRole, string>;

// ── Perfil ──────────────────────────────────────────────────────────────────

export function ProfileScreen() {
  const { t, formatDate } = useI18n();
  const nav = useNav();
  const store = useStore();
  const { colors } = useTheme();
  const snapshot = store.snapshot;
  return (
    <Screen testID="screen-profile">
      <Card>
        <View style={styles.brandRow}>
          <BrandMark size={44} />
          <View style={styles.flex}>
            <Wordmark tone="surface" size="md" />
            <Text variant="bodySm" tone="muted">
              {t("brand.tagline")}
            </Text>
          </View>
        </View>
        {snapshot ? (
          <>
            <Divider />
            <Text variant="title2" header>
              {snapshot.patient.displayName}
            </Text>
            <Text variant="bodySm" tone="muted">
              {snapshot.patient.clinicName}
              {snapshot.patient.dischargeDate
                ? ` • ${t("profile.discharge", {
                    date: formatDate(snapshot.patient.dischargeDate),
                  })}`
                : ""}
            </Text>
          </>
        ) : null}
      </Card>

      {snapshot ? (
        <>
          <StaleNotice />
          <Section title={t("profile.team")}>
            <Card>
              {snapshot.patient.careTeam.map((member, index) => (
                <View key={member.id}>
                  {index > 0 ? <Divider /> : null}
                  <ListRow
                    icon={ROLE_ICON[member.role]}
                    title={member.name}
                    subtitle={t(`profile.role.${member.role}`)}
                  />
                </View>
              ))}
            </Card>
            <View style={styles.note}>
              <Icon name="lock" size={16} color={colors.inkMuted} />
              <Text variant="bodySm" tone="muted" style={styles.flex}>
                {t("profile.psychotherapyNote")}
              </Text>
            </View>
          </Section>
        </>
      ) : (
        <NoDataState />
      )}

      <Card>
        <ListRow
          testID="profile-settings"
          icon="sliders"
          title={t("settings.title")}
          subtitle={`${t("settings.language")}, ${t("settings.appearance")}`}
          onPress={() => nav.navigate("Settings")}
        />
        <Divider />
        <ListRow
          testID="profile-privacy"
          icon="shield"
          title={t("privacy.title")}
          onPress={() => nav.navigate("Privacy")}
        />
      </Card>

      <SessionSection />
    </Screen>
  );
}

/**
 * Sair deste aparelho e sair dos outros aparelhos. Só existe no modo live com sessão
 * ativa; as duas ações pedem confirmação. Sair limpa o aparelho mesmo sem rede.
 */
function SessionSection() {
  const { t } = useI18n();
  const store = useStore();
  const session = useOptionalSession();
  const [confirm, setConfirm] = useState<"logout" | "others" | null>(null);
  const [busy, setBusy] = useState(false);
  const [feedback, setFeedback] = useState<FeedbackState | null>(null);
  const mounted = useRef(true);
  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);

  if (store.mode !== "live" || !session || session.status !== "active") {
    return null;
  }

  const logout = async () => {
    setBusy(true);
    await session.logout(); // a tela é trocada pela entrada quando a sessão acaba
    if (mounted.current) {
      setBusy(false);
      setConfirm(null);
    }
  };

  const logoutOthers = async () => {
    setBusy(true);
    const result = await session.logoutOthers();
    if (!mounted.current) return;
    setBusy(false);
    setConfirm(null);
    if (result.ok) {
      setFeedback({
        tone: "success",
        text:
          result.revoked > 0
            ? t("profile.logoutOthers.done", { count: result.revoked })
            : t("profile.logoutOthers.none"),
      });
    } else {
      setFeedback({ tone: "warning", text: t(authFailureKey(result.reason)) });
    }
  };

  return (
    <Section title={t("profile.session")}>
      <Card>
        <ListRow
          testID="profile-logout"
          icon="arrow-right"
          title={t("profile.logout")}
          subtitle={t("profile.logout.subtitle")}
          onPress={() => {
            setFeedback(null);
            setConfirm("logout");
          }}
        />
        <Divider />
        <ListRow
          testID="profile-logout-others"
          icon="phone"
          title={t("profile.logoutOthers")}
          subtitle={t("profile.logoutOthers.subtitle")}
          onPress={() => {
            setFeedback(null);
            setConfirm("others");
          }}
        />
      </Card>
      <FeedbackAlert feedback={feedback} />
      {confirm ? (
        <Alert
          tone="info"
          title={t(
            confirm === "logout"
              ? "profile.logout.confirm"
              : "profile.logoutOthers.confirm",
          )}
        >
          <Text variant="bodySm">
            {t(
              confirm === "logout"
                ? "profile.logout.body"
                : "profile.logoutOthers.body",
            )}
          </Text>
          <View style={styles.rowGap}>
            <Button
              label={t("common.cancel")}
              variant="secondary"
              size="sm"
              disabled={busy}
              style={styles.flex}
              testID="profile-session-cancel"
              onPress={() => setConfirm(null)}
            />
            <Button
              label={
                busy && confirm === "logout"
                  ? t("profile.logout.working")
                  : t("common.confirm")
              }
              size="sm"
              loading={busy}
              style={styles.flex}
              testID={
                confirm === "logout"
                  ? "profile-logout-confirm"
                  : "profile-logout-others-confirm"
              }
              onPress={() =>
                void (confirm === "logout" ? logout() : logoutOthers())
              }
            />
          </View>
        </Alert>
      ) : null}
    </Section>
  );
}

// ── Configurações ───────────────────────────────────────────────────────────

const THEMES: ThemePreference[] = ["system", "light", "dark"];

export function SettingsScreen() {
  const { t, locale, setLocale, busy, storageError } = useI18n();
  const theme = useTheme();
  const locales = Object.keys(catalogs) as Locale[];
  return (
    <Screen testID="screen-settings">
      <Card>
        <ChipGroup
          testID="settings-language"
          label={t("settings.language")}
          value={locale}
          onChange={(next) => void setLocale(next)}
          options={locales.map((code) => ({
            value: code,
            label: localeLabels[code],
          }))}
        />
        <Text variant="bodySm" tone="muted">
          {t("settings.language.note")}
        </Text>
        {busy ? (
          <Text variant="bodySm" tone="muted" accessibilityLiveRegion="polite">
            {t("common.loading")}
          </Text>
        ) : null}
      </Card>
      <Card>
        <ChipGroup
          testID="settings-theme"
          label={t("settings.appearance")}
          value={theme.preference}
          onChange={theme.setPreference}
          options={THEMES.map((value) => ({
            value,
            label: t(`settings.theme.${value}`),
          }))}
        />
      </Card>
      {storageError || theme.storageError ? (
        <Alert tone="warning" live>
          {t("settings.storageError")}
        </Alert>
      ) : null}
      <Card>
        <View style={styles.rowGap}>
          <Icon name="bell" size={20} color={theme.colors.inkMuted} />
          <Text variant="title3" header>
            {t("settings.reminders")}
          </Text>
        </View>
        <Text variant="bodySm" tone="muted">
          {t("settings.reminders.off")}
        </Text>
      </Card>
      <Card>
        <Text variant="title3" header>
          {t("settings.about")}
        </Text>
        <Text variant="bodySm">{t("settings.about.body")}</Text>
        <Text variant="bodySm" tone="muted">
          {t(currentModeKey)} • {t("common.version", { version: "1.0.0" })}
        </Text>
        <Text variant="bodySm" tone="muted">
          {t("settings.storage")}
        </Text>
      </Card>
    </Screen>
  );
}

// ── Privacidade e consentimentos ────────────────────────────────────────────

const REQUEST_TYPES: PrivacyRequestType[] = [
  "confirmation",
  "access",
  "correction",
  "portability",
  "revocation",
  "erasure",
];

export function PrivacyScreen() {
  const { t, formatDate } = useI18n();
  const store = useStore();
  const { feedback, run, report, setFeedback } = useRunAction();
  const snapshot = store.snapshot;

  const toggleConsent = (id: string, granted: boolean) =>
    run(mutations.setConsent({ id, granted }), "common.done");

  const requestRight = async (type: PrivacyRequestType) => {
    const outcome = await store.run(mutations.createPrivacyRequest(type));
    if (!outcome.ok && outcome.reason === "invalid") {
      setFeedback({ tone: "warning", text: t("privacy.request.duplicate") });
      return;
    }
    report(outcome, "privacy.request.sent");
  };

  return (
    <Screen testID="screen-privacy">
      <Text variant="body" tone="muted">
        {t("privacy.intro")}
      </Text>
      <FeedbackAlert feedback={feedback} />
      {!snapshot ? (
        <NoDataState />
      ) : (
        <>
          <Section title={t("privacy.consents")}>
            {snapshot.consents.map((consent) => {
              const granted = consent.status === "granted";
              const revocable =
                consent.canRevoke ?? (granted && !consent.mandatory);
              return (
                <Card key={consent.id} testID={`consent-${consent.purpose}`}>
                  <View style={styles.between}>
                    <Text variant="title3" style={styles.flex}>
                      {consent.title ??
                        t(
                          `privacy.consent.${consent.purpose}` as TranslationKey,
                        )}
                    </Text>
                    <Badge
                      label={t(
                        granted
                          ? "privacy.consent.granted"
                          : consent.status === "pending"
                            ? "privacy.consent.pending"
                            : "privacy.consent.revoked",
                      )}
                      tone={
                        granted
                          ? "success"
                          : consent.status === "pending"
                            ? "warning"
                            : "neutral"
                      }
                    />
                  </View>
                  <Text variant="bodySm" tone="muted">
                    {consent.decidedAt
                      ? t("privacy.consent.version", {
                          version: consent.documentVersion,
                          date: formatDate(consent.decidedAt),
                        })
                      : t("gate.consent.version", {
                          version: consent.documentVersion,
                        })}
                  </Text>
                  {consent.mandatory ? (
                    <Text variant="bodySm" tone="muted">
                      {t("privacy.consent.mandatory")}
                    </Text>
                  ) : granted && !revocable ? null : (
                    <Button
                      label={
                        granted
                          ? t("privacy.consent.revoke")
                          : t("privacy.consent.grant")
                      }
                      variant={granted ? "secondary" : "primary"}
                      size="sm"
                      testID={`consent-toggle-${consent.purpose}`}
                      onPress={() => toggleConsent(consent.id, !granted)}
                    />
                  )}
                </Card>
              );
            })}
            <Text variant="bodySm" tone="muted">
              {t("privacy.mandatoryNote")}
            </Text>
          </Section>

          <Section title={t("privacy.rights")}>
            <Text variant="bodySm" tone="muted">
              {t("privacy.rights.intro")}
            </Text>
            <Card>
              {REQUEST_TYPES.map((type, index) => (
                <View key={type}>
                  {index > 0 ? <Divider /> : null}
                  <ListRow
                    testID={`privacy-request-${type}`}
                    icon="file"
                    title={t(`privacy.request.${type}`)}
                    trailing={
                      <Button
                        label={t("privacy.request.open")}
                        size="sm"
                        variant="secondary"
                        testID={`privacy-open-${type}`}
                        onPress={() => requestRight(type)}
                      />
                    }
                  />
                </View>
              ))}
            </Card>
          </Section>

          <Section title={t("privacy.requests")}>
            {snapshot.privacyRequests.length === 0 ? (
              <Text variant="bodySm" tone="muted">
                {t("privacy.requests.none")}
              </Text>
            ) : (
              <Card>
                {snapshot.privacyRequests.map((request, index) => (
                  <View key={request.id}>
                    {index > 0 ? <Divider /> : null}
                    <ListRow
                      icon="clock"
                      title={t(`privacy.request.${request.type}`)}
                      subtitle={`${formatDate(request.requestedAt)} • ${t(`privacy.request.status.${request.status}`)}`}
                    />
                  </View>
                ))}
              </Card>
            )}
          </Section>
        </>
      )}
    </Screen>
  );
}

const styles = StyleSheet.create({
  brandRow: { flexDirection: "row", alignItems: "center", gap: 12 },
  flex: { flex: 1 },
  between: {
    flexDirection: "row",
    alignItems: "flex-start",
    justifyContent: "space-between",
    gap: 8,
  },
  note: { flexDirection: "row", gap: 8, alignItems: "flex-start" },
  rowGap: { flexDirection: "row", alignItems: "center", gap: 8 },
});
